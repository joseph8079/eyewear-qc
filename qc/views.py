from django.shortcuts import render, redirect
from .models import FrameVariant, Complaint, Attachment
from .forms import ComplaintForm

def variant_list(request):
    variants = FrameVariant.objects.all()
    return render(request, "qc/variant_list.html", {"variants": variants})

def complaint_create(request):
    if request.method == "POST":
        form = ComplaintForm(request.POST, request.FILES)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.store_id = 1  # TEMP store
            complaint.save()
            for f in request.FILES.getlist("attachments"):
                Attachment.objects.create(complaint=complaint, file=f)
            return redirect("/")
    else:
        form = ComplaintForm()
    return render(request, "qc/complaint_create.html", {"form": form})
