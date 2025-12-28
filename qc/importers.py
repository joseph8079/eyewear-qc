import csv
from io import TextIOWrapper
from dataclasses import dataclass
from typing import Dict, List, Tuple

from django.db import transaction

from .models import FrameStyle, FrameVariant


ALLOWED_STATUS = {c for c, _ in FrameVariant.STATUS_CHOICES}


@dataclass
class ImportResult:
    created_styles: int = 0
    created_variants: int = 0
    updated_variants: int = 0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


def import_frames_csv(file_obj) -> ImportResult:
    """
    CSV columns:
    style_code,supplier_name,sku,color,size,status
    """
    result = ImportResult()
    text_file = TextIOWrapper(file_obj, encoding="utf-8", newline="")
    reader = csv.DictReader(text_file)

    required_cols = {"style_code", "supplier_name", "sku", "color", "size", "status"}
    missing = required_cols - set(reader.fieldnames or [])
    if missing:
        result.errors.append(f"Missing CSV columns: {', '.join(sorted(missing))}")
        return result

    rows = list(reader)
    if not rows:
        result.errors.append("CSV is empty.")
        return result

    # Basic validation first (collect all errors)
    cleaned = []
    for i, r in enumerate(rows, start=2):  # header is line 1
        style_code = (r.get("style_code") or "").strip()
        supplier_name = (r.get("supplier_name") or "").strip()
        sku = (r.get("sku") or "").strip()
        color = (r.get("color") or "").strip()
        size = (r.get("size") or "").strip()
        status = (r.get("status") or "").strip().upper()

        if not style_code:
            result.errors.append(f"Line {i}: style_code is required")
        if not supplier_name:
            result.errors.append(f"Line {i}: supplier_name is required")
        if not sku:
            result.errors.append(f"Line {i}: sku is required")
        if not color:
            result.errors.append(f"Line {i}: color is required")
        if not size:
            result.errors.append(f"Line {i}: size is required")
        if status not in ALLOWED_STATUS:
            result.errors.append(f"Line {i}: status must be one of {sorted(ALLOWED_STATUS)} (got '{status}')")

        cleaned.append((style_code, supplier_name, sku, color, size, status))

    # stop if errors
    if result.errors:
        return result

    # Import atomically
    with transaction.atomic():
        # cache styles by style_code
        style_map: Dict[str, FrameStyle] = {
            s.style_code: s for s in FrameStyle.objects.filter(style_code__in={c[0] for c in cleaned})
        }

        # create missing styles
        for style_code, supplier_name, *_rest in cleaned:
            if style_code not in style_map:
                style = FrameStyle.objects.create(style_code=style_code, supplier_name=supplier_name)
                style_map[style_code] = style
                result.created_styles += 1
            else:
                # keep supplier_name updated if changed
                style = style_map[style_code]
                if supplier_name and style.supplier_name != supplier_name:
                    style.supplier_name = supplier_name
                    style.save(update_fields=["supplier_name"])

        # cache existing variants by sku
        existing = {v.sku: v for v in FrameVariant.objects.filter(sku__in={c[2] for c in cleaned}).select_related("style")}

        # upsert variants
        for style_code, _supplier_name, sku, color, size, status in cleaned:
            style = style_map[style_code]
            if sku in existing:
                v = existing[sku]
                changed = False

                if v.style_id != style.id:
                    v.style = style
                    changed = True
                if v.color != color:
                    v.color = color
                    changed = True
                if v.size != size:
                    v.size = size
                    changed = True
                if v.status != status:
                    v.status = status
                    changed = True

                if changed:
                    v.save()
                    result.updated_variants += 1
            else:
                FrameVariant.objects.create(
                    style=style,
                    sku=sku,
                    color=color,
                    size=size,
                    status=status,
                )
                result.created_variants += 1

    return result
