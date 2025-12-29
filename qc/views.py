import json
from django.http import JsonResponse
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from .models import (
    Unit,
    Inspection,
    InspectionStageResult,
    Defect,
    ReworkTicket,
)
from .services.metrics import pass_rate, first_pass_yield, avg_qc_time, bottleneck_stage


# -----------------------------------
# HEALTH
# -----------------------------------
def health(request):
    return JsonResponse({"ok": True, "service": "qc"})


# -----------------------------------
# LEGACY ENDPOINTS (SAFE STUBS)
# These prevent crashes while you migrate your frontend.
# They DO NOT require old models like Store/Complaint.
# -----------------------------------

@login_required
def legacy_stores(request):
    # Old UI expected a list of stores
    return JsonResponse({
        "legacy": True,
        "items": []
    })


@login_required
def legacy_frame_styles(request):
    # Old UI expected styles list
    return JsonResponse({
        "legacy": True,
        "items": []
    })


@login_required
def legacy_frame_variants(request):
    # Old UI expected variants list
    return JsonResponse({
        "legacy": True,
        "items": []
    })


@csrf_exempt
@login_required
def legacy_complaints(request):
    # Old UI expected complaints list + create
    if request.method == "GET":
        return JsonResponse({"legacy": True, "items": []})

    if request.method == "POST":
        # Accept and return a fake id so old UI doesn't crash
        payload = json.loads(request.body.decode("utf-8") or "{}")
        return JsonResponse({
            "legacy": True,
            "created": True,
            "complaint": {
                "id": 1,
                "data": payload,
                "note": "Legacy endpoint stub. Migrate UI to QC v2.1."
            }
        })

    return JsonResponse({"error": "method not allowed"}, status=405)


@login_required
def legacy_complaint_detail(request, complaint_id: int):
    # Old UI expected complaint detail
    return JsonResponse({
        "legacy": True,
        "complaint": {
            "id": complaint_id,
            "note": "Legacy endpoint stub. Complaint models removed."
        }
    })


@csrf_exempt
@login_required
def legacy_complaint_attachments(request, complaint_id: int):
    # Old UI expected attachment list + upload
    if request.method == "GET":
        return JsonResponse({"legacy": True, "items": []})

    if request.method == "POST":
        return JsonResponse({
            "legacy": True,
            "uploaded": True,
            "note": "Legacy endpoint stub. Attachment models removed."
        })

    return JsonResponse({"error": "method not allowed"}, status=405)


# -----------------------------------
# QC v2.1 ENDPOINTS (REAL)
# -----------------------------------

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

    # Update unit fields if provided
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

    return JsonResponse({
        "inspection_id": inspection.id,
        "unit_id": unit.unit_id,
        "attempt_number": attempt_number,
        "created_unit": created,
    })


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
        }
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

    return JsonResponse({
        "stage_result_id": stage_result.id,
        "inspection_id": inspection.id,
        "stage": stage,
        "status": status,
    })


@csrf_exempt
@login_required
def finalize_inspection(request):
    """
    POST JSON: { "inspection_id": 123 }

    Rule:
    - If all required stages PASS -> PASS + unit STORE_READY
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

    return JsonResponse({
        "inspection_id": inspection.id,
        "final_result": inspection.final_result,
        "unit_status": inspection.unit.status,
        "stages": stage_map,
    })


@login_required
def dashboard(request):
    """
    GET /api/qc/dashboard/?days=7
    """
    try:
        days = int(request.GET.get("days", "7"))
    except ValueError:
        days = 7

    return JsonResponse({
        "days": days,
        "pass_rate": pass_rate(days),
        "first_pass_yield": first_pass_yield(days),
        "avg_qc_time_minutes": avg_qc_time(days),
        "bottleneck_stage": bottleneck_stage(days),
    })

