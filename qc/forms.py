from django import forms
from .models import Complaint

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class ComplaintForm(forms.ModelForm):
    attachments = forms.FileField(required=False, widget=MultipleFileInput())

    class Meta:
        model = Complaint
        fields = ["variant", "failure_type", "severity", "notes", "attachments"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add Bootstrap classes
        for name, field in self.fields.items():
            if name == "attachments":
                field.widget.attrs.update({"class": "form-control"})
            elif name == "notes":
                field.widget.attrs.update({"class": "form-control", "rows": 4})
            else:
                field.widget.attrs.update({"class": "form-select" if name == "variant" else "form-control"})
