# qc/management/commands/seed_data.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from qc.models import Unit

DEFAULT_STORES = ["Williamsburg", "Monroe", "Boro Park"]
DEFAULT_LABS = ["Lab A", "Lab B"]
DEFAULT_MODELS = ["Model 100", "Model 200", "Model 300"]


class Command(BaseCommand):
    help = "Seed initial sample data (stores/labs/models) - lightweight version"

    def handle(self, *args, **options):
        # NOTE: your current models store store as text? If you add a Store model later, update here.
        self.stdout.write(self.style.WARNING("Seed script is lightweight. Your current schema stores lab/model as text fields."))

        # Create sample Units so the UI has something to show
        for i in range(1, 6):
            Unit.objects.get_or_create(
                unit_id=f"U-{i:04d}",
                defaults={
                    "order_id": f"ORD-{i:04d}",
                    "frame_model": DEFAULT_MODELS[i % len(DEFAULT_MODELS)],
                    "lab": DEFAULT_LABS[i % len(DEFAULT_LABS)],
                    "priority": "NORMAL",
                    "status": "RECEIVED",
                },
            )

        self.stdout.write(self.style.SUCCESS("Seeded sample Units."))
