from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


# -----------------------------
# Core reference data
# -----------------------------
class Store(models.Model):
    name = models.CharField(max_length=128, unique=True)

    def __str__(self):
        return self.name


class FrameModel(models.Model):
    """
    Catalog of frame models (for import/upload template + analytics by model).
    """
    model_name = models.CharField(max_length=128, unique=True)
    brand = models.CharField(max_length=128, blank=True, default="")

    def __str__(self):
        return self.model_name


class Lab(models.Model):
    """
    Catalog of labs (for analytics by lab + auto flags).
    """
    name = models.CharField(max_length=128, unique=True)

    def __str__(self):
        return self.name


# -----------------------------
# Units + QC workflow
# -----------------------------
class Unit(models.Model):
    """
    A single physical job/unit coming in for QC.
    """
    unit_id = models.CharField(max_length=64, unique=True)
    order_id = models.CharField(max_length=64, blank=True, null=True)

    store = models.ForeignKey(Store, on_delete=models.PROTECT, related_name="units")
    frame_model = models.ForeignKey(FrameModel, on_delete=models.PROTECT, related_name="units")
    lab = models.ForeignKey(Lab, on_delete=models.PROTECT, related_name="units")

    priority = models.CharField(
        max_length=16,
        choices=[("NORMAL", "NORMAL"), ("URGENT", "URGENT")],
        default="NORMAL"
    )

    status = models.CharField(
        max_length=32,
        choices=[
            ("RECEIVED", "RECEIVED"),
            ("QC_IN_PROGRESS", "QC_IN_PROGRESS"),
            ("REWORK", "REWORK"),
            ("RETEST", "RETEST"),
            ("STORE_READY", "STORE_READY"),
            ("QUARANTINE", "QUARANTINE"),
            ("FAILED", "FAILED"),
        ],
        default="RECEIVED"
    )

    received_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.unit_id


class Inspection(models.Model):
    """
    Each attempt of QC on a unit.
    """
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="inspections")
    attempt_number = models.PositiveIntegerField(default=1)

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    final_result = models.CharField(
        max_length=8,
        choices=[("PASS", "PASS"), ("FAIL", "FAIL")],
        blank=True,
        null=True
    )

    training_mode_used = models.BooleanField(default=False)
    tech_user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="inspections")

    def __str__(self):
        return f"{self.unit.unit_id} attempt {self.attempt_number}"


class InspectionStageResult(models.Model):
    """
    Stage results. We keep 4-step deep inspection as requested:
    - COSMETIC_DEEP (bending/throwing stress + deep cosmetic checks)
    - RX
    - FIT
    - FINAL_DECISION
    """
    inspection = models.ForeignKey(Inspection, on_delete=models.CASCADE, related_name="stages")

    stage = models.CharField(
        max_length=48,
        choices=[
            ("INTAKE", "INTAKE"),
            ("COSMETIC_DEEP", "COSMETIC_DEEP"),
            ("RX", "RX"),
            ("FIT", "FIT"),
            ("FINAL_DECISION", "FINAL_DECISION"),
        ]
    )

    status = models.CharField(
        max_length=8,
        choices=[("PASS", "PASS"), ("FAIL", "FAIL")]
    )

    notes = models.TextField(blank=True)
    data = models.JSONField(blank=True, null=True)  # store measurements/checklist

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(auto_now=True)


class Defect(models.Model):
    stage_result = models.ForeignKey(InspectionStageResult, on_delete=models.CASCADE, related_name="defects")
    category = models.CharField(max_length=64)
    reason_code = models.CharField(max_length=128)

    severity = models.CharField(
        max_length=8,
        choices=[("LOW", "LOW"), ("MED", "MED"), ("HIGH", "HIGH")]
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)


