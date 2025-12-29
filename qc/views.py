import csv
import io
import json
from collections import defaultdict

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template import TemplateDoesNotExist
from django.utils.timezone import now, timedelta
from django.views.decorators.csrf import csrf_exempt

from .models import (
    Unit,
    Inspection,
    InspectionStageResult,
    Defect,
    DefectPhoto,
    ReworkTicket,
    QualityFlag,
)


# ============================================================
# HEALTH (Render polls /health/)
# ============================================================

def health(request):
    return JsonResponse({"ok": True, "message": "QC service running"})


# ============================================================
# UI ROUTES
# ============================================================

@login_required
def ui_home(request):
    return redirect("/ui/dashboard/")


@login_required
def ui_dashboard(request):
    """
    Dashboard page. Will never 500:
    - if template missing -> renders fallback HTML
    - if DB empty -> shows zeros
    Includes:
      - analytics
      - SLA alerts
      - auto-flags (model/lab defect thresholds)
    """
    days = int(request.GET.get("days", "7") or 7)

    # Tunables (simple defaults)
    min_sample = int(request.GET.get("min_sample", "10") or 10)
    threshold = float(request.GET.get("threshold", "0.10") or 0.10)  # 10% defect rate
    urgent_sla_hours = float(request.GET.get("urgent_sla_h", "4") or 4)
    stuck_sla_hours = float(request.GET.get("stuck_sla_h", "12") or 12)

    try:
        context = _build_dashboard_context(
            days=days,
            min_sample=min_sample,
            threshold=threshold,
            urgent_sla_hours=urgent_sla_hours,
            stuck_sla_hours=stuck_sla_hours,
        )
    except Exception as e:
        context = {
            "days": days,
            "pass_rate": 0,
            "first_pass_yield": 0,
            "avg_qc_time_minutes": 0,
            "bottleneck_stage": "—",
            "alerts": [f"Dashboard safe mode: {e}"],
            "flags": [],
            "sla_alerts": [],
        }

    try:
        return render(request, "qc/dashboard.html", context)
    except TemplateDoesNotExist:
        flags_html = "".join(
            f"<li><b>{f['flag_type']}</b> {f['flag_key']} — defect {f['defect_rate']}% (thr {f['threshold']}%), n={f['sample_size']}</li>"
            for f in context.get("flags", [])
        ) or "<li>None</li>"

        sla_html = "".join(
            f"<li>{a}</li>" for a in context.get("sla_alerts", [])
        ) or "<li>None</li>"

        html = f"""
        <!doctype html>
        <html>
        <head><meta charset="utf-8"><title>QC Dashboard</title></head>
        <body style="font-family:Arial;padding:20px;background:#f6f7fb;">
          <h2>QC Dashboard (Safe Mode)</h2>
          <p style="color:#6b7280;">Template missing: <code>templates/qc/dashboard.html</code></p>

          <div style="background:#fff;padding:12px;border-radius:10px;max-width:720px;">
            <b>Last {context.get("days")} days</b><br/><br/>
            <b>Pass Rate:</b> {context.get("pass_rate")}%<br/>
            <b>First Pass Yield:</b> {context.get("first_pass_yield")}%<br/>
            <b>Avg QC Time:</b> {context.get("avg_qc_time_minutes")} min<br/>
            <b>Bottleneck:</b> {context.get("bottleneck_stage")}<br/>
          </div>

          <h3 style="margin-top:18px;">SLA Alerts</h3>
          <ul>{sla_html}</ul>

          <h3 style="margin-top:18px;">Auto Flags</h3>
          <ul>{flags_html}</ul>

          <p style="margin-top:14px;">
            <a href="/frames/">Frames</a> |
            <a href="/import/frames/">Import</a> |
            <a href="/ui/qc-wizard/">QC Wizard</a> |
            <a href="/admin/">Admin</a> |
            <a href="/health/">Health</a>
          </p>
        </body>
        </html>
        """
        return HttpResponse(html)


