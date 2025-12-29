# qc/views.py
from __future__ import annotations

import csv
import io
import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import (
    Unit,
    Inspection,
    InspectionStageResult,
    Defect,
    DefectPhoto,
    ReworkTicket,
    QualityFlag,
    # Complaints module (you said restored)
    Store,
    Complaint,
    ComplaintAttachment,
)

from .services.metrics import (
    counts_overview,
    first_pass_yield,
    avg_qc_time_hours,
    urgent_sla_breaches,
    auto_flag,
)
from .services.process import DEEP_COSMETIC_STEPS


# -----------------------
# Health
# -----------------------
def health(request: HttpRequest):
    return JsonResponse({"ok": True, "message": "QC service running"})


# -----------------------
# Home + UI shell
# -----------------------
@login_required
def home(request: HttpRequest):
    return redirect("ui_dashboard")


@login_required
def ui_home(request: HttpRequest):
    # /ui/ -> dashboard
    return redirect("ui_dashboard")


# -----------------------
# Dashboard
# -----------------------
@login_required
def ui_dashboard(request: HttpRequest):
    """
    Dashboard:
    - counts overview (not inspected / in progress / passed / failed)
    - First Pass Yield
    - avg QC time
    - urgent SLA breaches
    - auto flags (model/lab defect threshold last 7 days)
    """
    # Run auto flag calculation (never crash dashboard)
    try:
        auto_flag(defect_threshold_percent=10.0, days=7, min_sample=10)
    except Exception:
        pass

    overview = counts_overview()
    fpy = first_pass_yield(days=7)
    avg_hours = avg_qc_time_hours(days=7)
    urgent_breaches = urgent_sla_breaches(hours_threshold=6)

    active_flags = QualityFlag.objects.filter(is_active=True).order_by("-created_at")[:25]

    context = {
        "overview": overview,
        "fpy": fpy,
        "avg_hours": avg_hours,
        "urgent_breaches": urgent_breaches,
        "active_flags": active_flags,
    }
    return render(request, "qc/dashboard.html", context)


# -----------------------
# Frames list
# -----------------------
@login_required
def frames_list(request: HttpRequest):
    status = (request.GET.get("status") or "").strip()
    q = (request.GET.get("q") or "").strip()

    units = Unit.objects.all().order_by("-received_at")

    if status:
        units = units.filter(status=status)

    if q:
        units = units.filter(Q(unit_id__icontains=q) | Q(order_id__icontains=q))

    context = {
        "units": units[:500],
        "status": status,
        "q": q,
        "status_choices": [c[0] for c in Unit._meta.get_field("status").choices],
    }
    return render(request, "qc/frames_list.html", context)


# -----------------------
# Unit detail page
# -----------------------
@login_required
def unit_detail(request: HttpRequest, unit_id: int):
    """
    Detail view by DB primary key (Unit.id).
    Shows inspections, defects, tickets.
    """
    unit = get_object_or_404(Unit, id=unit_id)
    inspections = (
        Inspection.objects.filter(unit=unit)
        .select_related("tech_user")
        .order_by("-attempt_number")
    )
    tickets = (
        ReworkTicket.objects.filter(unit=unit)
        .select_related("inspection", "assigned_to")
        .order_by("-created_at")
    )
    defects = (
        Defect.objects.filter(stage_result__inspection__unit=unit)
        .select_related("stage_result")
        .order_by("-id")
    )

    context = {
        "unit": unit,
        "inspections": inspections,
        "tickets": tickets,
        "defects": defects,
    }
    return render(request, "qc/unit_detail.html", context)


