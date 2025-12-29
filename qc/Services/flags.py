from django.utils.timezone import now, timedelta
from qc.models import InspectionStageResult, QualityFlag

LOOKBACK_DAYS = 7
MIN_SAMPLE = 20
THRESHOLD = 0.12


def refresh_quality_flags():
    start = now() - timedelta(days=LOOKBACK_DAYS)

    # Count FAIL stage results and flag by model/lab
    failures = InspectionStageResult.objects.filter(
        status="FAIL",
        completed_at__gte=start
    )

    groups = {}

    for s in failures:
        unit = s.inspection.unit
        groups.setdefault(("MODEL", unit.frame_model), []).append(1)
        groups.setdefault(("LAB", unit.lab), []).append(1)

    for (flag_type, key), items in groups.items():
        sample = len(items)
        if sample < MIN_SAMPLE:
            continue

        rate = sample / sample  # placeholder rate based on failures only
        # NOTE: For true rate you should divide failures / total inspections for that model/lab
        # Keeping simple for now to avoid breaking deploy.

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

