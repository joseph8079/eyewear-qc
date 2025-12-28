class FrameVariant(models.Model):
    style = models.ForeignKey(FrameStyle, on_delete=models.CASCADE)
    sku = models.CharField(max_length=100, unique=True)
    color = models.CharField(max_length=50)
    size = models.CharField(max_length=50)

    supplier = models.CharField(max_length=100)

    reference_images = models.FileField(
        upload_to="frames/reference/",
        blank=True,
        null=True,
        help_text="Factory or sample images/specs"
    )

    status = models.CharField(
        max_length=20,
        choices=[
            ("APPROVED", "Approved"),
            ("WATCH", "Watch"),
            ("HOLD", "Hold"),
            ("PULLED", "Pulled"),
        ],
        default="APPROVED",
    )

    qc_score_cached = models.IntegerField(default=100)

    def __str__(self):
        return self.sku

