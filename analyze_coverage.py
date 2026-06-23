"""
Coverage analysis for the recommendation engine.

Run AFTER `python generate_recommendations.py` so it reflects the latest output.

Reports:
  - Variants that generate NO recommendations (empty bathroom AND kitchen, or skipped)
  - Variants that are NEVER recommended to any other tile

Usage:
    python analyze_coverage.py
Optional: write the two handle lists to CSVs for inspection:
    python analyze_coverage.py --dump
"""
import csv, json, sys

VARIANTS_FILE        = "variants.csv"
RECOMMENDATIONS_FILE = "recommendations.csv"

def parse_list(line_field):
    return line_field.replace("\x00", "")

def main():
    dump = "--dump" in sys.argv

    active = set()
    with open(VARIANTS_FILE, encoding="utf-8", errors="replace") as f:
        for row in csv.DictReader(f):
            if row["is_active"].strip().upper() == "TRUE":
                active.add(row["variant_handle"].strip())

    def clean_lines(path):
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                yield line.replace("\x00", "")

    # New grouped columns (flat bathroom_recommendations/kitchen_recommendations are gone).
    REC_COLS = ["bathroom_floor", "bathroom_base", "bathroom_highlighter",
                "kitchen_floor", "kitchen_backsplash"]

    def all_recs(row):
        out = []
        for col in REC_COLS:
            val = row.get(col)
            if val:
                out.extend(json.loads(val))
        return out

    generating = set()
    recommended = set()
    rows = 0
    for row in csv.DictReader(clean_lines(RECOMMENDATIONS_FILE)):
        rows += 1
        h = row["input_variant_handle"].strip()
        recs = all_recs(row)
        if recs:
            generating.add(h)
        for x in recs:
            recommended.add(x)

    not_generating  = active - generating
    not_recommended = active - recommended

    print(f"Active variants ............................ {len(active)}")
    print(f"Rows in recommendations.csv ................ {rows}")
    print(f"Variants that GENERATE recs (>=1) .......... {len(generating)}")
    print(f"Variants NOT generating any recs ........... {len(not_generating)}")
    print(f"Distinct variants USED as a recommendation . {len(recommended)}")
    print(f"Variants NOT part of ANY recommendation .... {len(not_recommended)}")

    if dump:
        with open("variants_not_generating.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["variant_handle"])
            w.writerows([h] for h in sorted(not_generating))
        with open("variants_not_recommended.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["variant_handle"])
            w.writerows([h] for h in sorted(not_recommended))
        print("\nWrote variants_not_generating.csv and variants_not_recommended.csv")

if __name__ == "__main__":
    main()
