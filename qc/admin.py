from django.contrib import admin
from .models import (
    Unit,
    Inspection,
    InspectionStageResult,
    Defect,
    DefectPhoto,
    ReworkTicket,
    QualityFlag,
)


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("unit_id", "order_id", "frame_model", "lab", "priority", "status", "received_at")
    search_fields = ("unit_id", "order_id", "frame_model", "lab")
    list_filter = ("priority", "status", "lab", "frame_model")


@admin.register(Inspection)
class InspectionAdmin(admin.ModelAdmin):
    list_display = ("unit", "attempt_number", "final_result", "tech_user", "started_at", "completed_at", "training_mode_used")
    search_fields = ("unit__unit_id", "unit__order_id", "tech_user__username")
    list_filter = ("final_result", "training_mode_used", "tech_user")


@admin.register(InspectionStageResult)
class InspectionStageResultAdmin(admin.ModelAdmin):
    list_display = ("inspection", "stage", "status", "started_at", "completed_at")
    list_filter = ("stage", "status")
    search_fields = ("inspection__unit__unit_id",)


@admin.register(Defect)
class DefectAdmin(admin.ModelAdmin):
    list_display = ("stage_result", "category", "reason_code", "severity")
    list_filter = ("category", "severity", "reason_code")
    search_fields = ("stage_result__inspection__unit__unit_id", "reason_code")


@admin.register(DefectPhoto)
class DefectPhotoAdmin(admin.ModelAdmin):
    list_display = ("defect", "image")
    search_fields = ("defect__stage_result__inspection__unit__unit_id",)


@admin.register(ReworkTicket)
class ReworkTicketAdmin(admin.ModelAdmin):
    list_display = ("unit", "failed_stage", "status", "assigned_to", "created_at", "closed_at")
    list_filter = ("status", "failed_stage")
    search_fields = ("unit__unit_id", "reason_summary")


@admin.register(QualityFlag)
class QualityFlagAdmin(admin.ModelAdmin):
    list_display = ("flag_type", "flag_key", "defect_rate", "threshold", "sample_size", "is_active", "created_at", "resolved_at")
    list_filter = ("flag_type", "is_active")
    search_fields = ("flag_key",)

