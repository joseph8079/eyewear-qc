from __future__ import annotations

import csv
import io

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import Complaint, FrameStyle, FrameVariant, Store


# -------------------------
# HOME
# -------------------------
@login_required
def home(request):
    stats = {
        "styles": FrameStyle.objects.count(),
        "variants": FrameVariant.objects.count(),
        "complaints": Complaint.objects.count(),
    }
    return render(request, "qc/home.html", {"stats": stats})


# -------------------------
# FRAMES LIST
# -------------------------
@login_required
def frames_list(request):
    frames = (
        FrameVariant.objects
        .select_related("style")
        .order_by("-created_at")
    )
    return render(request, "qc/frames_list.html", {"frames": frames})


# -------------------------
# COMPLAINTS LIST
# -------------------------
@login_required
def complaints_list(request):
    complaints = (
        Complaint.objects
        .select_related("variant", "variant__style", "store")
        .order_by("-created_at")
    )
    return render(request, "qc/complaints_list.html", {"complaints": complaints})


# =========================
# FORMS
# =========================
class FrameCreateForm(forms.Form):
    style_code = forms.CharField(max_length=64)
    supplier = forms.CharField(max_length=255, required=False)
    sku = forms.CharField(max_length=128)
    color = forms.CharField(max_length=64, required=False)
    size = forms.CharField(max_length=64, required=False)
    status = forms.ChoiceField(choices=FrameVariant.STATUS_CHOICES)


class ComplaintCreateForm(forms.Form):
    variant = forms.ModelChoiceField(
        queryset=FrameVariant.objects.select_related("style").order_by("sku")
    )
    store = forms.ModelChoiceField(
        queryset=Store.objects.order_by("name"),
        required=False
    )
    failure_type = forms.ChoiceField(choices=Complaint.FAILURE_CHOICES)
    severity = forms.ChoiceField(choices=Complaint.SEVERITY_CHOICES)
    notes = forms.CharField(widget=forms.Textarea, required=False)


# -------------------------
# ADD FRAME
# -------------------------
@login_required
@require_http_methods(["GET", "POST"])
def frame_create(request):
    if request.method == "POST":
        form = FrameCreateForm(request.POST)
        if form.is_valid():
            style, _ = FrameStyle.objects.get_or_create(
                style_code=form.cleaned_data["style_code"],
                defaults={"supplier": form.cleaned_data.get("supplier", "")},
            )

            FrameVariant.objects.update_or_create(
                sku=form.cleaned_data["sku"],
                defaults={
                    "style": style,
                    "color": form.cleaned_data.get("color", ""),
                    "size": form.cleaned_data.get("size", ""),
                    "status": form.cleaned_data["status"],
                    "created_at": timezone.now(),
                },
            )

            messages.success(request, "Frame saved.")
            return redirect("frames_list")
    else:
        form = FrameCreateForm(initial={"status": "OK"})

    return render(request, "qc/frame_form.html", {"form": form})


# -------------------------
# ADD COMPLAINT (STANDALONE)
# -------------------------
@login_required
@require_http_methods(["GET", "POST"])
def complaint_create(request):
    if request.method == "POST":
        form = ComplaintCreateForm(request.POST)
        if form.is_valid():
            Complaint.objects.create(
                variant=form.cleaned_data["variant"],
                store=form.cleaned_data.get("store"),
                failure_type=form.cleaned_data["failure_type"],
                severity=form.cleaned_data["severity"],
                notes=form.cleaned_data.get("notes", ""),
                created_at=timezone.now(),
            )
            messages.success(request, "Complaint created.")
            return redirect("complaints_list")
    else:
        form = ComplaintCreateForm()

    return render(request, "qc/complaint_form.html", {"form": form})


# -------------------------
# ADD COMPLAINT FOR FRAME
# -------------------------
@login_required
@require_http_methods(["GET", "POST"])
def complaint_create_for_frame(request, pk: int):
    variant = get_object_or_404(FrameVariant, pk=pk)

    if request.method == "POST":
        Complaint.objects.create(
            variant=variant,
            store_id=request.POST.get("store") or None,
            failure_type=request.POST.get("failure_type"),
            severity=request.POST.get("severity"),
            notes=request.POST.get("notes", ""),
            created_at=timezone.now(),
        )
        messages.success(request, f"Complaint added for {variant.sku}")
        return redirect("complaints_list")

    return render(
        request,
        "qc/complaint_form.html",
        {
            "variant": variant,
            "stores": Store.objects.all(),
            "failure_choices": Complaint.FAILURE_CHOICES,
            "severity_choices": Complaint.SEVERITY_CHOICES,
        },
    )


# -------------------------
# CSV TEMPLATE
# -------------------------
@login_required
def download_frames_template(request):
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["style_code", "supplier", "sku", "color", "size", "status"])
    writer.writerow(["RB1234", "Luxottica", "RB1234-001-52", "Black", "52-18-140", "OK"])

    response = HttpResponse(output.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="frames_template.csv"'
    return response


# -------------------------
# IMPORT FRAMES
# -------------------------
@login_required
@require_http_methods(["GET", "POST"])
def import_frames(request):
    if request.method == "POST":
        f = request.FILES.get("file")
        if not f:
            messages.error(request, "Upload a CSV file.")
            return redirect("import_frames")

        raw = f.read().decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(io.StringIO(raw))

        with transaction.atomic():
            for row in reader:
                style, _ = FrameStyle.objects.get_or_create(
                    style_code=row["style_code"],
                    defaults={"supplier": row.get("supplier", "")},
                )

                FrameVariant.objects.update_or_create(
                    sku=row["sku"],
                    defaults={
                        "style": style,
                        "color": row.get("color", ""),
                        "size": row.get("size", ""),
                        "status": row.get("status", "OK"),
                        "created_at": timezone.now(),
                    },
                )

        messages.success(request, "Frames imported.")
        return redirect("frames_list")

    return render(request, "qc/import_frames.html")

