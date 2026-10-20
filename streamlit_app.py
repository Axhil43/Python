import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from metabolism_model import MetaMapModel, ENZYMES, ATP0

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="MetaMap-ML | Neural Metabolic Network",
    page_icon="🧬",
    layout="wide"
)

st.title("🧬 MetaMap-ML: Neural Metabolic Network & Pathway Topology")
st.markdown("Systems-level neural network prediction of cellular stress mapped across metabolic reaction topologies.")

# --- SIDEBAR CONTROL PANEL ---
st.sidebar.header("⚙️ Simulation & Neural Weights")

st.sidebar.subheader("Nutrient Influx Rates (mM/h)")
glucose_in = st.sidebar.slider("Glucose Intake Rate", 0.5, 20.0, 4.0, 0.5)
fructose_in = st.sidebar.slider("Fructose Intake Rate", 0.0, 10.0, 0.5, 0.1)
galactose_in = st.sidebar.slider("Galactose Intake Rate", 0.0, 5.0, 0.3, 0.1)

st.sidebar.subheader("Enzyme Activity Levels (0 = Blocked, 1 = Normal)")
activity_dict = {}

preset = st.sidebar.selectbox(
    "Clinical / Genetic Presets",
    ["Custom", "Healthy Baseline", "Hereditary Fructose Intolerance (ALDOB-def)", "Classic Galactosemia (GALT-def)", "Severe Polyol Stress (SORD-def)"]
)

if preset == "Hereditary Fructose Intolerance (ALDOB-def)":
    activity_dict["ALDOB"] = 0.05
elif preset == "Classic Galactosemia (GALT-def)":
    activity_dict["GALT"] = 0.05
elif preset == "Severe Polyol Stress (SORD-def)":
    activity_dict["SORD"] = 0.05

for enzyme in ENZYMES:
    if enzyme not in activity_dict:
        activity_dict[enzyme] = st.sidebar.slider(f"{enzyme} Activity", 0.0, 1.5, 1.0, 0.05)

# --- RUN SIMULATION & NEURAL MODEL ---
intake = {"Glucose": glucose_in, "Fructose": fructose_in, "Galactose": galactose_in}
model = MetaMapModel(intake=intake, activity=activity_dict)
model.simulate(hours=48)
score, contrib_df = model.stress()
table_df = model.pathway_table()
pools = model.result["pools"]

# --- TOP METRICS ROW ---
col1, col2, col3, col4 = st.columns(4)
stress_status = "NORMAL" if score < 20 else "ELEVATED" if score < 50 else "CRITICAL"
col1.metric("Neural Stress Score", f"{score:.1f} / 100", delta=stress_status, delta_color="inverse")

atp_delta = round(pools['ATP'] - ATP0, 2)
col2.metric("Intracellular ATP Pool", f"{pools['ATP']:.2f} mM", delta=f"{atp_delta} mM vs baseline", delta_color="normal")

flagged = table_df[table_df["Status"].str.startswith("BOTTLENECK")]["Enzyme"].tolist()
col3.metric("Flagged Bottlenecks", len(flagged), delta=", ".join(flagged) if flagged else "None", delta_color="off")

f1p_val = pools.get("F1P", 0)
col4.metric("F1P Accumulation", f"{f1p_val:.3f} mM", delta="Toxicity Risk" if f1p_val > 5 else "Normal", delta_color="inverse")

st.markdown("---")

# --- INTERACTIVE TABS ---
tab1, tab2, tab3 = st.tabs(["🕸️ Metabolic Network Topology Map", "📊 Metabolite Pools & Stress", "⚡ Reaction Flux Table"])

