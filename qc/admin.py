from django.contrib import admin
from .models import Store, FrameStyle, FrameVariant, Complaint, ComplaintAttachment


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(FrameStyle)
class FrameStyleAdmin(admin.ModelAdmin):
    list_display = ("style_code", "supplier")
    search_fields = ("style_code", "supplier")


@admin.register(FrameVariant)
class FrameVariantAdmin(admin.ModelAdmin):
    list_display = ("sku", "style", "color", "size", "status", "qc_score_cached")
    list_filter = ("status", "style")
    search_fields = ("sku", "style__style_code", "color", "size")


class ComplaintAttachmentInline(admin.TabularInline):
    model = ComplaintAttachment
    extra = 0


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ("variant", "store", "failure_type", "severity", "created_at")
    list_filter = ("store", "failure_type", "severity", "created_at")
    search_fields = ("variant__sku", "variant__style__style_code", "notes")
    inlines = [ComplaintAttachmentInline]


@admin.register(ComplaintAttachment)
class ComplaintAttachmentAdmin(admin.ModelAdmin):
    list_display = ("complaint", "file", "uploaded_at")
