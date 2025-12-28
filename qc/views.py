from __future__ import annotations

import csv
import io

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
    """
    Simple dashboard / landing page.
    """
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
    q = (request.GET.get("q") or "").strip()
    qs = FrameVariant.objects.select_related("style").order_by("-created_at")

    if q:
        qs = qs.filter(sku__icontains=q) | qs.filter(style__style_code__icontains=q)

    return render(request, "qc/frames_list.html", {"frames": qs, "q": q})


# -------------------------
# COMPLAINTS LIST
# -------------------------
@login_required
def complaints_list(request):
    qs = (
        Complaint.objects.select_related("variant", "variant__style", "store")
        .order_by("-created_at")
    )
    return render(request, "qc/complaints_list.html", {"complaints": qs})


# -------------------------
# CREATE COMPLAINT FOR FRAME
# -------------------------
@login_required
@require_http_methods(["GET", "POST"])
def complaint_create_for_frame(request, pk: int):
    variant = get_object_or_404(FrameVariant.objects.select_related("style"), pk=pk)

    if request.method == "POST":
        store_id = request.POST.get("store") or None
        failure_type = request.POST.get("failure_type") or "OTHER"
        severity = request.POST.get("severity") or "LOW"
        notes = request.POST.get("notes") or ""

        store = None
        if store_id:
            store = Store.objects.filter(id=store_id).first()

        Complaint.objects.create(
            variant=variant,
            store=store,
            failure_type=failure_type,
            severity=severity,
            notes=notes,
            created_at=timezone.now(),
        )
        messages.success(request, f"Complaint created for {variant.sku}")
        return redirect("complaints_list")

    stores = Store.objects.order_by("name")
    return render(
        request,
        "qc/complaint_form.html",
        {
            "variant": variant,
            "stores": stores,
            "failure_choices": Complaint.FAILURE_CHOICES,
            "severity_choices": Complaint.SEVERITY_CHOICES,
        },
    )


# -------------------------
# CSV TEMPLATE DOWNLOAD
# -------------------------
@login_required
def download_frames_template(request):
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["style_code", "supplier", "sku", "color", "size", "status"])
    writer.writerow(["RB1234", "Luxottica", "RB1234-001-52", "Black", "52-18-140", "OK"])

    resp = HttpResponse(output.getvalue(), content_type="text/csv")
    resp["Content-Disposition"] = 'attachment; filename="frames_import_template.csv"'
    return resp


# -------------------------
# IMPORT FRAMES (CSV UPLOAD)
# -------------------------
@login_required
@require_http_methods(["GET", "POST"])
def import_frames(request):
    """
    Upload a CSV to create/update FrameStyle + FrameVariant.
    """
    if request.method == "POST":
        f = request.FILES.get("file")
        if not f:
            messages.error(request, "Please choose a CSV file.")
            return redirect("import_frames")

        # Read CSV
        raw = f.read().decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(io.StringIO(raw))

        required = {"style_code", "sku"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            messages.error(
                request,
                f"CSV must include at least these columns: {', '.join(sorted(required))}",
            )
            return redirect("import_frames")

        created_variants = 0
        updated_variants = 0
        created_styles = 0
        updated_styles = 0

        with transaction.atomic():
            for row in reader:
                style_code = (row.get("style_code") or "").strip()
                supplier = (row.get("supplier") or "").strip()
                sku = (row.get("sku") or "").strip()
                color = (row.get("color") or "").strip()
                size = (row.get("size") or "").strip()
                status = (row.get("status") or "OK").strip().upper()

                if not style_code or not sku:
                    continue

                if status not in {"OK", "HOLD", "OFF"}:
                    status = "OK"

                style, style_created = FrameStyle.objects.get_or_create(
                    style_code=style_code,
                    defaults={"supplier": supplier},
                )
                if style_created:
                    created_styles += 1
                else:
                    # keep supplier updated if provided
                    if supplier and style.supplier != supplier:
                        style.supplier = supplier
                        style.save(update_fields=["supplier"])
                        updated_styles += 1

                variant, v_created = FrameVariant.objects.get_or_create(
                    sku=sku,
                    defaults={
                        "style": style,
                        "color": color,
                        "size": size,
                        "status": status,
                        "created_at": timezone.now(),
                    },
                )
                if v_created:
                    created_variants += 1
                else:
                    changed = False
                    if variant.style_id != style.id:
                        variant.style = style
                        changed = True
                    if color and variant.color != color:
                        variant.color = color
                        changed = True
                    if size and variant.size != size:
                        variant.size = size
                        changed = True
                    if status and variant.status != status:
                        variant.status = status
                        changed = True

                    if changed:
                        variant.save()
                        updated_variants += 1

        messages.success(
            request,
            f"Import done. Styles: +{created_styles} new, {updated_styles} updated. "
            f"Variants: +{created_variants} new, {updated_variants} updated."
        )
        return redirect("frames_list")

    return render(request, "qc/import_frames.html")
