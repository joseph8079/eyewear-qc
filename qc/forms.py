from django import forms
from .models import FrameStyle, FrameVariant, Complaint

class FrameForm(forms.ModelForm):
    style_code = forms.CharField(max_length=50, label="Style Code")
    supplier = forms.CharField(max_length=100, required=False, label="Supplier")

    class Meta:
        model = FrameVariant
        fields = ["style_code", "supplier", "sku", "color", "size", "status"]

    def save(self, commit=True):
        style_code = self.cleaned_data["style_code"].strip()
        supplier = (self.cleaned_data.get("supplier") or "").strip()

        style, _ = FrameStyle.objects.get_or_create(
            style_code=style_code,
            defaults={"supplier": supplier},
        )
        if supplier and style.supplier != supplier:
            style.supplier = supplier
            style.save(update_fields=["supplier"])

        frame = super().save(commit=False)
        frame.style = style
        if commit:
            frame.save()
        return frame
class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ["store", "failure_type", "severity", "notes"]

