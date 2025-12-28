import csv

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ComplaintForm, FrameForm
from .models import Complaint, FrameVariant


@login_required
def home(request):
    return render(request, "qc/home.html")


@login_required
def frames_list(request):
    frames = FrameVariant.objects.select_related("style").order_by("-created_at")
    return render(request, "qc/frames_list.html", {"frames": frames})


@login_required
def frame_detail(request, pk):
    variant = get_object_or_404(FrameVariant.objects.select_related("style"), pk=pk)
    complaints = variant.complaints.select_related("store").order_by("-created_at")
    return render(
        request,
        "qc/frame_detail.html",
        {"variant": variant, "complaints": complaints},
    )


@login_required
def complaints_list(request):
    complaints = Complaint.objects.select_related("variant", "store", "variant__style").order_by("-created_at")
    return render(request, "qc/complaints_list.html", {"complaints": complaints})


# ✅ THIS is the missing view your urls.py is calling
@login_required
def complaint_create_for_frame(request, pk):
    variant = get_object_or_404(FrameVariant.objects.select_related("style"), pk=pk)

    if request.method == "POST":
        form = ComplaintForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.variant = variant
            obj.save()
            return redirect("qc:frame_detail", pk=variant.pk)
    else:
        form = ComplaintForm()

    return render(request, "qc/complaint_form.html", {"form": form, "variant": variant})


@login_required
def download_frames_template(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="frames_template.csv"'
    writer = csv.writer(response)
    writer.writerow(["style_code", "supplier", "sku", "color", "size", "status"])
    writer.writerow(["ST123", "Acme", "ST123-001", "Black", "52-18", "OK"])
    return response


# Keep this if you already have an import page; otherwise it’s a harmless placeholder.
@login_required
def import_frames(request):
    # If you already had import logic, paste it back in here.
    # For now, just render a page with a download link.
    return render(request, "qc/import_frames.html")
