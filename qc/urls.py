from django.urls import path
from . import views

urlpatterns = [
    # UI
    path("ui/", views.ui_home, name="ui-home"),
    path("ui/dashboard/", views.ui_dashboard, name="ui-dashboard"),
    path("frames/", views.ui_frames, name="ui-frames"),
    path("import/frames/", views.ui_import_frames, name="ui-import-frames"),
    path("ui/qc/", views.ui_qc_wizard, name="ui-qc-wizard"),

    # API (QC v2.1)
    path("api/qc/start-inspection/", views.start_inspection, name="qc-start-inspection"),
    path("api/qc/complete-stage/", views.complete_stage, name="qc-complete-stage"),
    path("api/qc/finalize/", views.finalize_inspection, name="qc-finalize"),
    path("api/qc/dashboard/", views.dashboard, name="qc-dashboard"),
]
