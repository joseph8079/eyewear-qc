

from django.contrib import admin

from .models import (
    Unit,
    Inspection,
    InspectionStageResult,
    Defect,
    DefectPhoto,
    ReworkTicket,
    QualityFlag,
    Store,
    Complaint,
    ComplaintAttachment,
)


# ----------------------------
# QC MODELS
# ----------------------------

@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("unit_id", "order_id", "frame_model", "lab", "priority", "status", "received_at")
    list_filter = ("priority", "status", "lab", "frame_model")
    search_fields = ("unit_id", "order_id", "frame_model", "lab")
    date_hierarchy = "received_at"
    ordering = ("-received_at",)


@admin.register(Inspection)
class InspectionAdmin(admin.ModelAdmin):
    list_display = ("unit", "attempt_number", "final_result", "tech_user", "training_mode_used", "started_at", "completed_at")
    list_filter = ("final_result", "training_mode_used", "tech_user")
    search_fields = ("unit__unit_id", "unit__order_id", "tech_user__username", "tech_user__email")
    date_hierarchy = "started_at"
    ordering = ("-started_at",)


@admin.register(InspectionStageResult)
class InspectionStageResultAdmin(admin.ModelAdmin):
    list_display = ("inspection", "stage", "status", "started_at", "completed_at")
    list_filter = ("stage", "status")
    search_fields = ("inspection__unit__unit_id", "inspection__unit__order_id")
    date_hierarchy = "started_at"
    ordering = ("-started_at",)


@admin.register(Defect)
class DefectAdmin(admin.ModelAdmin):
    list_display = ("id", "stage_result", "category", "reason_code", "severity")
    list_filter = ("severity", "category", "reason_code")
    search_fields = (
        "category",
        "reason_code",
        "notes",
        "stage_result__inspection__unit__unit_id",
        "stage_result__inspection__unit__order_id",
    )
    ordering = ("-id",)


@admin.register(DefectPhoto)
class DefectPhotoAdmin(admin.ModelAdmin):
    list_display = ("id", "defect", "image")
    search_fields = ("defect__reason_code", "defect__category")
    ordering = ("-id",)


@admin.register(ReworkTicket)
class ReworkTicketAdmin(admin.ModelAdmin):
    list_display = ("id", "unit", "inspection", "failed_stage", "status", "assigned_to", "created_at", "closed_at")
    list_filter = ("status", "failed_stage", "assigned_to")
    search_fields = ("unit__unit_id", "unit__order_id", "reason_summary")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)


@admin.register(QualityFlag)
class QualityFlagAdmin(admin.ModelAdmin):
    list_display = ("id", "flag_type", "flag_key", "defect_rate", "threshold", "sample_size", "is_active", "created_at")
    list_filter = ("flag_type", "is_active")
    search_fields = ("flag_key",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)


# ----------------------------
# COMPLAINTS MODULE
# ----------------------------

class ComplaintAttachmentInline(admin.TabularInline):
    model = ComplaintAttachment
    extra = 0
    fields = ("file", "note", "uploaded_by", "uploaded_at")
    readonly_fields = ("uploaded_at",)

    def get_readonly_fields(self, request, obj=None):
        # uploaded_by is set in code usually; keep editable only for superusers if you want
        if request.user.is_superuser:
            return ("uploaded_at",)
        return ("uploaded_by", "uploaded_at")


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")
    ordering = ("name",)


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    inlines = [ComplaintAttachmentInline]

    list_display = (
        "id",
        "created_at",
        "store",
        "status",
        "category",
        "title",
        "unit_display",
        "created_by",
    )
    list_filter = ("status", "category", "store")
    search_fields = (
        "title",
        "description",
        "unit__unit_id",
        "unit__order_id",
        "unit_id_text",
        "order_id_text",
        "created_by__username",
        "created_by__email",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    readonly_fields = ("created_at",)

    def unit_display(self, obj: Complaint):
        if obj.unit:
            return obj.unit.unit_id
        return obj.unit_id_text or "-"
    unit_display.short_description = "Unit"

    def save_model(self, request, obj, form, change):
        # If created_by not set, default to current user
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ComplaintAttachment)
class ComplaintAttachmentAdmin(admin.ModelAdmin):
    list_display = ("id", "complaint", "uploaded_by", "uploaded_at", "note")
    list_filter = ("uploaded_at",)
    search_fields = ("complaint__title", "note", "uploaded_by__username", "uploaded_by__email")
    date_hierarchy = "uploaded_at"
    ordering = ("-uploaded_at",)
