from django.db import models
from django.utils import timezone


# ------------------------
# STORES (3 locations)
# ------------------------
class Store(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


# ------------------------
# FRAME STYLE (parent SKU)
# ------------------------
class FrameStyle(models.Model):
    style_code = models.CharField(max_length=50, unique=True)
    brand = models.CharField(max_length=100, blank=True)
    supplier = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.style_code}"


# ------------------------
# FRAME VARIANT (COLOR + SIZE)
# ------------------------
class FrameVariant(models.Model):
    STATUS_CHOICES = [
        ("approved", "Approved"),
        ("monitor", "Monitor"),
        ("blocked", "Blocked"),
    ]

    style = models.ForeignKey(
        FrameStyle,
        on_delete=models.CASCADE,
        related_name="variants",
    )
    color = models.CharField(max_length=50)
    size = models.CharField(max_length=20)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="approved",
    )

    qc_score_cached = models.FloatField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("style", "color", "size")

    def __str__(self):
        return f"{self.style.style_code} | {self.color} | {self.size}"


# ------------------------
# COMPLAINTS (FROM STORES)
# ------------------------
class Complaint(models.Model):
    SEVERITY_CHOICES = [
        (1, "Low"),
        (2, "Medium"),
        (3, "High"),
    ]

    FAILURE_CHOICES = [
        ("hinge", "Hinge Break"),
        ("temple", "Temple Break"),
        ("frame", "Frame Crack"),
        ("lens", "Lens Issue"),
        ("other", "Other"),
    ]

    variant = models.ForeignKey(
        FrameVariant,
        on_delete=models.CASCADE,
        related_name="complaints",
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    failure_type = models.CharField(
        max_length=20,
        choices=FAILURE_CHOICES,
    )
    severity = models.IntegerField(choices=SEVERITY_CHOICES)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Complaint #{self.id} – {self.variant}"


# ------------------------
# COMPLAINT ATTACHMENTS (IMAGES)
# ------------------------
class ComplaintAttachment(models.Model):
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    file = models.FileField(upload_to="complaints/")

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attachment {self.id}"