@login_required
def ui_frames(request):
    """
    Frames/Units list. Never 500.
    """
    try:
        units = Unit.objects.all().order_by("-received_at")[:300]
        return render(request, "qc/frames.html", {"units": units})
    except TemplateDoesNotExist:
        count = Unit.objects.count()
        return HttpResponse(f"""
        <html><body style="font-family:Arial;padding:20px;background:#f6f7fb;">
          <h2>Frames (Template Missing)</h2>
          <p style="color:#6b7280;">Missing <code>templates/qc/frames.html</code></p>
          <div style="background:#fff;padding:12px;border-radius:10px;">
            Total Units in DB: <b>{count}</b>
          </div>
          <p style="margin-top:14px;">
            <a href="/ui/dashboard/">Dashboard</a> |
            <a href="/import/frames/">Import</a> |
            <a href="/admin/">Admin</a>
          </p>
        </body></html>
        """)
    except Exception as e:
        return HttpResponse(f"""
        <html><body style="font-family:Arial;padding:20px;background:#f6f7fb;">
          <h2>Frames (Safe Mode)</h2>
          <div style="background:#fff;padding:12px;border-radius:10px;">
            <b>Error:</b> <code>{str(e)}</code>
          </div>
          <p style="margin-top:14px;">
            <a href="/ui/dashboard/">Dashboard</a> |
            <a href="/admin/">Admin</a>
          </p>
        </body></html>
        """)


@login_required
@csrf_exempt
def ui_import_frames(request):
    """
    CSV import Units.
    Columns supported (case-insensitive):
      unit_id, order_id, frame_model, lab, priority
    """
    if request.method == "GET":
        try:
            return render(request, "qc/import_frames.html")
        except TemplateDoesNotExist:
            return HttpResponse("""
            <html><body style="font-family:Arial;padding:20px;">
              <h2>Import Frames</h2>
              <p>Missing template <code>templates/qc/import_frames.html</code></p>
              <p>Upload a CSV with headers: unit_id, order_id, frame_model, lab, priority</p>
            </body></html>
            """)

    uploaded = request.FILES.get("file")
    if not uploaded:
        return HttpResponse("No file uploaded", status=400)

    try:
        raw = uploaded.read().decode("utf-8", errors="ignore")
        f = io.StringIO(raw)
        reader = csv.DictReader(f)

        created = 0
        updated = 0
        skipped = 0

        for row in reader:
            norm = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
            unit_id = norm.get("unit_id") or norm.get("unit") or norm.get("id")
            if not unit_id:
                skipped += 1
                continue

            defaults = {
                "order_id": norm.get("order_id") or norm.get("order"),
                "frame_model": norm.get("frame_model") or norm.get("model") or "",
                "lab": norm.get("lab") or "",
                "priority": (norm.get("priority") or "NORMAL").upper(),
                "status": "RECEIVED",
            }

            unit, was_created = Unit.objects.get_or_create(unit_id=unit_id, defaults=defaults)

            if was_created:
                created += 1
            else:
                changed = False
                for field in ["order_id", "frame_model", "lab", "priority"]:
                    v = defaults.get(field)
                    if v is not None and v != "" and getattr(unit, field) != v:
                        setattr(unit, field, v)
                        changed = True
                if changed:
                    unit.save()
                    updated += 1

        msg = f"Import complete: created {created}, updated {updated}, skipped {skipped}"
        try:
            return render(request, "qc/import_frames.html", {"success": msg})
        except TemplateDoesNotExist:
            return HttpResponse(msg)

    except Exception as e:
        try:
            return render(request, "qc/import_frames.html", {"error": f"Upload failed: {e}"})
        except Exception:
            return HttpResponse(f"Upload failed: {e}", status=500)


@login_required
def ui_qc_wizard(request):
    """
    Placeholder: step-by-step QC screen.
    """
    try:
        return render(request, "qc/qc_wizard.html")
    except TemplateDoesNotExist:
        return HttpResponse("""
        <html><body style="font-family:Arial;padding:20px;background:#f6f7fb;">
          <h2>QC Wizard</h2>
          <p>Missing template <code>templates/qc/qc_wizard.html</code></p>
          <p><a href="/ui/dashboard/">Back</a></p>
        </body></html>
        """)


# ============================================================
# DASHBOARD METRICS + FLAGS + SLA
# ============================================================

def _pass_rate(days=7):
    start = now() - timedelta(days=days)
    total = Inspection.objects.filter(started_at__gte=start).count()
    passed = Inspection.objects.filter(started_at__gte=start, final_result="PASS").count()
    return 0 if total == 0 else round((passed / total) * 100, 2)