# -----------------------
# Import frames (single endpoint)
# matches qc/urls.py: path("import/frames/", views.import_frames, name="import_frames")
# -----------------------
@login_required
@require_http_methods(["GET", "POST"])
@transaction.atomic
def import_frames(request: HttpRequest):
    """
    GET:
      - render import page
    POST:
      - if action=download_template => returns CSV
      - else expects CSV upload under "file"
    """
    if request.method == "GET":
        return render(request, "qc/import_frames.html")

    action = (request.POST.get("action") or "").strip()

    # Download template via POST (simple + avoids adding another URL)
    if action == "download_template":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["unit_id", "order_id", "frame_model", "lab", "priority", "status"])
        w.writerow(["U-0001", "ORD-0001", "Model 100", "Lab A", "NORMAL", "RECEIVED"])
        w.writerow(["U-0002", "ORD-0002", "Model 200", "Lab B", "URGENT", "RECEIVED"])

        resp = HttpResponse(buf.getvalue(), content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="frames_import_template.csv"'
        return resp

    # Upload CSV
    f = request.FILES.get("file")
    if not f:
        messages.error(request, "Please choose a CSV file.")
        return redirect("import_frames")

    try:
        content = f.read().decode("utf-8-sig")
    except Exception:
        messages.error(request, "Could not read file. Please upload a UTF-8 CSV.")
        return redirect("import_frames")

    reader = csv.DictReader(io.StringIO(content))
    required = {"unit_id", "order_id", "frame_model", "lab", "priority", "status"}
    if not required.issubset(set(reader.fieldnames or [])):
        messages.error(request, f"CSV missing columns. Required: {', '.join(sorted(required))}")
        return redirect("import_frames")

    created = 0
    updated = 0

    for row in reader:
        unit_code = (row.get("unit_id") or "").strip()
        if not unit_code:
            continue

        defaults = {
            "order_id": (row.get("order_id") or "").strip() or None,
            "frame_model": (row.get("frame_model") or "").strip(),
            "lab": (row.get("lab") or "").strip(),
            "priority": (row.get("priority") or "NORMAL").strip().upper(),
            "status": (row.get("status") or "RECEIVED").strip().upper(),
        }

        obj, was_created = Unit.objects.update_or_create(unit_id=unit_code, defaults=defaults)
        created += 1 if was_created else 0
        updated += 0 if was_created else 1

    messages.success(request, f"Import complete. Created: {created}, Updated: {updated}.")
    return redirect("frames_list")


# -----------------------
# Inspection wizard (4-step deep cosmetic process)
# NOTE: If you want this routed, add URLs for start_inspection + inspection_wizard
# -----------------------
@login_required
def start_inspection(request: HttpRequest, unit_pk: int):
    unit = get_object_or_404(Unit, id=unit_pk)

    last_attempt = Inspection.objects.filter(unit=unit).order_by("-attempt_number").first()
    attempt_number = (last_attempt.attempt_number + 1) if last_attempt else 1

    training_mode = request.GET.get("training", "0") == "1"

    inspection = Inspection.objects.create(
        unit=unit,
        attempt_number=attempt_number,
        tech_user=request.user,
        training_mode_used=training_mode,
    )

    unit.status = "QC_IN_PROGRESS"
    unit.save(update_fields=["status"])

    for stage in ["INTAKE", "COSMETIC", "FIT", "DECISION"]:
        InspectionStageResult.objects.create(
            inspection=inspection,
            stage=stage,
            status="PASS",
            notes="",
            data={},
        )

    return redirect("inspection_wizard", inspection_id=inspection.id)


@login_required
@require_http_methods(["GET", "POST"])
def inspection_wizard(request: HttpRequest, inspection_id: int):
    inspection = get_object_or_404(Inspection, id=inspection_id)
    unit = inspection.unit

    stage_results = {sr.stage: sr for sr in InspectionStageResult.objects.filter(inspection=inspection)}
    intake = stage_results.get("INTAKE")
    cosmetic = stage_results.get("COSMETIC")
    fit = stage_results.get("FIT")

    training_mode = inspection.training_mode_used

    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "save_intake" and intake:
            intake.notes = request.POST.get("intake_notes", "")
            intake.status = request.POST.get("intake_status", "PASS")
            intake.data = {
                "verified_unit_id": request.POST.get("verified_unit_id", ""),
                "verified_order_id": request.POST.get("verified_order_id", ""),
            }
            intake.save()

        elif action == "save_cosmetic" and cosmetic:
            cosmetic.notes = request.POST.get("cosmetic_notes", "")
            steps = {}
            for s in DEEP_COSMETIC_STEPS:
                key = s["key"]
                steps[key] = request.POST.get(f"step_{key}", "PASS")
            cosmetic.data = {"deep_steps": steps}
            cosmetic.status = "FAIL" if any(v == "FAIL" for v in steps.values()) else "PASS"
            cosmetic.save()

        elif action == "save_fit" and fit:
            fit.notes = request.POST.get("fit_notes", "")
            fit.data = {
                "temple_alignment": request.POST.get("temple_alignment", ""),
                "nosepads": request.POST.get("nosepads", ""),
            }
            fit.status = request.POST.get("fit_status", "PASS")
            fit.save()

        elif action == "add_defect":
            stage = request.POST.get("defect_stage", "COSMETIC")
            sr = stage_results.get(stage)
            if sr:
                d = Defect.objects.create(
                    stage_result=sr,
                    category=request.POST.get("category", "UNKNOWN"),
                    reason_code=request.POST.get("reason_code", "UNKNOWN"),
                    severity=request.POST.get("severity", "LOW"),
                    notes=request.POST.get("defect_notes", ""),
                )

                photo = request.FILES.get("defect_photo")
                if photo:
                    annotation_json = request.POST.get("annotation_json", "")
                    try:
                        ann = json.loads(annotation_json) if annotation_json else None
                    except Exception:
                        ann = None
                    DefectPhoto.objects.create(defect=d, image=photo, annotation_json=ann)

                sr.status = "FAIL"
                sr.save()

        elif action == "finalize":
            final = request.POST.get("final_result", "PASS")
            inspection.final_result = final
            inspection.completed_at = timezone.now()
            inspection.save(update_fields=["final_result", "completed_at"])

            if final == "PASS":
                unit.status = "STORE_READY"
                unit.save(update_fields=["status"])
                messages.success(request, f"Unit {unit.unit_id} marked STORE_READY ✅")
            else:
                unit.status = "REWORK"
                unit.save(update_fields=["status"])

                failed_stage = request.POST.get("failed_stage", "COSMETIC")
                summary = request.POST.get("reason_summary", "Failed QC")
                ReworkTicket.objects.create(
                    unit=unit,
                    inspection=inspection,
                    failed_stage=failed_stage,
                    reason_summary=summary,
                    assigned_to=None,
                    status="OPEN",
                )
                messages.error(request, f"Unit {unit.unit_id} FAILED → Rework ticket created.")

            return redirect("frames_list")

        return redirect("inspection_wizard", inspection_id=inspection.id)

    defects = (
        Defect.objects.filter(stage_result__inspection=inspection)
        .select_related("stage_result")
        .order_by("-id")
    )

    context = {
        "inspection": inspection,
        "unit": unit,
        "stage_results": stage_results,
        "defects": defects,
        "deep_steps": DEEP_COSMETIC_STEPS,
        "training_mode": training_mode,
    }
    return render(request, "qc/inspection_wizard.html", context)


# -----------------------
# Complaints module
# -----------------------
@login_required
def complaints_list(request: HttpRequest):
    status = (request.GET.get("status") or "").strip()
    store_code = (request.GET.get("store") or "").strip()
    q = (request.GET.get("q") or "").strip()

    qs = Complaint.objects.select_related("store", "unit", "created_by").order_by("-created_at")

    if status:
        qs = qs.filter(status=status)
    if store_code:
        qs = qs.filter(store__code=store_code)
    if q:
        qs = qs.filter(
            Q(title__icontains=q)
            | Q(description__icontains=q)
            | Q(unit_id_text__icontains=q)
            | Q(order_id_text__icontains=q)
        )

    stores = Store.objects.filter(is_active=True).order_by("name")

    context = {
        "complaints": qs[:500],
        "status": status,
        "store_code": store_code,
        "q": q,
        "stores": stores,
        "status_choices": [c[0] for c in Complaint.STATUS_CHOICES],
        "category_choices": [c[0] for c in Complaint.CATEGORY_CHOICES],
    }
    return render(request, "qc/complaints_list.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def complaints_new(request: HttpRequest):
    stores = Store.objects.filter(is_active=True).order_by("name")

    if request.method == "POST":
        store_id = request.POST.get("store_id")
        title = (request.POST.get("title") or "").strip()
        category = request.POST.get("category") or "OTHER"
        description = (request.POST.get("description") or "").strip()
        unit_id = (request.POST.get("unit_id") or "").strip()
        order_id = (request.POST.get("order_id") or "").strip()

        if not store_id or not title:
            messages.error(request, "Store + Title are required.")
            return render(
                request,
                "qc/complaints_new.html",
                {"stores": stores, "category_choices": [c[0] for c in Complaint.CATEGORY_CHOICES]},
            )

        store = get_object_or_404(Store, id=store_id)

        unit_obj = Unit.objects.filter(unit_id=unit_id).first() if unit_id else None

        complaint = Complaint.objects.create(
            store=store,
            unit=unit_obj,
            unit_id_text=unit_id or None,
            order_id_text=order_id or None,
            category=category,
            title=title,
            description=description,
            created_by=request.user,
        )

        for f in request.FILES.getlist("files"):
            ComplaintAttachment.objects.create(
                complaint=complaint,
                file=f,
                note="",
                uploaded_by=request.user,
            )

        messages.success(request, "Complaint created.")
        return redirect("complaints_detail", complaint_id=complaint.id)

    return render(
        request,
        "qc/complaints_new.html",
        {"stores": stores, "category_choices": [c[0] for c in Complaint.CATEGORY_CHOICES]},
    )


@login_required
@require_http_methods(["GET", "POST"])
def complaints_detail(request: HttpRequest, complaint_id: int):
    complaint = get_object_or_404(
        Complaint.objects.select_related("store", "unit", "created_by", "resolved_by"),
        id=complaint_id,
    )

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add_attachment":
            f = request.FILES.get("file")
            note = (request.POST.get("note") or "").strip()
            if not f:
                messages.error(request, "Choose a file to upload.")
            else:
                ComplaintAttachment.objects.create(
                    complaint=complaint,
                    file=f,
                    note=note,
                    uploaded_by=request.user,
                )
                messages.success(request, "Attachment added.")
            return redirect("complaints_detail", complaint_id=complaint.id)

        if action == "update_status":
            new_status = request.POST.get("status") or complaint.status
            complaint.status = new_status

            if new_status == "RESOLVED":
                complaint.resolved_by = request.user
                complaint.resolved_at = timezone.now()
                complaint.resolution_notes = (request.POST.get("resolution_notes") or "").strip()

            complaint.save()
            messages.success(request, "Complaint updated.")
            return redirect("complaints_detail", complaint_id=complaint.id)

    attachments = complaint.attachments.all().order_by("-uploaded_at")

    context = {
        "complaint": complaint,
        "attachments": attachments,
        "status_choices": [c[0] for c in Complaint.STATUS_CHOICES],
    }
    return render(request, "qc/complaints_detail.html", context)
