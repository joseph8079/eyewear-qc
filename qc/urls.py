from django.urls import path
from . import views

app_name = "qc"

urlpatterns = [
    # -------------------------
    # DASHBOARD
    # -------------------------
    path("", views.home, name="home"),

    # -------------------------
    # FRAMES
    # -------------------------
    path("frames/", views.frames_list, name="frames_list"),
    path(
        "frames/<int:pk>/complaints/new/",
        views.complaint_create_for_frame,
        name="complaint_create_for_frame",
    ),

    # CSV template download
    path(
        "import/frames/template.csv/",
        views.download_frames_template,
        name="download_frames_template",
    ),

    # -------------------------
    # COMPLAINTS
    # -------------------------
    path("complaints/", views.complaints_list, name="complaints_list"),

    # -------------------------
    # CSV IMPORT
    # -------------------------
    path("import/frames/", views.import_frames, name="import_frames"),
]
