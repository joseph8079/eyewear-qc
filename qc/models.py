from django.db import models


class Store(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class FrameStyle(models.Model):
    style_code = models.CharField(max_length=50, unique=True)
    supplier = models.CharField(max_length=120, blank=True, default="")

    def __str__(self):
        return self.style_code


class FrameVariant(models.Model):
    STATUS_CHOICES = [
        ("OK", "OK (on shelf)"),
        ("HOLD", "Hold (watch)"),
        ("OFF", "Off shelf"),
    ]

    style = models.ForeignKey(FrameStyle, on_delete=models.CASCADE, related_name="frames")

    # ✅ THIS fixes your error:
    sku = models.CharField(max_length=80, unique=True)

    color = models.CharField(max_length=50, blank=True, default="")
    size = models.CharField(max_length=50, blank=True, default="")

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="OK")
    qc_score_cached = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.style.style_code} - {self.sku}"


class Complaint(models.Model):
    SEVERITY_CHOICES = [
        ("LOW", "Low"),
        ("MED", "Medium"),
        ("HIGH", "High"),
    ]

    FAILURE_CHOICES = [
        ("HINGE", "Hinge"),
        ("ARM", "Arm/Temple"),
        ("BRIDGE", "Bridge"),
        ("SCREW", "Screw"),
        ("LENS", "Lens Issue"),
        ("OTHER", "Other"),
    ]

    variant = models.ForeignKey(FrameVariant, on_delete=models.CASCADE, related_name="complaints")
    store = models.ForeignKey(Store, on_delete=models.SET_NULL, null=True, blank=True)

    failure_type = models.CharField(max_length=20, choices=FAILURE_CHOICES, default="OTHER")
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default="LOW")
    notes = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Complaint: {self.variant.sku} ({self.failure_type})"


class ComplaintAttachment(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="complaints/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attachment for complaint {self.complaint_id}"
