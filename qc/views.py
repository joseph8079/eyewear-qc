from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponse
from django.utils import timezone

from .models import FrameVariant, Complaint, Attachment, Store
from .forms import ComplaintForm


def dashboard(request):
    # last 30 days complaints
    since = timezone.now() - timezone.timedelta(days=30)

    total_variants = FrameVariant.objects.count()
    total_complaints_30 = Complaint.objects.filter(created_at__gte=since).count()

    top_variants = (
        Complaint.objects.filter(created_at__gte=since)
        .values("variant__sku", "variant__style__style_code")
        .annotate(c=Count("id"))
        .order_by("-c")[:10]
    )

    by_failure = (
        Complaint.objects.filter(created_at__gte=since)
        .values("failure_type")
        .annotate(c=Count("id"))
        .order_by("-c")[:10]
    )

    by_store = (
        Complaint.objects.filter(created_at__gte=since)
        .values("store__name")
        .annotate(c=Count("id"))
        .order_by("-c")
    )

    context = {
        "since": since,
        "total_variants": total_variants,
        "total_complaints_30": total_complaints_30,
        "top_variants": top_variants,
        "by_failure": by_failure,
        "by_store": by_store,
    }
    return render(request, "qc/dashboard.html", context)


def variant_list(request):
    qs = FrameVariant.objects.select_related("style").all()

    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    supplier = request.GET.get("supplier", "").strip()

    if q:
        qs = qs.filter(sku__icontains=q) | qs.filter(style__style_code__icontains=q)
    if status:
        qs = qs.filter(status=status)
    if supplier:
        qs = qs.filter(style__supplier_name__icontains=supplier)

    # annotate complaint counts (last 90 days)
    since = timezone.now() - timezone.timedelta(days=90)
    complaint_counts = (
        Complaint.objects.filter(created_at__gte=since)
        .values("variant_id")
        .annotate(c=Count("id"))
    )
    counts_map = {row["variant_id"]: row["c"] for row in complaint_counts}

    variants = list(qs.order_by("style__style_code", "sku")[:2000])  # safe cap for now
    for v in variants:
        v.complaints_90 = counts_map.get(v.id, 0)

    context = {
        "variants": variants,
        "q": q,
        "status": status,
        "supplier": supplier,
        "status_choices": FrameVariant.STATUS_CHOICES,
    }
    return render(request, "qc/variant_list.html", context)


def variant_detail(request, variant_id: int):
    variant = get_object_or_404(FrameVariant.objects.select_related("style"), id=variant_id)
    complaints = (
        Complaint.objects.filter(variant=variant)
        .select_related("store")
        .order_by("-created_at")[:100]
    )
    context = {"variant": variant, "complaints": complaints}
    return render(request, "qc/variant_detail.html", context)


def complaints_list(request):
    qs = Complaint.objects.select_related("variant", "variant__style", "store").order_by("-created_at")

    store_id = request.GET.get("store", "").strip()
    failure_type = request.GET.get("failure", "").strip()
    q = request.GET.get("q", "").strip()

    if store_id:
        qs = qs.filter(store_id=store_id)
    if failure_type:
        qs = qs.filter(failure_type__icontains=failure_type)
    if q:
        qs = qs.filter(variant__sku__icontains=q) | qs.filter(variant__style__style_code__icontains=q)

    stores = Store.objects.all().order_by("name")

    context = {
        "complaints": qs[:500],
        "stores": stores,
        "store_id": store_id,
        "failure_type": failure_type,
        "q": q,
    }
    return render(request, "qc/complaints_list.html", context)


def complaint_create(request, variant_id=None):
    initial = {}
    if variant_id:
        initial["variant"] = get_object_or_404(FrameVariant, id=variant_id)

    if request.method == "POST":
        form = ComplaintForm(request.POST, request.FILES, initial=initial)
        if form.is_valid():
            complaint = form.save()

            for f in request.FILES.getlist("attachments"):
                Attachment.objects.create(complaint=complaint, file=f)

            return redirect("variant_detail", variant_id=complaint.variant_id)
    else:
        form = ComplaintForm(initial=initial)

    return render(request, "qc/complaint_create.html", {"form": form, "variant_id": variant_id})


def variant_set_status(request, variant_id: int, status: str):
    variant = get_object_or_404(FrameVariant, id=variant_id)
    allowed = {s for s, _ in FrameVariant.STATUS_CHOICES}
    if status in allowed:
        variant.status = status
        variant.save(update_fields=["status"])
    return redirect("variant_detail", variant_id=variant_id)


def supplier_export_csv(request):
    """
    Simple export you can hand to supplier:
    SKU, Style, Supplier, Color, Size, Status, Complaints90
    """
    since = timezone.now() - timezone.timedelta(days=90)
    complaint_counts = (
        Complaint.objects.filter(created_at__gte=since)
        .values("variant_id")
        .annotate(c=Count("id"))
    )
    counts_map = {row["variant_id"]: row["c"] for row in complaint_counts}

    supplier = request.GET.get("supplier", "").strip()
    qs = FrameVariant.objects.select_related("style").all()
    if supplier:
        qs = qs.filter(style__supplier_name__icontains=supplier)

    import csv
    from io import StringIO

    out = StringIO()
    w = csv.writer(out)
    w.writerow(["SKU", "Style", "Supplier", "Color", "Size", "Status", "Complaints90"])

    for v in qs.order_by("style__style_code", "sku")[:5000]:
        w.writerow([
            v.sku,
            v.style.style_code,
            v.style.supplier_name,
            v.color,
            v.size,
            v.status,
            counts_map.get(v.id, 0),
        ])

    resp = HttpResponse(out.getvalue(), content_type="text/csv")
    resp["Content-Disposition"] = 'attachment; filename="supplier_export.csv"'
    return resp
