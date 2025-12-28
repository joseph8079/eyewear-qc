from django import forms
from .models import Complaint


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class ComplaintForm(forms.ModelForm):
    attachments = forms.FileField(required=False, widget=MultipleFileInput())

    class Meta:
        model = Complaint
        fields = ["store", "variant", "failure_type", "severity", "notes", "attachments"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Bootstrap classes
        self.fields["store"].widget.attrs.update({"class": "form-select"})
        self.fields["variant"].widget.attrs.update({"class": "form-select"})
        self.fields["failure_type"].widget.attrs.update({"class": "form-control", "placeholder": "e.g. hinge crack"})
        self.fields["severity"].widget.attrs.update({"class": "form-control", "placeholder": "Low / Medium / High"})
        self.fields["notes"].widget.attrs.update({"class": "form-control", "rows": 4})
        self.fields["attachments"].widget.attrs.update({"class": "form-control"})
