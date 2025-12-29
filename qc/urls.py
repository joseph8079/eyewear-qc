# qc/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("health/", views.health, name="health"),

    # UI shell
    path("", views.home, name="home"),
    path("ui/", views.ui_root, name="ui_root"),
    path("ui/dashboard/", views.ui_dashboard, name="ui_dashboard"),

    # Frames
    path("ui/frames/", views.frames_list, name="frames_list"),
    path("ui/import/", views.import_frames_page, name="import_frames_page"),
    path("ui/import/template.csv", views.download_frames_template, name="download_frames_template"),
    path("ui/import/upload/", views.upload_frames_csv, name="upload_frames_csv"),

    # Inspection flow
    path("ui/inspect/<str:unit_id>/start/", views.start_inspection, name="start_inspection"),
    path("ui/inspect/<int:inspection_id>/", views.inspection_wizard, name="inspection_wizard"),

    # Complaints
    path("ui/complaints/", views.complaints_list, name="complaints_list"),
    path("ui/complaints/new/", views.complaints_new, name="complaints_new"),
    path("ui/complaints/<int:complaint_id>/", views.complaints_detail, name="complaints_detail"),
]
