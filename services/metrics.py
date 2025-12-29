cat > qc/services/metrics.py <<'PY'
# qc/services/metrics.py
from __future__ import annotations

from datetime import timedelta
from django.utils import timezone

from qc.models import Unit, Inspection, QualityFlag, Defect


def counts_overview() -> dict:
    return {
        "not_inspected": Unit.objects.filter(status="RECEIVED").count(),
        "in_progress": Unit.objects.filter(status="QC_IN_PROGRESS").count(),
        "passed": Unit.objects.filter(status="STORE_READY").count(),
        "failed": Unit.objects.filter(status__in=["REWORK", "RETEST", "QUARANTINE"]).count(),
        "total": Unit.objects.all().count(),
    }


def first_pass_yield(days: int = 7) -> float:
    since = timezone.now() - timedelta(days=days)
    first_attempts = Inspection.objects.filter(started_at__gte=since, attempt_number=1)
    total = first_attempts.count()
    if total == 0:
        return 0.0
    passed = first_attempts.filter(final_result="PASS").count()
    return round((passed / total) * 100.0, 2)


def avg_qc_time_hours(days: int = 7) -> float:
    since = timezone.now() - timedelta(days=days)
    qs = Inspection.objects.filter(completed_at__isnull=False, completed_at__gte=since).only(
        "started_at", "completed_at"
    )
    if not qs.exists():
        return 0.0

    total_seconds = 0.0
    n = 0
    for insp in qs:
        if insp.started_at and insp.completed_at:
            total_seconds += (insp.completed_at - insp.started_at).total_seconds()
            n += 1

    if n == 0:
        return 0.0
    return round((total_seconds / n) / 3600.0, 2)


def urgent_sla_breaches(hours_threshold: int = 6) -> int:
    since = timezone.now() - timedelta(hours=hours_threshold)
    return Unit.objects.filter(
        priority="URGENT",
        status__in=["RECEIVED", "QC_IN_PROGRESS"],
        received_at__lt=since,
    ).count()


def auto_flag(defect_threshold_percent: float = 10.0, days: int = 7, min_sample: int = 10) -> None:
    window_end = timezone.now()
    window_start = window_end - timedelta(days=days)

    inspections = (
        Inspection.objects.filter(completed_at__isnull=False, completed_at__gte=window_start)
        .select_related("unit")
    )

    # ---- LAB flags ----
    lab_counts = {}
    for insp in inspections:
        lab_counts[insp.unit.lab] = lab_counts.get(insp.unit.lab, 0) + 1

    for lab, sample in lab_counts.items():
        if sample < min_sample:
            continue
        defect_count = Defect.objects.filter(
            stage_result__inspection__in=inspections,
            stage_result__inspection__unit__lab=lab,
        ).count()
        defect_rate = (defect_count / sample) * 100.0 if sample else 0.0
        if defect_rate >= defect_threshold_percent:
            QualityFlag.objects.get_or_create(
                flag_type="LAB",
                flag_key=lab,
                window_start=window_start,
                window_end=window_end,
                defaults={
                    "sample_size": sample,
                    "defect_rate": float(defect_rate),
                    "threshold": float(defect_threshold_percent),
                    "is_active": True,
                },
            )

    # ---- MODEL flags ----
    model_counts = {}
    for insp in inspections:
        model_counts[insp.unit.frame_model] = model_counts.get(insp.unit.frame_model, 0) + 1

    for model, sample in model_counts.items():
        if sample < min_sample:
            continue
        defect_count = Defect.objects.filter(
            stage_result__inspection__in=inspections,
            stage_result__inspection__unit__frame_model=model,
        ).count()
        defect_rate = (defect_count / sample) * 100.0 if sample else 0.0
        if defect_rate >= defect_threshold_percent:
            QualityFlag.objects.get_or_create(
                flag_type="MODEL",
                flag_key=model,
                window_start=window_start,
                window_end=window_end,
                defaults={
                    "sample_size": sample,
                    "defect_rate": float(defect_rate),
                    "threshold": float(defect_threshold_percent),
                    "is_active": True,
                },
            )
PY
