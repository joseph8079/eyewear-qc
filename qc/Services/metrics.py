# qc/services/metrics.py
from __future__ import annotations

from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from qc.models import Unit, Inspection, Defect, QualityFlag


def counts_overview() -> dict:
    """
    Returns counts for dashboard:
      - not_inspected (RECEIVED)
      - in_progress (QC_IN_PROGRESS)
      - passed (STORE_READY)
      - failed (REWORK, RETEST, QUARANTINE)
    """
    return {
        "not_inspected": Unit.objects.filter(status="RECEIVED").count(),
        "in_progress": Unit.objects.filter(status="QC_IN_PROGRESS").count(),
        "passed": Unit.objects.filter(status="STORE_READY").count(),
        "failed": Unit.objects.filter(status__in=["REWORK", "RETEST", "QUARANTINE"]).count(),
        "total": Unit.objects.all().count(),
    }


def first_pass_yield(days: int = 7) -> float:
    """
    FPY = units that PASS on attempt 1 / units with attempt 1 completed.
    """
    since = timezone.now() - timedelta(days=days)
    first_attempts = Inspection.objects.filter(attempt_number=1, completed_at__isnull=False, started_at__gte=since)

    denom = first_attempts.count()
    if denom == 0:
        return 0.0

    num = first_attempts.filter(final_result="PASS").count()
    return round((num / denom) * 100.0, 2)


def avg_qc_time_hours(days: int = 7) -> float:
    """
    Avg hours from inspection started_at to completed_at.
    """
    since = timezone.now() - timedelta(days=days)
    qs = Inspection.objects.filter(completed_at__isnull=False, started_at__gte=since)

    total_seconds = 0.0
    n = 0
    for ins in qs.only("started_at", "completed_at"):
        if ins.started_at and ins.completed_at:
            total_seconds += (ins.completed_at - ins.started_at).total_seconds()
            n += 1

    if n == 0:
        return 0.0

    return round((total_seconds / n) / 3600.0, 2)


def urgent_sla_breaches(hours_threshold: int = 6) -> int:
    """
    Urgent SLA breaches:
    Urgent units that are not STORE_READY within N hours of received_at.
    """
    cutoff = timezone.now() - timedelta(hours=hours_threshold)
    return Unit.objects.filter(priority="URGENT", status__in=["RECEIVED", "QC_IN_PROGRESS", "REWORK", "RETEST"]).filter(
        received_at__lte=cutoff
    ).count()


def auto_flag(defect_threshold_percent: float = 10.0, days: int = 7, min_sample: int = 10) -> int:
    """
    Auto-flag labs and frame_models if defect rate exceeds threshold in a time window.
    Creates QualityFlag rows. Returns number of new flags created.
    """
    now = timezone.now()
    window_start = now - timedelta(days=days)

    # Units in window (by received)
    units = Unit.objects.filter(received_at__gte=window_start)

    # Total per lab
    lab_totals = units.values("lab").annotate(n=Count("id"))
    model_totals = units.values("frame_model").annotate(n=Count("id"))

    # Defective units in window (any defect tied to inspection->unit)
    defective_unit_ids = (
        Defect.objects.filter(stage_result__inspection__started_at__gte=window_start)
        .values_list("stage_result__inspection__unit_id", flat=True)
        .distinct()
    )
    defective_units = Unit.objects.filter(id__in=list(defective_unit_ids))

    # Defects per lab/model
    lab_defects = defective_units.values("lab").annotate(n=Count("id"))
    model_defects = defective_units.values("frame_model").annotate(n=Count("id"))

    lab_def_map = {x["lab"]: x["n"] for x in lab_defects}
    model_def_map = {x["frame_model"]: x["n"] for x in model_defects}

    created = 0

    # LAB flags
    for row in lab_totals:
        lab = row["lab"]
        total = row["n"]
        if not lab or total < min_sample:
            continue
        defects = lab_def_map.get(lab, 0)
        rate = (defects / total) * 100.0
        if rate >= defect_threshold_percent:
            obj, was_created = QualityFlag.objects.get_or_create(
                flag_type="LAB",
                flag_key=lab,
                window_start=window_start,
                window_end=now,
                defaults={
                    "sample_size": total,
                    "defect_rate": rate,
                    "threshold": defect_threshold_percent,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1

    # MODEL flags
    for row in model_totals:
        model = row["frame_model"]
        total = row["n"]
        if not model or total < min_sample:
            continue
        defects = model_def_map.get(model, 0)
        rate = (defects / total) * 100.0
        if rate >= defect_threshold_percent:
            obj, was_created = QualityFlag.objects.get_or_create(
                flag_type="MODEL",
                flag_key=model,
                window_start=window_start,
                window_end=now,
                defaults={
                    "sample_size": total,
                    "defect_rate": rate,
                    "threshold": defect_threshold_percent,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1

    return created
