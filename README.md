# IO Signal Sudoku — Beginner Prototype

This is a hackathon prototype based on the supplied problem statement.

## What it demonstrates
1. Upload an Excel/CSV IO MDB.
2. Configure a few rules.
3. Allocate signals to Cabinet → CIOC → Baseplate → CHARM slot.
4. Run basic rule/capacity checks.
5. Show a TQ/issue report.
6. Download an Excel report.

## Run locally

Install Python 3.10+.

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the local URL shown by Streamlit.

## Important
This is a **prototype**, not a production DCS engineering allocator. It intentionally implements a manageable subset of the problem so a beginner team can understand and demo it.

For the final hackathon version, extend:
- exact cable-pair packing
- full user-defined rule engine
- correct hardware/terminal mapping
- robust A/B separation
- spare-room optimization
- revision A vs B comparison
- TQ generation for unresolved conflicts
- validation against the organizer's sample/hidden data