with tab1:
    st.subheader("Interactive Biochemical Pathway & Neural Node Topology")
    st.markdown("Visualizing metabolic flux nodes (Glycolysis, Fructolysis, Leloir, Polyol pathways) as an interconnected network graph.")

    # Generate network graph layout coordinates for metabolites & enzymes
    nodes = {
        "Glucose": (0, 2), "Fructose": (0, 1), "Galactose": (0, 0),
        "GCK": (1, 2.3), "PFK1": (2, 2.3), "KHK": (1, 1), "GALK1": (1, 0),
        "G6P": (1.5, 2), "F16BP": (2.5, 2), "F1P": (1.5, 1), "Gal1P": (1.5, 0),
        "ALDOB": (2, 1), "GALT": (2, 0), "Pyruvate": (3.5, 1.5), "AcetylCoA": (4.5, 1.5),
        "ATP": (5, 2.5), "Sorbitol": (1.5, -1), "Galactitol": (1.5, -2)
    }
    
    edge_x = []
    edge_y = []
    connections = [
        ("Glucose", "GCK"), ("GCK", "G6P"), ("G6P", "PFK1"), ("PFK1", "F16BP"), ("F16BP", "Pyruvate"),
        ("Fructose", "KHK"), ("KHK", "F1P"), ("F1P", "ALDOB"), ("ALDOB", "Pyruvate"),
        ("Galactose", "GALK1"), ("GALK1", "Gal1P"), ("Gal1P", "GALT"), ("GALT", "Pyruvate"),
        ("Pyruvate", "AcetylCoA"), ("Glucose", "Sorbitol"), ("Galactose", "Galactitol"),
        ("F1P", "ATP"), ("Gal1P", "ATP"), ("AcetylCoA", "ATP")
    ]
    
    for edge in connections:
        if edge[0] in nodes and edge[1] in nodes:
            x0, y0 = nodes[edge[0]]
            x1, y1 = nodes[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=1.5, color='#00f2fe'), hoverinfo='none', mode='lines')

    node_x = []
    node_y = []
    node_text = []
    node_color = []
    
    for node, coords in nodes.items():
        node_x.append(coords[0])
        node_y.append(coords[1])
        node_text.append(node)
        if node in ["F1P", "Gal1P", "Sorbitol", "Galactitol"] and pools.get(node, 0) > 1.0:
            node_color.append("#ff4b4b")  # Red for pathological buildup
        elif node == "ATP" and pools.get("ATP", 5.0) < 3.5:
            node_color.append("#ffaa00")  # Orange for depletion
        else:
            node_color.append("#00f2fe")  # Normal cyan node

    node_trace = go.Scatter(
        x=node_x, y=node_y, mode='text+markers',
        text=node_text, textposition="top center",
        marker=dict(showscale=False, color=node_color, size=18, line=dict(width=2, color='white'))
    )

    fig_net = go.Figure(data=[edge_trace, node_trace],
                 layout=go.Layout(
                    showlegend=False, hovermode='closest',
                    margin=dict(b=20,l=20,r=20,t=40),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)'
                ))
    st.plotly_chart(fig_net, use_container_width=True)

with tab2:
    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("Metabolite Pool Sizes (mM)")
        pool_df = pd.DataFrame(list(pools.items()), columns=["Metabolite", "Concentration"])
        fig_bar = px.bar(pool_df, x="Metabolite", y="Concentration", color="Concentration", color_continuous_scale="Viridis")
        fig_bar.update_layout(xaxis_tickangle=-45, margin=dict(l=20, r=20, t=30, b=80))
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with col_r:
        st.subheader("Neural Network Stress Attribution")
        fig_pie = px.pie(contrib_df[contrib_df["Contribution"] > 0], names="Feature", values="Contribution", hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
        fig_pie.update_layout(margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig_pie, use_container_width=True)

with tab3:
    st.subheader("Reaction Network & Bottleneck Diagnostics")
    def highlight_bottleneck(val):
        if "BOTTLENECK" in str(val):
            return "background-color: #ff4b4b; color: white; font-weight: bold;"
        return ""
    st.dataframe(table_df.style.applymap(highlight_bottleneck, subset=["Status"]), use_container_width=True, hide_index=True)
