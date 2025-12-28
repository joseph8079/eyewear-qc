from django.conf import settings
from django.db import models
from django.utils import timezone


class Store(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class FrameStyle(models.Model):
    style_code = models.CharField(max_length=50, unique=True)
    supplier_name = models.CharField(max_length=100)
    material = models.CharField(max_length=50)

    def __str__(self):
        return self.style_code


class FrameVariant(models.Model):
    STATUS_CHOICES = [
        ("APPROVED", "Approved"),
        ("WATCH", "Watch"),
        ("HOLD", "Hold"),
        ("PULLED", "Pulled"),
    ]

    style = models.ForeignKey(FrameStyle, on_delete=models.CASCADE)
    sku = models.CharField(max_length=100, unique=True)
    color = models.CharField(max_length=50)
    size = models.CharField(max_length=20)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="APPROVED")
    qc_score_cached = models.IntegerField(default=100)

    def __str__(self):
        return self.sku


class Complaint(models.Model):
    variant = models.ForeignKey(FrameVariant, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    failure_type = models.CharField(max_length=50)
    severity = models.CharField(max_length=10)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.variant.sku} - {self.failure_type}"


class Attachment(models.Model):
    complaint = models.ForeignKey(Complaint, related_name="attachments", on_delete=models.CASCADE)
    file = models.FileField(upload_to="complaints/")
