from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.shortcuts import render, redirect, get_object_or_404

from .importers import import_frames_csv
from .models import FrameVariant, Complaint, ComplaintAttachment
from .forms import FrameForm, ComplaintForm


@login_required
def dashboard(request):
    total_frames = FrameVariant.objects.count()
    total_complaints = Complaint.objects.count()

    latest_complaints = (
        Complaint.objects.select_related("variant", "variant__style", "store")
        .order_by("-created_at")[:10]
    )

    worst_frames = FrameVariant.objects.select_related("style").order_by("-qc_score_cached")[:10]

    return render(
        request,
        "qc/dashboard.html",
        {
            "total_frames": total_frames,
            "total_complaints": total_complaints,
            "latest_complaints": latest_complaints,
            "worst_frames": worst_frames,
        },
    )


@login_required
def frame_list(request):
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip().upper()

    frames = FrameVariant.objects.select_related("style").all().order_by("style__style_code", "sku")

    if q:
        frames = frames.filter(
            models.Q(sku__icontains=q)
            | models.Q(style__style_code__icontains=q)
            | models.Q(color__icontains=q)
            | models.Q(size__icontains=q)
        )

    if status:
        frames = frames.filter(status=status)

    return render(request, "qc/frame_list.html", {"frames": frames, "q": q, "status": status})


@login_required
def frame_detail(request, pk):
    frame = get_object_or_404(FrameVariant.objects.select_related("style"), pk=pk)
    complaints = (
        Complaint.objects.filter(variant=frame)
        .select_related("store")
        .order_by("-created_at")
    )
    return render(request, "qc/frame_detail.html", {"frame": frame, "complaints": complaints})


@login_required
def frame_create(request):
    if request.method == "POST":
        form = FrameForm(request.POST)
        if form.is_valid():
            frame = form.save()
            messages.success(request, "Frame created.")
            return redirect("frame_detail", pk=frame.pk)
    else:
        form = FrameForm()

    return render(request, "qc/frame_form.html", {"form": form, "mode": "create"})


@login_required
def frame_edit(request, pk):
    frame = get_object_or_404(FrameVariant, pk=pk)

    initial = {
        "style_code": frame.style.style_code,
        "supplier": frame.style.supplier,
    }

    if request.method == "POST":
        form = FrameForm(request.POST, instance=frame)
        if form.is_valid():
            frame = form.save()
            messages.success(request, "Frame updated.")
            return redirect("frame_detail", pk=frame.pk)
    else:
        form = FrameForm(instance=frame, initial=initial)

    return render(
        request,
        "qc/frame_form.html",
        {"form": form, "mode": "edit", "frame": frame},
    )


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import ComplaintForm
from .models import FrameVariant

@login_required
def complaint_create(request, frame_id=None):
    initial = {}
    if frame_id:
        initial["variant"] = get_object_or_404(FrameVariant, pk=frame_id)

    if request.method == "POST":
        form = ComplaintForm(request.POST, request.FILES, initial=initial)
        if form.is_valid():
            form.save()
            return redirect("complaints_list")
    else:
        form = ComplaintForm(initial=initial)

    return render(request, "qc/complaint_create.html", {"form": form})


@login_required
def complaints_list(request):
    complaints = (
        Complaint.objects.select_related("variant", "variant__style", "store")
        .order_by("-created_at")
    )
    return render(request, "qc/complaints_list.html", {"complaints": complaints})


@login_required
def import_frames(request):
    if request.method == "POST":
        f = request.FILES.get("csv_file")
        if not f:
            messages.error(request, "Please choose a CSV file.")
            return redirect("import_frames")

        try:
            result = import_frames_csv(f.file)
            messages.success(
                request,
                f"Import complete. Styles created: {result['created_styles']} | "
                f"Frames created: {result['created_frames']} | "
                f"Frames updated: {result['updated_frames']}"
            )
            return redirect("frame_list")
        except Exception as e:
            messages.error(request, f"Import failed: {e}")
            return redirect("import_frames")

    return render(request, "qc/import_frames.html")

import csv
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

@login_required
def download_frames_csv_template(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="Ctrue_Quality_Tracker_Frames_Template.csv"'

    writer = csv.writer(response)
    writer.writerow(["style_code", "supplier", "sku", "color", "size", "status"])

    # optional example row
    writer.writerow(["STY-1001", "Acme Optical", "STY-1001-BLK-52", "Black", "52-18-140", "OK"])

    return response


