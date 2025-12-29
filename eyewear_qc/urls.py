from django.contrib import admin
from django.urls import path, include
from qc import views as qc_views

urlpatterns = [
    path("admin/", admin.site.urls),

    # Always-safe endpoints (Render + monitoring)
    path("", qc_views.home, name="root"),
    path("health/", qc_views.health, name="health"),

    # Everything else (UI + API)
    path("", include("qc.urls")),
]