class DefectPhoto(models.Model):
    """
    Photo annotation enabled:
    - annotation_json stores circles/boxes
    """
    defect = models.ForeignKey(Defect, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="qc_defects/")
    annotation_json = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ReworkTicket(models.Model):
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="rework_tickets")
    inspection = models.ForeignKey(Inspection, on_delete=models.CASCADE, related_name="rework_tickets")

    failed_stage = models.CharField(max_length=48)
    reason_summary = models.TextField()

    assigned_to = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name="assigned_rework")

    status = models.CharField(
        max_length=16,
        choices=[
            ("OPEN", "OPEN"),
            ("IN_PROGRESS", "IN_PROGRESS"),
            ("DONE", "DONE"),
        ],
        default="OPEN"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(blank=True, null=True)


class QualityFlag(models.Model):
    """
    Auto-flag if a model/lab exceeds defect threshold in last 7 days.
    """
    flag_type = models.CharField(
        max_length=16,
        choices=[("MODEL", "MODEL"), ("LAB", "LAB")]
    )

    flag_key = models.CharField(max_length=128)  # model_name or lab_name
    window_start = models.DateTimeField()
    window_end = models.DateTimeField()

    sample_size = models.PositiveIntegerField()
    defect_rate = models.FloatField()
    threshold = models.FloatField()

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.flag_type}:{self.flag_key} ({self.defect_rate:.2%})"


# -----------------------------
# Complaints (RESTORED)
# -----------------------------
class Complaint(models.Model):
    """
    Complaint / issue report (restores the “complaints section”).
    Can be linked to a Unit when known.
    """
    store = models.ForeignKey(Store, on_delete=models.PROTECT, related_name="complaints")
    unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True, related_name="complaints")

    title = models.CharField(max_length=160)
    description = models.TextField()

    status = models.CharField(
        max_length=16,
        choices=[
            ("OPEN", "OPEN"),
            ("INVESTIGATING", "INVESTIGATING"),
            ("RESOLVED", "RESOLVED"),
        ],
        default="OPEN"
    )

    severity = models.CharField(
        max_length=8,
        choices=[("LOW", "LOW"), ("MED", "MED"), ("HIGH", "HIGH")],
        default="MED"
    )

    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="complaints_created")
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(blank=True, null=True)

    def mark_resolved(self):
        self.status = "RESOLVED"
        self.resolved_at = timezone.now()
        self.save(update_fields=["status", "resolved_at"])

    def __str__(self):
        return f"{self.title} ({self.status})"


class ComplaintAttachment(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="attachments")
    image = models.ImageField(upload_to="qc_complaints/")
    note = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
# qc/models.py  (ADD THESE AT THE BOTTOM — keep your existing models above)

from django.conf import settings


class Store(models.Model):
    """
    3 stores supported. You can create them in Admin:
    - Williamsburg
    - Monroe
    - Boro Park
    """
    name = models.CharField(max_length=128, unique=True)
    code = models.CharField(max_length=32, unique=True)  # e.g. WBG, MNR, BRP
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class Complaint(models.Model):
    STATUS_CHOICES = [
        ("OPEN", "OPEN"),
        ("IN_REVIEW", "IN_REVIEW"),
        ("RESOLVED", "RESOLVED"),
        ("REJECTED", "REJECTED"),
    ]

    CATEGORY_CHOICES = [
        ("COSMETIC", "COSMETIC"),
        ("FIT", "FIT"),
        ("RX", "RX"),
        ("MISSING_PARTS", "MISSING_PARTS"),
        ("OTHER", "OTHER"),
    ]

    store = models.ForeignKey(Store, on_delete=models.PROTECT, related_name="complaints")

    # Optional link to unit (if complaint is about a specific unit)
    unit = models.ForeignKey("Unit", on_delete=models.SET_NULL, null=True, blank=True, related_name="complaints")

    # Optional plain-text identifiers (in case unit not found / not created yet)
    unit_id_text = models.CharField(max_length=64, blank=True, null=True)
    order_id_text = models.CharField(max_length=64, blank=True, null=True)

    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, default="OTHER")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="OPEN")

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="complaints_created")
    created_at = models.DateTimeField(auto_now_add=True)

    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="complaints_resolved"
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.store.code} • {self.title} • {self.status}"


class ComplaintAttachment(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="attachments")

    # Use ImageField so you can preview images. Pillow is already in requirements.
    file = models.ImageField(upload_to="complaints/")
    note = models.CharField(max_length=200, blank=True)

    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attachment {self.id} for Complaint {self.complaint_id}"

