from django.utils.timezone import now, timedelta
from qc.models import InspectionStageResult, QualityFlag

LOOKBACK_DAYS = 7
MIN_SAMPLE = 20
THRESHOLD = 0.12


def refresh_quality_flags():
    start = now() - timedelta(days=LOOKBACK_DAYS)

    qs = InspectionStageResult.objects.filter(
        status="FAIL", completed_at__gte=start
    )

    grouped = {}

    for s in qs:
        unit = s.inspection.unit
        grouped.setdefault(("MODEL", unit.frame_model), []).append(s)
        grouped.setdefault(("LAB", unit.lab), []).append(s)

    for (flag_type, key), failures in grouped.items():
        sample = len(failures)
        if sample < MIN_SAMPLE:
            continue

        rate = len(failures) / sample
        if rate >= THRESHOLD:
            QualityFlag.objects.update_or_create(
                flag_type=flag_type,
                flag_key=key,
                is_active=True,
                defaults={
                    "window_start": start,
                    "window_end": now(),
                    "sample_size": sample,
                    "defect_rate": rate,
                    "threshold": THRESHOLD,
                },
            )

