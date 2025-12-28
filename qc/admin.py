from django.contrib import admin
from .models import Store, FrameStyle, FrameVariant, Complaint, ComplaintAttachment


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(FrameStyle)
class FrameStyleAdmin(admin.ModelAdmin):
    search_fields = ("style_code", "supplier")


@admin.register(FrameVariant)
class FrameVariantAdmin(admin.ModelAdmin):
    list_display = ("sku", "style", "color", "size", "status", "qc_score_cached", "created_at")
    list_filter = ("status", "style__supplier")
    search_fields = ("sku", "style__style_code", "style__supplier")


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ("variant", "store", "failure_type", "severity", "created_at")
    list_filter = ("failure_type", "severity", "store")
    search_fields = ("variant__sku", "variant__style__style_code", "notes")


@admin.register(ComplaintAttachment)
class ComplaintAttachmentAdmin(admin.ModelAdmin):
    list_display = ("complaint", "file", "uploaded_at")