def _first_pass_yield(days=7):
    start = now() - timedelta(days=days)
    first_pass = Inspection.objects.filter(started_at__gte=start, attempt_number=1, final_result="PASS")
    if not first_pass.exists():
        return 0

    reworked_units = set(
        ReworkTicket.objects.filter(inspection__in=first_pass).values_list("unit_id", flat=True)
    )
    fp_count = first_pass.exclude(unit_id__in=reworked_units).count()
    total = first_pass.count()
    return 0 if total == 0 else round((fp_count / total) * 100, 2)


def _avg_qc_time_minutes(days=7):
    start = now() - timedelta(days=days)
    qs = Inspection.objects.filter(started_at__gte=start, completed_at__isnull=False)

    secs = []
    for i in qs:
        if i.started_at and i.completed_at:
            secs.append((i.completed_at - i.started_at).total_seconds())

    return 0 if not secs else round((sum(secs) / len(secs)) / 60, 2)


def _bottleneck_stage(days=7):
    start = now() - timedelta(days=days)
    qs = InspectionStageResult.objects.filter(started_at__gte=start)

    durations = defaultdict(list)
    for r in qs:
        if r.started_at and r.completed_at:
            durations[r.stage].append((r.completed_at - r.started_at).total_seconds())

    if not durations:
        return None

    avg = {k: (sum(v) / len(v)) for k, v in durations.items()}
    return max(avg, key=avg.get)


def _sla_alerts(urgent_sla_hours=4, stuck_sla_hours=12):
    """
    Alerts for urgent jobs in progress too long and any job stuck too long in QC.
    (Uses Unit.received_at as baseline since no stage timer per-unit here yet)
    """
    alerts = []
    t_urgent = now() - timedelta(hours=urgent_sla_hours)
    t_stuck = now() - timedelta(hours=stuck_sla_hours)

    urgent_stuck = Unit.objects.filter(
        priority="URGENT",
        status__in=["QC_IN_PROGRESS", "REWORK", "RETEST"],
        received_at__lte=t_urgent,
    ).count()

    stuck_any = Unit.objects.filter(
        status__in=["QC_IN_PROGRESS", "REWORK", "RETEST"],
        received_at__lte=t_stuck,
    ).count()

    if urgent_stuck > 0:
        alerts.append(f"URGENT SLA: {urgent_stuck} urgent units older than {urgent_sla_hours}h")
    if stuck_any > 0:
        alerts.append(f"STUCK SLA: {stuck_any} units in QC/rework older than {stuck_sla_hours}h")

    return alerts


def _auto_quality_flags(days=7, min_sample=10, threshold=0.10):
    """
    Compute defect rate by frame_model and lab based on Defect count / inspected units count.
    Creates/updates QualityFlag rows in the rolling window.
    Returns list of active flags (dicts) for dashboard.
    """
    window_end = now()
    window_start = window_end - timedelta(days=days)

    # inspected units in window
    inspections = Inspection.objects.filter(started_at__gte=window_start, started_at__lte=window_end)
    unit_ids = list(inspections.values_list("unit_id", flat=True).distinct())

    if not unit_ids:
        # Resolve any old flags in this window (optional)
        return []

    units = Unit.objects.filter(id__in=unit_ids)

    # sample size by key
    sample_by_model = defaultdict(int)
    sample_by_lab = defaultdict(int)
    for u in units:
        sample_by_model[u.frame_model] += 1
        sample_by_lab[u.lab] += 1

    # defects in window (based on stage_result timestamps)
    defects = Defect.objects.filter(
        stage_result__inspection__unit_id__in=unit_ids,
        stage_result__started_at__gte=window_start,
        stage_result__started_at__lte=window_end,
    ).select_related("stage_result__inspection__unit")

    defect_by_model = defaultdict(int)
    defect_by_lab = defaultdict(int)
    for d in defects:
        unit = d.stage_result.inspection.unit
        defect_by_model[unit.frame_model] += 1
        defect_by_lab[unit.lab] += 1

    active_flags = []

    def upsert_flag(flag_type, key, sample_size, defect_count):
        if sample_size < min_sample:
            # if exists active, keep it but allow resolving logic later
            return

        rate = 0 if sample_size == 0 else (defect_count / sample_size)
        should_flag = rate >= threshold

        obj, _ = QualityFlag.objects.get_or_create(
            flag_type=flag_type,
            flag_key=key,
            window_start=window_start,
            window_end=window_end,
            defaults={
                "sample_size": sample_size,
                "defect_rate": rate,
                "threshold": threshold,
                "is_active": should_flag,
            },
        )

        # update (rolling window)
        obj.sample_size = sample_size
        obj.defect_rate = rate
        obj.threshold = threshold

        if should_flag:
            obj.is_active = True
            obj.resolved_at = None
        else:
            # auto-resolve if it was active
            if obj.is_active:
                obj.is_active = False
                obj.resolved_at = now()

        obj.save()

        if obj.is_active:
            active_flags.append(
                {
                    "flag_type": obj.flag_type,
                    "flag_key": obj.flag_key,
                    "sample_size": obj.sample_size,
                    "defect_rate": round(obj.defect_rate * 100, 2),
                    "threshold": round(obj.threshold * 100, 2),
                }
            )

    # model flags
    for model_key, n in sample_by_model.items():
        upsert_flag("MODEL", model_key, n, defect_by_model.get(model_key, 0))

    # lab flags
    for lab_key, n in sample_by_lab.items():
        upsert_flag("LAB", lab_key, n, defect_by_lab.get(lab_key, 0))

    return active_flags


