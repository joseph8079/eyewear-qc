from datetime import timedelta
from django.utils import timezone

from qc.models import Unit


def urgent_sla_breaches(stuck_hours=12):
    """
    Returns urgent units that exceeded SLA time (hours).
    """
    now = timezone.now()
    cutoff = now - timedelta(hours=stuck_hours)
    qs = Unit.objects.filter(priority="URGENT", received_at__lte=cutoff).exclude(status="STORE_READY")
    return qs
