from django.utils.timezone import now, timedelta
from qc.models import Inspection, InspectionStageResult, ReworkTicket


def pass_rate(days=7):
    start = now() - timedelta(days=days)
    total = Inspection.objects.filter(started_at__gte=start).count()
    passed = Inspection.objects.filter(started_at__gte=start, final_result="PASS").count()
    return 0 if total == 0 else round((passed / total) * 100, 2)


def first_pass_yield(days=7):
    start = now() - timedelta(days=days)

    first_pass = Inspection.objects.filter(
        started_at__gte=start,
        attempt_number=1,
        final_result="PASS"
    )

    # Units that had rework on that first attempt are NOT FPY
    reworked_unit_ids = set(
        ReworkTicket.objects.filter(inspection__in=first_pass)
        .values_list("unit_id", flat=True)
    )

    fp_count = first_pass.exclude(unit_id__in=reworked_unit_ids).count()
    total = first_pass.count()
    return 0 if total == 0 else round((fp_count / total) * 100, 2)


def avg_qc_time(days=7):
    start = now() - timedelta(days=days)
    qs = Inspection.objects.filter(started_at__gte=start, completed_at__isnull=False)

    secs = [
        (i.completed_at - i.started_at).total_seconds()
        for i in qs
        if i.completed_at and i.started_at
    ]
    return 0 if not secs else round((sum(secs) / len(secs)) / 60, 2)


def bottleneck_stage(days=7):
    start = now() - timedelta(days=days)
    qs = InspectionStageResult.objects.filter(started_at__gte=start)

    durations = {}
    for r in qs:
        dur = (r.completed_at - r.started_at).total_seconds()
        durations.setdefault(r.stage, []).append(dur)

    if not durations:
        return None

    avg = {k: sum(v) / len(v) for k, v in durations.items()}
    return max(avg, key=avg.get)
