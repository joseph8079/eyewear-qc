import csv
import io
import json

from django.http import JsonResponse
from django.shortcuts import render
from django.utils.timezone import now, timedelta
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from .models import (
    Unit,
    Inspection,
    InspectionStageResult,
    Defect,
    ReworkTicket,
)


# ============================================================
# ROOT + HEALTH (ALWAYS SAFE FOR RENDER HEALTH CHECKS)
# ============================================================

def home(request):
    """
    Keep root route extremely stable:
    - Works for GET and HEAD
    - No templates
    - Prevents Render health checks from failing
    """
    return JsonResponse({"ok": True, "message": "QC service running"})


def health(request):
    return JsonResponse({"ok": True, "service": "qc"})


# ============================================================
# UI PAGES (HTML)
# ============================================================

@login_required
def ui_home(request):
    return render(request, "qc/home.html")


@login_required
def legacy_frames_page(request):
    # Later you can bind this to real Unit data
    return render(request, "qc/frames.html")


@login_required
def legacy_complaints_page(request):
    return render(request, "qc/complaints.html")


@login_required
@csrf_exempt
def legacy_import_frames_page(request):
    """
    Basic CSV uploader.
    Expected columns (any casing ok, extra columns ignored):
      unit_id, order_id, frame_model, lab, priority

    If unit_id missing in a row, row is skipped.
    """
    if request.method == "GET":
        return render(request, "qc/import_frames.html")

    uploaded = request.FILES.get("file")
    if not uploaded:
        return render(request, "qc/import_frames.html", {"error": "No file uploaded"})

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
                    if v:
                        setattr(unit, field, v)
                        changed = True
                if changed:
                    unit.save()
                    updated += 1

        return render(
            request,
            "qc/import_frames.html",
            {"success": f"Import complete: created {created}, updated {updated}, skipped {skipped}"},
        )
    except Exception as e:
        return render(request, "qc/import_frames.html", {"error": f"Upload failed: {e}"})


# ============================================================
# INLINE METRICS (NO qc.services PACKAGE)
# ============================================================

def _pass_rate(days=7):
    start = now() - timedelta(days=days)
    total = Inspection.objects.filter(started_at__gte=start).count()
    passed = Inspection.objects.filter(started_at__gte=start, final_result="PASS").count()
    return 0 if total == 0 else round((passed / total) * 100, 2)


def _first_pass_yield(days=7):
    start = now() - timedelta(days=days)

    first_pass = Inspection.objects.filter(
        started_at__gte=start,
        attempt_number=1,
        final_result="PASS",
    )

    reworked_unit_ids = set(
        ReworkTicket.objects.filter(inspection__in=first_pass)
        .values_list("unit_id", flat=True)
    )

    fp_count = first_pass.exclude(unit_id__in=reworked_unit_ids).count()
    total = first_pass.count()
    return 0 if total == 0 else round((fp_count / total) * 100, 2)


def _avg_qc_time(days=7):
    start = now() - timedelta(days=days)
    qs = Inspection.objects.filter(started_at__gte=start, completed_at__isnull=False)

    secs = [
        (i.completed_at - i.started_at).total_seconds()
        for i in qs
        if i.completed_at and i.started_at
    ]
    return 0 if not secs else round((sum(secs) / len(secs)) / 60, 2)


def _bottleneck_stage(days=7):
    start = now() - timedelta(days=days)
    qs = InspectionStageResult.objects.filter(started_at__gte=start)

    durations = {}
    for r in qs:
        # started_at may be null depending on your model defaults
        if not r.started_at or not r.completed_at:
            continue
        dur = (r.completed_at - r.started_at).total_seconds()
        durations.setdefault(r.stage, []).append(dur)

    if not durations:
        return None

    avg = {k: sum(v) / len(v) for k, v in durations.items()}
    return max(avg, key=avg.get)


# ============================================================
# LEGACY API ENDPOINTS (SAFE STUBS)
# ============================================================

@login_required
def legacy_stores(request):
    return JsonResponse({"legacy": True, "items": []})


@login_required
def legacy_frame_styles(request):
    return JsonResponse({"legacy": True, "items": []})


@login_required
def legacy_frame_variants(request):
    return JsonResponse({"legacy": True, "items": []})


@csrf_exempt
@login_required
def legacy_complaints(request):
    if request.method == "GET":
        return JsonResponse({"legacy": True, "items": []})

    if request.method == "POST":
        payload = json.loads(request.body.decode("utf-8") or "{}")
        return JsonResponse(
            {
                "legacy": True,
                "created": True,
                "complaint": {
                    "id": 1,
                    "data": payload,
                    "note": "Legacy stub. Old Complaint models removed.",
                },
            }
        )

    return JsonResponse({"error": "method not allowed"}, status=405)


