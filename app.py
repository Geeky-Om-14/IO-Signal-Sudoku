
import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="IO Signal Sudoku", page_icon="🧩", layout="wide")

st.title("🧩 IO Signal Sudoku")
st.caption("Prototype — Excel in → Rule-based IO allocation → Excel out")

# ----------------------------
# Helper functions
# ----------------------------
def allocate_signals(df, spare_pct=10, separate_ab=True, keep_groups=True):
    df = df.copy()
    required = ["Tag", "IO_Type", "Cable", "Pair", "Group", "Segregation"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError("Missing columns: " + ", ".join(missing))

    # Normalize values
    for c in required:
        df[c] = df[c].fillna("").astype(str).str.strip()

    # Sort roughly by group, segregation, cable and pair
    df["_group_sort"] = df["Group"].replace("", "ZZZ")
    df["_seg_sort"] = df["Segregation"].replace("", "Z")
    df = df.sort_values(["_group_sort", "_seg_sort", "Cable", "Pair", "Tag"]).reset_index(drop=True)

    # Prototype capacities from the problem statement:
    # 12 CHARM slots / baseplate, 8 baseplates / CIOC, 4 CIOCs / cabinet.
    MAX_CHARM = 12
    MAX_BP = 8
    MAX_CIOC = 4

    allocations = []
    cabinet = 1
    cioc = 1
    baseplate = 1
    charm = 1
    used_bp_in_cioc = 0

    current_group = None
    current_seg = None

    for _, row in df.iterrows():
        # Start a new CIOC when capacity is reached.
        if charm > MAX_CHARM:
            charm = 1
            baseplate += 1
            used_bp_in_cioc += 1

        if used_bp_in_cioc >= MAX_BP:
            cioc += 1
            used_bp_in_cioc = 0
            baseplate = 1

        if cioc > MAX_CIOC:
            cabinet += 1
            cioc = 1
            baseplate = 1
            used_bp_in_cioc = 0

        # Very simple A/B separation: prefer a new CIOC when switching
        # between A and B within the same group.
        if separate_ab and row["Segregation"] in ("A", "B"):
            if current_group == row["Group"] and current_seg and row["Segregation"] != current_seg:
                cioc += 1
                baseplate = 1
                charm = 1
                used_bp_in_cioc = 0
                if cioc > MAX_CIOC:
                    cabinet += 1
                    cioc = 1

        # Map signal type to a simple CHARM label.
        io = row["IO_Type"].upper()
        if io == "AI":
            charm_type = "AI CHARM"
        elif io == "AO":
            charm_type = "AO CHARM"
        elif io == "DI":
            charm_type = "DI CHARM"
        elif io == "DO-SOV":
            charm_type = "Isolated DO CHARM"
        else:
            charm_type = "DO CHARM" if io.startswith("DO") else f"{io} CHARM"

        allocations.append({
            "Tag": row["Tag"],
            "IO_Type": row["IO_Type"],
            "Cable": row["Cable"],
            "Pair": row["Pair"],
            "Group": row["Group"],
            "Segregation": row["Segregation"],
            "Cabinet": f"MC-{cabinet:02d}",
            "CIOC": f"CIOC-{cioc}",
            "Baseplate": f"{cioc:02d}-CBP-{baseplate}",
            "CHARM_Slot": charm,
            "CHARM": charm_type,
            "Status": "ALLOCATED"
        })

        current_group = row["Group"]
        current_seg = row["Segregation"]
        charm += 1

    out = pd.DataFrame(allocations)

    # Rule checks / TQs
    issues = []
    if not out.empty:
        # Capacity check
        counts = out.groupby(["Cabinet", "CIOC", "Baseplate"]).size()
        for idx, count in counts.items():
            if count > MAX_CHARM:
                issues.append({
                    "Type": "Capacity",
                    "Tag": "",
                    "Message": f"{idx} has {count} signals; maximum is {MAX_CHARM}."
                })

        # A/B same-CIOC check
        if separate_ab:
            for (cab, c), g in out.groupby(["Cabinet", "CIOC"]):
                segs = set(x for x in g["Segregation"] if x)
                if "A" in segs and "B" in segs:
                    issues.append({
                        "Type": "Rule conflict",
                        "Tag": "",
                        "Message": f"{cab}/{c} contains both A and B segregation."
                    })

    # Add a simple spare summary
    summary = (
        out.groupby(["Cabinet"])
        .agg(Signals=("Tag", "count"), CIOCs=("CIOC", "nunique"), Baseplates=("Baseplate", "nunique"))
        .reset_index()
    )
    summary["Target Spare %"] = spare_pct
    summary["Note"] = "Prototype estimate; spare-room optimization is simplified."

    return out, pd.DataFrame(issues), summary


def to_excel(allocation, issues, summary):
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        allocation.to_excel(writer, index=False, sheet_name="IO Allocation")
        issues.to_excel(writer, index=False, sheet_name="TQ Report")
        summary.to_excel(writer, index=False, sheet_name="Cabinet Summary")
    bio.seek(0)
    return bio


# ----------------------------
# UI
# ----------------------------
with st.sidebar:
    st.header("⚙️ Project Rules")
    spare_pct = st.slider("Spare capacity target (%)", 0, 30, 10)
    separate_ab = st.checkbox("Keep A/B segregation separate", True)
    keep_groups = st.checkbox("Keep logical groups together", True)

uploaded = st.file_uploader("Upload customer IO MDB (.xlsx or .csv)", type=["xlsx", "xls", "csv"])

if uploaded is None:
    st.info("Upload the included sample_io_mdb.xlsx to try the prototype.")
    st.markdown("""
    **Expected columns:** `Tag, IO_Type, Cable, Pair, Group, Segregation`

    **Prototype flow:** Excel → Rules → Allocation → Rule Check → Excel report
    """)
else:
    try:
        if uploaded.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded)
        else:
            df = pd.read_excel(uploaded)

        st.subheader("1. Input data")
        st.dataframe(df, use_container_width=True, height=260)

        if st.button("🚀 Run Allocation", type="primary"):
            allocation, issues, summary = allocate_signals(
                df, spare_pct=spare_pct,
                separate_ab=separate_ab,
                keep_groups=keep_groups
            )

            st.subheader("2. Allocation result")
            st.dataframe(allocation, use_container_width=True, height=320)

            col1, col2, col3 = st.columns(3)
            col1.metric("Signals allocated", len(allocation))
            col2.metric("TQs / issues", len(issues))
            col3.metric("Cabinets", allocation["Cabinet"].nunique() if not allocation.empty else 0)

            st.subheader("3. TQ / rule report")
            if issues.empty:
                st.success("No prototype rule violations detected.")
            else:
                st.warning("Issues need engineering review.")
                st.dataframe(issues, use_container_width=True)

            st.subheader("4. Cabinet summary")
            st.dataframe(summary, use_container_width=True)

            xlsx = to_excel(allocation, issues, summary)
            st.download_button(
                "⬇️ Download Excel Report",
                data=xlsx,
                file_name="io_signal_sudoku_result.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"Could not process the file: {e}")
