# qc/models.py
from __future__ import annotations

from django.db import models
from django.contrib.auth.models import User


# -------------------------
# Stores (3 locations)
# -------------------------
class Store(models.Model):
    code = models.CharField(max_length=32, unique=True)  # e.g. WILLIAMSBURG / MONROE / BORO_PARK
    name = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


# -------------------------
# Units / Frames
# -------------------------
class Unit(models.Model):
    unit_id = models.CharField(max_length=64, unique=True)
    order_id = models.CharField(max_length=64, blank=True, null=True)
    frame_model = models.CharField(max_length=128)
    lab = models.CharField(max_length=128)

    # ✅ this is what Render is complaining about
    store = models.ForeignKey(
        Store,
        on_delete=models.PROTECT,
        related_name="units",
        null=True,
        blank=True,
    )

    priority = models.CharField(
        max_length=16,
        choices=[("NORMAL", "NORMAL"), ("URGENT", "URGENT")],
        default="NORMAL",
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
        ],
        default="RECEIVED",
    )

    received_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.unit_id


# -------------------------
# Inspection
# -------------------------
class Inspection(models.Model):
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    attempt_number = models.PositiveIntegerField(default=1)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    final_result = models.CharField(
        max_length=8,
        choices=[("PASS", "PASS"), ("FAIL", "FAIL")],
        blank=True,
        null=True,
    )

    training_mode_used = models.BooleanField(default=False)
    tech_user = models.ForeignKey(User, on_delete=models.PROTECT)

    def __str__(self) -> str:
        return f"{self.unit.unit_id} attempt {self.attempt_number}"


class InspectionStageResult(models.Model):
    inspection = models.ForeignKey(Inspection, on_delete=models.CASCADE)

    stage = models.CharField(
        max_length=32,
        choices=[
            ("INTAKE", "INTAKE"),
            ("COSMETIC", "COSMETIC"),
            ("RX", "RX"),
            ("FIT", "FIT"),
            ("FINAL_PREP", "FINAL_PREP"),
            ("DECISION", "DECISION"),
        ],
    )

    status = models.CharField(
        max_length=8,
        choices=[("PASS", "PASS"), ("FAIL", "FAIL")],
    )

    notes = models.TextField(blank=True)
    data = models.JSONField(blank=True, null=True)

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(auto_now=True)


class Defect(models.Model):
    stage_result = models.ForeignKey(InspectionStageResult, on_delete=models.CASCADE)
    category = models.CharField(max_length=32)
    reason_code = models.CharField(max_length=64)

    severity = models.CharField(
        max_length=8,
        choices=[("LOW", "LOW"), ("MED", "MED"), ("HIGH", "HIGH")],
    )

    notes = models.TextField(blank=True)


class DefectPhoto(models.Model):
    defect = models.ForeignKey(Defect, on_delete=models.CASCADE)
    image = models.ImageField(upload_to="qc_defects/")
    annotation_json = models.JSONField(blank=True, null=True)


class ReworkTicket(models.Model):
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    inspection = models.ForeignKey(Inspection, on_delete=models.CASCADE)

    failed_stage = models.CharField(max_length=32)
    reason_summary = models.TextField()

    assigned_to = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)

    status = models.CharField(
        max_length=16,
        choices=[("OPEN", "OPEN"), ("IN_PROGRESS", "IN_PROGRESS"), ("DONE", "DONE")],
        default="OPEN",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(blank=True, null=True)


class QualityFlag(models.Model):
    flag_type = models.CharField(
        max_length=16,
        choices=[("MODEL", "MODEL"), ("LAB", "LAB")],
    )

    flag_key = models.CharField(max_length=128)
    window_start = models.DateTimeField()
    window_end = models.DateTimeField()

    sample_size = models.PositiveIntegerField()
    defect_rate = models.FloatField()
    threshold = models.FloatField()

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(blank=True, null=True)


# -------------------------
# Complaints
# -------------------------
class Complaint(models.Model):
    CATEGORY_CHOICES = [
        ("COSMETIC", "COSMETIC"),
        ("FIT", "FIT"),
        ("RX", "RX"),
        ("LAB", "LAB"),
        ("OTHER", "OTHER"),
    ]
    STATUS_CHOICES = [
        ("OPEN", "OPEN"),
        ("IN_PROGRESS", "IN_PROGRESS"),
        ("RESOLVED", "RESOLVED"),
    ]

    store = models.ForeignKey(Store, on_delete=models.PROTECT, related_name="complaints")
    unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True, related_name="complaints")

    unit_id_text = models.CharField(max_length=64, blank=True, null=True)
    order_id_text = models.CharField(max_length=64, blank=True, null=True)

    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, default="OTHER")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="OPEN")

    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="complaints_created")
    created_at = models.DateTimeField(auto_now_add=True)

    resolved_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name="complaints_resolved")
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"{self.store.code}: {self.title}"


class ComplaintAttachment(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="complaints/")
    note = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT)
    uploaded_at = models.DateTimeField(auto_now_add=True)
