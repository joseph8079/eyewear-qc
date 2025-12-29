from datetime import timedelta
from django.db.models import Count, Q
from django.utils import timezone

from qc.models import Inspection, Defect, QualityFlag


def _defect_rate_for_filter(window_start, window_end, inspection_filter_q, min_sample):
    """
    defect rate = units with >=1 defect / units inspected (completed)
    """
    ins_qs = Inspection.objects.filter(
        completed_at__isnull=False,
        started_at__gte=window_start,
        started_at__lte=window_end
    ).filter(inspection_filter_q)

    sample = ins_qs.count()
    if sample < min_sample:
        return sample, None  # not enough data

    # count inspections that have any defect
    defective = Defect.objects.filter(
        created_at__gte=window_start,
        created_at__lte=window_end,
        stage_result__inspection__in=ins_qs
    ).values("stage_result__inspection").distinct().count()

    rate = defective / sample if sample else 0.0
    return sample, rate


def run_auto_flags(window_days=7, model_threshold=0.08, lab_threshold=0.10, min_sample=20):
    """
    Auto-flag if defect threshold exceeded over last N days.
    Creates/updates active QualityFlag rows.

    model_threshold: defect rate threshold for frame model
    lab_threshold: defect rate threshold for lab
    """
    now = timezone.now()
    window_start = now - timedelta(days=window_days)
    window_end = now

    # Resolve existing flags that are out of window
    QualityFlag.objects.filter(is_active=True, window_end__lt=window_start).update(is_active=False, resolved_at=now)

    # -----------------------
    # MODEL FLAGS
    # -----------------------
    # Find all model names present in window
    model_names = Inspection.objects.filter(
        started_at__gte=window_start,
        started_at__lte=window_end,
        completed_at__isnull=False
    ).values_list("unit__frame_model__model_name", flat=True).distinct()

    for model_name in model_names:
        sample, rate = _defect_rate_for_filter(
            window_start, window_end,
            inspection_filter_q=Q(unit__frame_model__model_name=model_name),
            min_sample=min_sample
        )
        if rate is None:
            continue
        if rate >= model_threshold:
            QualityFlag.objects.update_or_create(
                flag_type="MODEL",
                flag_key=model_name,
                window_start=window_start,
                window_end=window_end,
                defaults={
                    "sample_size": sample,
                    "defect_rate": rate,
                    "threshold": model_threshold,
                    "is_active": True,
                    "resolved_at": None,
                }
            )

    # -----------------------
    # LAB FLAGS
    # -----------------------
    lab_names = Inspection.objects.filter(
        started_at__gte=window_start,
        started_at__lte=window_end,
        completed_at__isnull=False
    ).values_list("unit__lab__name", flat=True).distinct()

    for lab_name in lab_names:
        sample, rate = _defect_rate_for_filter(
            window_start, window_end,
            inspection_filter_q=Q(unit__lab__name=lab_name),
            min_sample=min_sample
        )
        if rate is None:
            continue
        if rate >= lab_threshold:
            QualityFlag.objects.update_or_create(
                flag_type="LAB",
                flag_key=lab_name,
                window_start=window_start,
                window_end=window_end,
                defaults={
                    "sample_size": sample,
                    "defect_rate": rate,
                    "threshold": lab_threshold,
                    "is_active": True,
                    "resolved_at": None,
                }
            )
