from django.core.management.base import BaseCommand
from qc.services.flags import refresh_quality_flags


class Command(BaseCommand):
    help = "Run QC quality flag checks"

    def handle(self, *args, **kwargs):
        refresh_quality_flags()
        self.stdout.write("QC flags refreshed")
