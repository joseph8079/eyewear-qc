from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),

    path("frames/", views.frames_list, name="frames_list"),
    path("frames/template.csv", views.download_frames_template, name="download_frames_template"),

    path("complaints/", views.complaints_list, name="complaints_list"),
    path("frames/<int:pk>/complaints/new/", views.complaint_create_for_frame, name="complaint_create_for_frame"),

    path("import/frames/", views.import_frames, name="import_frames"),
]
