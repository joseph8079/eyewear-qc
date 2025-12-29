from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),

    # Frames
    path("frames/", views.frames_list, name="frames_list"),
    path("frames/new/", views.frame_create, name="frame_create"),
    path("frames/template.csv", views.download_frames_template, name="download_frames_template"),
    path("import/frames/", views.import_frames, name="import_frames"),

    # Complaints
    path("complaints/", views.complaints_list, name="complaints_list"),
    path("complaints/new/", views.complaint_create, name="complaint_create"),
    path("frames/<int:pk>/complaints/new/", views.complaint_create_for_frame, name="complaint_create_for_frame"),

    # QC Wizard
    path("api/qc/start-inspection/", views.start_inspection, name="qc-start-inspection"),
    path("api/qc/complete-stage/", views.complete_stage, name="qc-complete-stage"),
    path("api/qc/finalize/", views.finalize_inspection, name="qc-finalize"),

    # Dashboards
    path("api/qc/dashboard/", views.dashboard, name="qc-dashboard"),
]
