from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("variants/", views.variant_list, name="variant_list"),
    path("variants/<int:variant_id>/", views.variant_detail, name="variant_detail"),
    path("variants/<int:variant_id>/status/<str:status>/", views.variant_set_status, name="variant_set_status"),

    path("complaints/", views.complaints_list, name="complaints_list"),
    path("complaints/new/", views.complaint_create, name="complaint_create"),
    path("complaints/new/<int:variant_id>/", views.complaint_create, name="complaint_create_for_variant"),

    path("export/supplier.csv", views.supplier_export_csv, name="supplier_export_csv"),
    path("import/frames/", views.import_frames, name="import_frames"),

]

