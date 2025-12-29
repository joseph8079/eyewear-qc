
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Q, Avg
from qc.models import Unit, Inspection, InspectionStageResult, Defect, QualityFlag


def counts_overview():
    """Dashboard counts: not inspected yet, passed, failed."""
    not_inspected = Unit.objects.filter(status="RECEIVED").count()
    passed = Unit.objects.filter(status="STORE_READY").count()
    failed = Unit.objects.filter(status__in=["REWORK", "RETEST", "QUARANTINE"]).count()
    in_progress = Unit.objects.filter(status="QC_IN_PROGRESS").count()
    return {
        "not_inspected": not_inspected,
        "in_progress": in_progress,
        "passed": passed,
        "failed": failed,
    }


def first_pass_yield(days=7):
    """Pass with zero rework: first inspection PASS and unit went STORE_READY without REWORK/RETEST on later attempts."""
    since = timezone.now() - timedelta(days=days)

    # Units that completed at least one inspection in window
    completed = Inspection.objects.filter(completed_at__gte=since).values_list("unit_id", flat=True).distinct()
    if not completed:
        return {"fpy": 0.0, "numerator": 0, "denominator": 0}

    # First inspection per unit: attempt_number=1 and PASS
    first_pass_units = set(
        Inspection.objects.filter(unit_id__in=completed, attempt_number=1, final_result="PASS")
        .values_list("unit_id", flat=True)
        .distinct()
    )

    # Any unit that had rework/retest statuses at any time after
    bad_units = set(Unit.objects.filter(id__in=completed, status__in=["REWORK", "RETEST", "QUARANTINE"]).values_list("id", flat=True))

    numerator = len(first_pass_units - bad_units)
    denominator = len(set(completed))
    fpy = (numerator / denominator) * 100.0 if denominator else 0.0
    return {"fpy": round(fpy, 2), "numerator": numerator, "denominator": denominator}


def avg_qc_time_hours(days=7):
    """Average hours from inspection started -> completed."""
    since = timezone.now() - timedelta(days=days)
    qs = Inspection.objects.filter(completed_at__isnull=False, started_at__gte=since)
    # avg duration in seconds:
    durations = []
    for ins in qs.only("started_at", "completed_at"):
        durations.append((ins.completed_at - ins.started_at).total_seconds())
    if not durations:
        return 0.0
    return round(sum(durations) / len(durations) / 3600.0, 2)


def urgent_sla_breaches(hours_threshold=6):
    """Urgent jobs stuck > X hours (RECEIVED or QC_IN_PROGRESS)"""
    cutoff = timezone.now() - timedelta(hours=hours_threshold)
    qs = Unit.objects.filter(priority="URGENT", status__in=["RECEIVED", "QC_IN_PROGRESS"], received_at__lte=cutoff)
    return qs.count()


def defect_rate_by_key(flag_type="MODEL", days=7, min_sample=10):
    """
    Returns list of dicts: key, sample_size, defect_rate%
    - sample_size = inspections completed in window for that key
    - defect_rate = units with FAIL (final_result=FAIL) / total
    """
    since = timezone.now() - timedelta(days=days)

    inspections = Inspection.objects.filter(completed_at__gte=since, final_result__in=["PASS", "FAIL"]).select_related("unit")

    buckets = {}
    for ins in inspections:
        key = ins.unit.frame_model if flag_type == "MODEL" else ins.unit.lab
        if key not in buckets:
            buckets[key] = {"total": 0, "fails": 0}
        buckets[key]["total"] += 1
        if ins.final_result == "FAIL":
            buckets[key]["fails"] += 1

    out = []
    for key, v in buckets.items():
        if v["total"] < min_sample:
            continue
        rate = (v["fails"] / v["total"]) * 100.0
        out.append({"key": key, "sample_size": v["total"], "defect_rate": round(rate, 2)})
    out.sort(key=lambda x: x["defect_rate"], reverse=True)
    return out


def auto_flag(defect_threshold_percent=10.0, days=7, min_sample=10):
    """
    Auto create/update QualityFlag when MODEL or LAB exceeds threshold in last 7 days.
    """
    now = timezone.now()
    window_start = now - timedelta(days=days)

    for flag_type in ["MODEL", "LAB"]:
        rates = defect_rate_by_key(flag_type=flag_type, days=days, min_sample=min_sample)
        for r in rates:
            if r["defect_rate"] < defect_threshold_percent:
                continue

            flag, created = QualityFlag.objects.get_or_create(
                flag_type=flag_type,
                flag_key=r["key"],
                window_start=window_start,
                window_end=now,
                defaults={
                    "sample_size": r["sample_size"],
                    "defect_rate": r["defect_rate"],
                    "threshold": defect_threshold_percent,
                    "is_active": True,
                },
            )
            if not created:
                flag.sample_size = r["sample_size"]
                flag.defect_rate = r["defect_rate"]
                flag.threshold = defect_threshold_percent
                flag.window_start = window_start
                flag.window_end = now
                flag.is_active = True
                flag.save()

    return True
