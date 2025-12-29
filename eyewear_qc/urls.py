# eyewear_qc/urls.py

from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # Django auth (provides /accounts/login/ and /accounts/logout/)
    path("accounts/", include("django.contrib.auth.urls")),

    # Your app
    path("", include("qc.urls")),
]

# Serve uploaded media in DEBUG only (local/dev).
# On Render prod, use a persistent disk or object storage for MEDIA.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
