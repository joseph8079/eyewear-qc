from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),

    path("frames/", views.frame_list, name="frame_list"),
    path("frames/new/", views.frame_create, name="frame_create"),
    path("frames/<int:pk>/", views.frame_detail, name="frame_detail"),
    path("frames/<int:pk>/edit/", views.frame_edit, name="frame_edit"),

    path("frames/<int:pk>/complaints/new/", views.complaint_create_for_frame, name="complaint_create_for_frame"),
    path("complaints/", views.complaints_list, name="complaints_list"),

    path("import/frames/", views.import_frames, name="import_frames"),
    path("complaints/new/", views.complaint_create, name="complaint_create"),
    path("frames/<int:frame_id>/complaints/new/", views.complaint_create, name="complaint_create_for_frame"),
    path("download/frames-template/", views.download_frames_csv_template, name="download_frames_template"),

]
