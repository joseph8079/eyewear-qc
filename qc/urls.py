

from django.urls import path
from . import views

urlpatterns = [
    # base
    path("", views.home, name="home"),
    path("health/", views.health, name="health"),

    # UI
    path("ui/", views.ui_home, name="ui_home"),
    path("ui/dashboard/", views.ui_dashboard, name="ui_dashboard"),

    # Frames / Units
    path("frames/", views.frames_list, name="frames_list"),
    path("frames/<int:unit_id>/", views.unit_detail, name="unit_detail"),

    # Imports (frames template upload/download)
    path("import/frames/", views.import_frames, name="import_frames"),

    # Complaints
    path("complaints/", views.complaints_list, name="complaints_list"),
    path("complaints/new/", views.complaints_new, name="complaints_new"),
    path("complaints/<int:complaint_id>/", views.complaints_detail, name="complaints_detail"),
]
