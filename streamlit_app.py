import streamlit as st
import pandas as pd
from metabolism_model import MetaMapModel, ENZYMES, ATP0

st.set_page_config(page_title="MetaMap-ML Dashboard", layout="wide")

st.title("🧬 MetaMap-ML: Metabolic Pathways & Bottleneck Simulator")
st.markdown("Interactive systems-level simulation of human metabolic pathways, cellular stress scoring, and enzyme deficiency prediction.")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("Nutrient Inflow (mM/h)")
glucose_in = st.sidebar.slider("Glucose Intake", 1.0, 20.0, 4.0, 0.5)
fructose_in = st.sidebar.slider("Fructose Intake", 0.0, 10.0, 0.5, 0.1)
galactose_in = st.sidebar.slider("Galactose Intake", 0.0, 5.0, 0.3, 0.1)

st.sidebar.header("Enzyme Activity Levels (0 = Dead, 1 = Normal)")
activity_dict = {}
for enzyme in ENZYMES:
    default_val = 1.0
    # Add presets for classic conditions
    activity_dict[enzyme] = st.sidebar.slider(f"{enzyme} Activity", 0.0, 1.5, default_val, 0.01)

# --- RUN SIMULATION ---
intake = {"Glucose": glucose_in, "Fructose": fructose_in, "Galactose": galactose_in}
model = MetaMapModel(intake=intake, activity=activity_dict)
model.simulate(hours=48)
score, contrib_df = model.stress()
table_df = model.pathway_table()

# --- MAIN DASHBOARD DISPLAY ---
col1, col2, col3 = st.columns(3)

level = "LOW" if score < 20 else "MODERATE" if score < 50 else "HIGH"
col1.metric("Cellular Stress Score", f"{score:.1f} / 100", level, delta_color="inverse")
col2.metric("ATP Level", f"{model.result['pools']['ATP']:.2f} mM", f"Set-point: {ATP0} mM")

flagged = table_df[table_df["Status"].str.startswith(("BOTTLENECK", "SATURATED"))]["Enzyme"].unique()
col3.metric("Flagged Bottlenecks", ", ".join(flagged) if len(flagged) > 0 else "None")

st.markdown("---")

# Stress Breakdown Table
st.subheader("📊 Cellular Stress Breakdown (Sigma-Sum Model)")
st.dataframe(contrib_df, use_container_width=True)

# Pathway Status Table
st.subheader("⚡ Reaction Network & Bottleneck Status")
st.dataframe(table_df, use_container_width=True)
