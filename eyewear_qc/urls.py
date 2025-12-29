from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from qc import views as qc_views

urlpatterns = [
    path("admin/", admin.site.urls),

    # Django auth (adds /accounts/login/, /accounts/logout/, etc.)
    path("accounts/", include("django.contrib.auth.urls")),

    # Health endpoint (Render uses this)
    path("health/", qc_views.health, name="health"),

    # Root goes to UI
    path("", RedirectView.as_view(url="/ui/", permanent=False), name="root"),

    # QC app
    path("", include("qc.urls")),
]