def _build_dashboard_context(days=7, min_sample=10, threshold=0.10, urgent_sla_hours=4, stuck_sla_hours=12):
    flags = _auto_quality_flags(days=days, min_sample=min_sample, threshold=threshold)
    return {
        "days": days,
        "pass_rate": _pass_rate(days),
        "first_pass_yield": _first_pass_yield(days),
        "avg_qc_time_minutes": _avg_qc_time_minutes(days),
        "bottleneck_stage": _bottleneck_stage(days) or "—",
        "flags": flags,
        "sla_alerts": _sla_alerts(urgent_sla_hours=urgent_sla_hours, stuck_sla_hours=stuck_sla_hours),
        "alerts": [],
        "min_sample": min_sample,
        "threshold": threshold,
    }


# ============================================================
# API: QC FLOW
# ============================================================

@csrf_exempt
@login_required
def start_inspection(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    payload = json.loads(request.body.decode("utf-8") or "{}")
    unit_id = payload.get("unit_id")
    if not unit_id:
        return JsonResponse({"error": "unit_id required"}, status=400)

    unit, created = Unit.objects.get_or_create(
        unit_id=unit_id,
        defaults={
            "order_id": payload.get("order_id"),
            "frame_model": payload.get("frame_model", ""),
            "lab": payload.get("lab", ""),
            "priority": payload.get("priority", "NORMAL"),
            "status": "QC_IN_PROGRESS",
        },
    )

    # update optional fields
    for field in ["order_id", "frame_model", "lab", "priority"]:
        if payload.get(field):
            setattr(unit, field, payload[field])
    unit.status = "QC_IN_PROGRESS"
    unit.save()

    last_attempt = Inspection.objects.filter(unit=unit).order_by("-attempt_number").first()
    attempt_number = 1 if not last_attempt else last_attempt.attempt_number + 1

    inspection = Inspection.objects.create(
        unit=unit,
        attempt_number=attempt_number,
        tech_user=request.user,
        training_mode_used=bool(payload.get("training_mode_used", False)),
    )

    return JsonResponse(
        {
            "inspection_id": inspection.id,
            "unit_id": unit.unit_id,
            "attempt_number": attempt_number,
            "created_unit": created,
        }
    )


@csrf_exempt
@login_required
def complete_stage(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    payload = json.loads(request.body.decode("utf-8") or "{}")
    inspection_id = payload.get("inspection_id")
    stage = payload.get("stage")
    status = payload.get("status")

    if not inspection_id or not stage or status not in ("PASS", "FAIL"):
        return JsonResponse({"error": "inspection_id, stage, status required"}, status=400)

    inspection = get_object_or_404(Inspection, id=inspection_id)

    # NOTE: InspectionStageResult.completed_at is auto_now=True in your model.
    # So we don't need to force it; Django will update it automatically on save.
    stage_result, _ = InspectionStageResult.objects.update_or_create(
        inspection=inspection,
        stage=stage,
        defaults={
            "status": status,
            "notes": payload.get("notes", ""),
            "data": payload.get("data"),
        },
    )

    if status == "FAIL":
        defect_payload = payload.get("defect")
        if not defect_payload:
            return JsonResponse({"error": "defect required when FAIL"}, status=400)

        defect = Defect.objects.create(
            stage_result=stage_result,
            category=defect_payload.get("category", stage),
            reason_code=defect_payload.get("reason_code", "UNKNOWN"),
            severity=defect_payload.get("severity", "LOW"),
            notes=defect_payload.get("notes", ""),
        )

        ReworkTicket.objects.create(
            unit=inspection.unit,
            inspection=inspection,
            failed_stage=stage,
            reason_summary=f"{defect.reason_code} ({defect.severity})",
        )

        inspection.unit.status = "QUARANTINE" if defect.severity == "HIGH" else "REWORK"
        inspection.unit.save()

        return JsonResponse({"stage_result_id": stage_result.id, "defect_id": defect.id, "status": "FAIL"})

    return JsonResponse({"stage_result_id": stage_result.id, "status": "PASS"})


@csrf_exempt
@login_required
def finalize_inspection(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    payload = json.loads(request.body.decode("utf-8") or "{}")
    inspection_id = payload.get("inspection_id")
    if not inspection_id:
        return JsonResponse({"error": "inspection_id required"}, status=400)

    inspection = get_object_or_404(Inspection, id=inspection_id)

    required_stages = {"INTAKE", "COSMETIC", "RX", "FIT", "FINAL_PREP"}
    results = InspectionStageResult.objects.filter(inspection=inspection)
    stage_map = {r.stage: r.status for r in results}

    all_present = required_stages.issubset(stage_map.keys())
    all_passed = all_present and all(stage_map[s] == "PASS" for s in required_stages)

    inspection.completed_at = now()

    if all_passed:
        inspection.final_result = "PASS"
        inspection.unit.status = "STORE_READY"
        inspection.unit.save()
    else:
        inspection.final_result = "FAIL"

    inspection.save()

    return JsonResponse(
        {
            "inspection_id": inspection.id,
            "final_result": inspection.final_result,
            "unit_status": inspection.unit.status,
        }
    )


# ============================================================
# API: PHOTO UPLOAD + ANNOTATION (circle defect)
# ============================================================

@csrf_exempt
@login_required
def upload_defect_photo(request, defect_id):
    """
    POST multipart form-data:
      - image: file
      - annotation_json: optional JSON string
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    defect = get_object_or_404(Defect, id=defect_id)

    img = request.FILES.get("image")
    if not img:
        return JsonResponse({"error": "image file required"}, status=400)

    annotation_raw = request.POST.get("annotation_json")
    annotation = None
    if annotation_raw:
        try:
            annotation = json.loads(annotation_raw)
        except Exception:
            return JsonResponse({"error": "annotation_json must be valid JSON"}, status=400)

    photo = DefectPhoto.objects.create(defect=defect, image=img, annotation_json=annotation)
    return JsonResponse({"photo_id": photo.id, "ok": True})


@csrf_exempt
@login_required
def update_defect_annotation(request, photo_id):
    """
    POST JSON:
      { "annotation_json": {...} }
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    photo = get_object_or_404(DefectPhoto, id=photo_id)

    payload = json.loads(request.body.decode("utf-8") or "{}")
    if "annotation_json" not in payload:
        return JsonResponse({"error": "annotation_json required"}, status=400)

    photo.annotation_json = payload["annotation_json"]
    photo.save()
    return JsonResponse({"ok": True})


# ============================================================
# JSON dashboard endpoint for new UI JS
# ============================================================

@login_required
def dashboard(request):
    try:
        days = int(request.GET.get("days", "7"))
    except ValueError:
        days = 7

    return JsonResponse(
        {
            "days": days,
            "pass_rate": _pass_rate(days),
            "first_pass_yield": _first_pass_yield(days),
            "avg_qc_time_minutes": _avg_qc_time_minutes(days),
            "bottleneck_stage": _bottleneck_stage(days),
        }
    )
