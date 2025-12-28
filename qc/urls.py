from django.urls import path
from . import views

urlpatterns = [
    path("", views.variant_list, name="variant_list"),
    path("complaints/new/", views.complaint_create, name="complaint_create"),
]
