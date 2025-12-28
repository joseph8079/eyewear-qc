import csv
from io import TextIOWrapper
from django.db import transaction

from .models import FrameStyle, FrameVariant

ALLOWED_STATUS = {"APPROVED", "WATCH", "HOLD", "PULLED"}

def import_frames_csv(file_obj):
    """
    CSV required headers:
      style_code,supplier_name,sku,color,size,status
    """
    text_file = TextIOWrapper(file_obj, encoding="utf-8", newline="")
    reader = csv.DictReader(text_file)

    required = {"style_code", "supplier_name", "sku", "color", "size", "status"}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        missing = required - set(reader.fieldnames or [])
        raise ValueError(f"CSV missing required columns: {', '.join(sorted(missing))}")

    created_styles = 0
    created_frames = 0
    updated_frames = 0

    with transaction.atomic():
        for row in reader:
            style_code = row["style_code"].strip()
            supplier_name = row["supplier_name"].strip()
            sku = row["sku"].strip()
            color = row["color"].strip()
            size = row["size"].strip()
            status = row["status"].strip().upper()

            if not sku:
                raise ValueError("SKU cannot be blank.")
            if status not in ALLOWED_STATUS:
                raise ValueError(f"Invalid status '{status}' for SKU '{sku}'.")

            style, style_created = FrameStyle.objects.get_or_create(
                style_code=style_code,
                defaults={"supplier": supplier_name},
            )
            if style_created:
                created_styles += 1
            else:
                # Keep supplier updated if it changes
                if supplier_name and style.supplier != supplier_name:
                    style.supplier = supplier_name
                    style.save(update_fields=["supplier"])

            frame, created = FrameVariant.objects.update_or_create(
                sku=sku,
                defaults={
                    "style": style,
                    "color": color,
                    "size": size,
                    "status": status,
                },
            )
            if created:
                created_frames += 1
            else:
                updated_frames += 1

    return {
        "created_styles": created_styles,
        "created_frames": created_frames,
        "updated_frames": updated_frames,
    }

