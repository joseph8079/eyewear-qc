from django.utils.timezone import now, timedelta
from qc.models import Inspection, InspectionStageResult, Unit, ReworkTicket


def pass_rate(days=7):
    start = now() - timedelta(days=days)
    total = Inspection.objects.filter(started_at__gte=start).count()
    passed = Inspection.objects.filter(
        started_at__gte=start, final_result="PASS"
    ).count()
    return 0 if total == 0 else round(passed / total * 100, 2)


def first_pass_yield(days=7):
    start = now() - timedelta(days=days)
    inspections = Inspection.objects.filter(
        started_at__gte=start, attempt_number=1, final_result="PASS"
    )

    reworked_units = ReworkTicket.objects.filter(
        inspection__in=inspections
    ).values_list("unit_id", flat=True)

    fp_units = inspections.exclude(unit_id__in=reworked_units).count()
    total = inspections.count()

    return 0 if total == 0 else round(fp_units / total * 100, 2)


def avg_qc_time(days=7):
    start = now() - timedelta(days=days)
    inspections = Inspection.objects.filter(
        started_at__gte=start, completed_at__isnull=False
    )

    times = [
        (i.completed_at - i.started_at).total_seconds()
        for i in inspections
    ]

    return 0 if not times else round(sum(times) / len(times) / 60, 2)


def bottleneck_stage(days=7):
    start = now() - timedelta(days=days)
    stages = InspectionStageResult.objects.filter(started_at__gte=start)

    durations = {}
    for s in stages:
        dur = (s.completed_at - s.started_at).total_seconds()
        durations.setdefault(s.stage, []).append(dur)

    avg = {
        stage: sum(times) / len(times)
        for stage, times in durations.items()
    }

    return max(avg, key=avg.get) if avg else None