@login_required
def legacy_complaint_detail(request, complaint_id: int):
    return JsonResponse(
        {
            "legacy": True,
            "complaint": {
                "id": complaint_id,
                "note": "Legacy stub. Old Complaint models removed.",
            },
        }
    )


@csrf_exempt
@login_required
def legacy_complaint_attachments(request, complaint_id: int):
    if request.method == "GET":
        return JsonResponse({"legacy": True, "items": []})

    if request.method == "POST":
        return JsonResponse(
            {"legacy": True, "uploaded": True, "note": "Legacy stub. Old Attachment models removed."}
        )

    return JsonResponse({"error": "method not allowed"}, status=405)


# ============================================================
# QC v2.1 API ENDPOINTS
# ============================================================

@csrf_exempt
@login_required
def start_inspection(request):
    """
    POST JSON:
    {
      "unit_id": "U123",
      "order_id": "O999",
      "frame_model": "Rayban 123",
      "lab": "LabA",
      "priority": "NORMAL" | "URGENT",
      "training_mode_used": true/false
    }
    """
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
    """
    POST JSON:
    {
      "inspection_id": 123,
      "stage": "INTAKE"|"COSMETIC"|"RX"|"FIT"|"FINAL_PREP"|"DECISION",
      "status": "PASS"|"FAIL",
      "notes": "text",
      "data": {...},
      "defect": {  # required if FAIL
        "category": "COSMETIC",
        "reason_code": "LENS_SCRATCH",
        "severity": "LOW"|"MED"|"HIGH",
        "notes": "optional"
      }
    }
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    payload = json.loads(request.body.decode("utf-8") or "{}")

    inspection_id = payload.get("inspection_id")
    stage = payload.get("stage")
    status = payload.get("status")

    if not inspection_id or not stage or status not in ("PASS", "FAIL"):
        return JsonResponse({"error": "inspection_id, stage, status required"}, status=400)

    try:
        inspection = Inspection.objects.get(id=inspection_id)
    except Inspection.DoesNotExist:
        return JsonResponse({"error": "inspection not found"}, status=404)

    stage_result, _ = InspectionStageResult.objects.update_or_create(
        inspection=inspection,
        stage=stage,
        defaults={
            "status": status,
            "notes": payload.get("notes", ""),
            "data": payload.get("data"),
            "completed_at": now(),
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

        return JsonResponse(
            {
                "stage_result_id": stage_result.id,
                "inspection_id": inspection.id,
                "stage": stage,
                "status": status,
                "defect_id": defect.id,
            }
        )

    return JsonResponse(
        {
            "stage_result_id": stage_result.id,
            "inspection_id": inspection.id,
            "stage": stage,
            "status": status,
        }
    )


@csrf_exempt
@login_required
def finalize_inspection(request):
    """
    POST JSON: { "inspection_id": 123 }

    Rule:
    - If INTAKE+COSMETIC+RX+FIT+FINAL_PREP are all PASS => PASS and unit STORE_READY
    - Else FAIL (unit stays REWORK/QUARANTINE/QC_IN_PROGRESS)
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    payload = json.loads(request.body.decode("utf-8") or "{}")
    inspection_id = payload.get("inspection_id")
    if not inspection_id:
        return JsonResponse({"error": "inspection_id required"}, status=400)

    try:
        inspection = Inspection.objects.get(id=inspection_id)
    except Inspection.DoesNotExist:
        return JsonResponse({"error": "inspection not found"}, status=404)

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
        if inspection.unit.status == "QC_IN_PROGRESS":
            inspection.unit.status = "QC_IN_PROGRESS"
            inspection.unit.save()

    inspection.save()

    return JsonResponse(
        {
            "inspection_id": inspection.id,
            "final_result": inspection.final_result,
            "unit_status": inspection.unit.status,
            "stages": stage_map,
        }
    )


@login_required
def dashboard(request):
    """
    GET /api/qc/dashboard/?days=7
    """
    try:
        days = int(request.GET.get("days", "7"))
    except ValueError:
        days = 7

    return JsonResponse(
        {
            "days": days,
            "pass_rate": _pass_rate(days),
            "first_pass_yield": _first_pass_yield(days),
            "avg_qc_time_minutes": _avg_qc_time(days),
            "bottleneck_stage": _bottleneck_stage(days),
        }
    )
