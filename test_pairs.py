from agents import pipeline

pairs = [
    ("E11.9", "83036"),   # Type 2 diabetes / HbA1c
    ("J18.9", "71046"),   # Pneumonia / Chest X-ray
    ("M54.5", "99213"),   # Low back pain / Office visit
    ("I10",   "93000"),   # Hypertension / ECG
]

for dx, cpt in pairs:
    print()
    print("=" * 60)
    print(f"dx={dx}  cpt={cpt}")
    print("=" * 60)
    result = pipeline.invoke({"dx_code": dx, "cpt_code": cpt, "code_resolution": ""})
    print(result["code_resolution"])
