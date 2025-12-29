from django.urls import path
from . import views

urlpatterns = [
    # Home / health
    path("", views.home, name="home"),
    path("health/", views.health, name="qc-health"),

    # ----------------------------
    # LEGACY PAGES (so old UI links don't 404)
    # ----------------------------
    path("frames/", views.legacy_frames_page, name="legacy-frames-page"),
    path("complaints/", views.legacy_complaints_page, name="legacy-complaints-page"),
    path("import/frames/", views.legacy_import_frames_page, name="legacy-import-frames-page"),

    # ----------------------------
    # Legacy API endpoints (stubs)
    # ----------------------------
    path("api/stores/", views.legacy_stores, name="legacy-stores"),
    path("api/frame-styles/", views.legacy_frame_styles, name="legacy-frame-styles"),
    path("api/frame-variants/", views.legacy_frame_variants, name="legacy-frame-variants"),
    path("api/complaints/", views.legacy_complaints, name="legacy-complaints"),
    path("api/complaints/<int:complaint_id>/", views.legacy_complaint_detail, name="legacy-complaint-detail"),
    path("api/complaints/<int:complaint_id>/attachments/", views.legacy_complaint_attachments, name="legacy-complaint-attachments"),

    # ----------------------------
    # QC v2.1 API
    # ----------------------------
    path("api/qc/start-inspection/", views.start_inspection, name="qc-start-inspection"),
    path("api/qc/complete-stage/", views.complete_stage, name="qc-complete-stage"),
    path("api/qc/finalize/", views.finalize_inspection, name="qc-finalize"),
    path("api/qc/dashboard/", views.dashboard, name="qc-dashboard"),
]
