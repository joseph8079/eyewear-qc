# qc/models.py
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


# =============================================================================
# Store
# =============================================================================
class Store(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True, default="DEFAULT")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


# =============================================================================
# Unit (Frame)
# =============================================================================
class Unit(models.Model):
    PRIORITY_CHOICES = [
        ("NORMAL", "Normal"),
        ("URGENT", "Urgent"),
    ]

    STATUS_CHOICES = [
        ("RECEIVED", "Received"),
        ("QC_IN_PROGRESS", "QC In Progress"),
        ("STORE_READY", "Store Ready"),
        ("REWORK", "Rework"),
        ("QUARANTINE", "Quarantine"),
        ("RETEST", "Retest"),
    ]

    unit_id = models.CharField(max_length=64, unique=True)
    order_id = models.CharField(max_length=64, blank=True, null=True)

    frame_model = models.CharField(max_length=255, blank=True, default="")
    lab = models.CharField(max_length=255, blank=True, default="")

    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="NORMAL")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="RECEIVED")

    # Optional link to store (safe if you want it; null OK)
    store = models.ForeignKey(Store, on_delete=models.SET_NULL, null=True, blank=True)

    received_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-received_at"]

    def __str__(self) -> str:
        return self.unit_id


# =============================================================================
# Inspection
# =============================================================================
class Inspection(models.Model):
    RESULT_CHOICES = [
        ("PASS", "Pass"),
        ("FAIL", "Fail"),
    ]

    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="inspections")
    attempt_number = models.PositiveIntegerField(default=1)

    tech_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="qc_inspections",
    )

    training_mode_used = models.BooleanField(default=False)

    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    final_result = models.CharField(max_length=10, choices=RESULT_CHOICES, blank=True, default="")

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"Inspection {self.id} ({self.unit.unit_id}) Attempt {self.attempt_number}"


# =============================================================================
# Inspection stage results
# =============================================================================
class InspectionStageResult(models.Model):
    STAGE_CHOICES = [
        ("INTAKE", "Intake"),
        ("COSMETIC", "Cosmetic"),
        ("FIT", "Fit"),
        ("DECISION", "Decision"),
    ]

    STATUS_CHOICES = [
        ("PASS", "Pass"),
        ("FAIL", "Fail"),
    ]

    inspection = models.ForeignKey(Inspection, on_delete=models.CASCADE, related_name="stage_results")
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PASS")

    notes = models.TextField(blank=True, default="")
    data = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = [("inspection", "stage")]
        ordering = ["inspection_id", "stage"]

    def __str__(self) -> str:
        return f"{self.inspection_id}:{self.stage} ({self.status})"


# =============================================================================
# Defects
# =============================================================================
class Defect(models.Model):
    SEVERITY_CHOICES = [
        ("LOW", "Low"),
        ("MED", "Medium"),
        ("HIGH", "High"),
    ]

    stage_result = models.ForeignKey(
        InspectionStageResult, on_delete=models.CASCADE, related_name="defects"
    )

    category = models.CharField(max_length=100, default="UNKNOWN")
    reason_code = models.CharField(max_length=100, default="UNKNOWN")
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default="LOW")

    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"Defect {self.id} ({self.category}/{self.reason_code})"


class DefectPhoto(models.Model):
    defect = models.ForeignKey(Defect, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="defect_photos/")
    annotation_json = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"DefectPhoto {self.id} (defect {self.defect_id})"


# =============================================================================
# Rework tickets
# =============================================================================
class ReworkTicket(models.Model):
    STATUS_CHOICES = [
        ("OPEN", "Open"),
        ("IN_PROGRESS", "In Progress"),
        ("DONE", "Done"),
        ("CLOSED", "Closed"),
    ]

    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="rework_tickets")
    inspection = models.ForeignKey(
        Inspection, on_delete=models.SET_NULL, null=True, blank=True, related_name="rework_tickets"
    )

    failed_stage = models.CharField(max_length=20, default="COSMETIC")
    reason_summary = models.TextField(default="Failed QC")

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rework_assigned",
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="OPEN")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"ReworkTicket {self.id} ({self.unit.unit_id})"


# =============================================================================
# Quality flags
# =============================================================================
class QualityFlag(models.Model):
    FLAG_TYPE_CHOICES = [
        ("MODEL", "Model"),
        ("LAB", "Lab"),
    ]

    flag_type = models.CharField(max_length=20, choices=FLAG_TYPE_CHOICES)
    flag_key = models.CharField(max_length=255)

    window_start = models.DateTimeField()
    window_end = models.DateTimeField()

    sample_size = models.PositiveIntegerField(default=0)
    defect_rate = models.FloatField(default=0.0)
    threshold = models.FloatField(default=10.0)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["flag_type", "flag_key"]),
            models.Index(fields=["window_start", "window_end"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.flag_type}:{self.flag_key} ({self.defect_rate:.1f}%)"


# =============================================================================
# Complaints
# =============================================================================
class Complaint(models.Model):
    STATUS_CHOICES = [
        ("OPEN", "Open"),
        ("IN_PROGRESS", "In Progress"),
        ("RESOLVED", "Resolved"),
        ("CLOSED", "Closed"),
    ]

    CATEGORY_CHOICES = [
        ("OTHER", "Other"),
        ("LENS", "Lens"),
        ("FRAME", "Frame"),
        ("COSMETIC", "Cosmetic"),
        ("FIT", "Fit"),
        ("RX", "RX"),
        ("SHIPPING", "Shipping"),
    ]

    store = models.ForeignKey(Store, on_delete=models.SET_NULL, null=True, blank=True)
    unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True)

    unit_id_text = models.CharField(max_length=64, null=True, blank=True)
    order_id_text = models.CharField(max_length=64, null=True, blank=True)

    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default="OTHER")
    title = models.CharField(max_length=255, default="")
    description = models.TextField(blank=True, default="")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="OPEN")

    # KEY FIX: allow NULL so old rows can migrate without failing
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaints_created",
    )

    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaints_resolved",
    )

    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Complaint {self.id}: {self.title}"


class ComplaintAttachment(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="complaint_attachments/")
    note = models.TextField(blank=True, default="")

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaint_attachments",
    )

    uploaded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self) -> str:
        return f"Attachment {self.id} (complaint {self.complaint_id})"
