from django.urls import path
from . import views

app_name = "qc"

urlpatterns = [
    path("", views.home, name="home"),
    path("frames/", views.frames_list, name="frames_list"),
    path("frames/<int:pk>/", views.frame_detail, name="frame_detail"),
    path("frames/<int:pk>/complaints/new/", views.complaint_create_for_frame, name="complaint_create_for_frame"),
    path("complaints/", views.complaints_list, name="complaints_list"),
    path("import/frames/", views.import_frames, name="import_frames"),
    path("download/frames-template.csv", views.download_frames_template, name="download_frames_template"),
]
