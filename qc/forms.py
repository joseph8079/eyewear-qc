from django import forms
from .models import Complaint


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class ComplaintForm(forms.ModelForm):
    attachments = forms.FileField(
        required=False,
        widget=MultipleFileInput(),
    )

    class Meta:
        model = Complaint
        fields = ["variant", "failure_type", "severity", "notes", "attachments"]
