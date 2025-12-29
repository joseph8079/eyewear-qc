cat > qc/services/process.py <<'PY'
# qc/services/process.py

DEEP_COSMETIC_STEPS = [
    {"key": "bend_check", "label": "Bend Check (temple / bridge flex)"},
    {"key": "torque_check", "label": "Torque / twist check (light torsion)"},
    {"key": "drop_check", "label": "Drop / impact simulation (controlled)"},
    {"key": "final_visual", "label": "Final visual under light + loupe"},
]
PY
