# qc/services/process.py
"""
Process definitions for the inspection flow:
- You asked to replace "cosmetic only" with a 4-step deep inspection:
  1) BENDING
  2) THROW / DROP TEST
  3) HINGE / TEMPLE STRESS
  4) FINAL COSMETIC REVIEW
We implement these inside the COSMETIC stage as required checks.
"""

DEEP_COSMETIC_STEPS = [
    {"key": "BENDING", "label": "Bending stress test", "tip": "Gently flex frame front + temples. Check alignment + no creaks."},
    {"key": "DROP_TEST", "label": "Throw / drop test", "tip": "Drop from short height onto padded surface. Check for looseness."},
    {"key": "HINGE_STRESS", "label": "Hinge & temple stress", "tip": "Open/close hinges repeatedly. Check screws + resistance."},
    {"key": "FINAL_COSMETIC", "label": "Final cosmetic scan", "tip": "Inspect lenses + frame finish. Look for scratches, chips, marks."},
]
