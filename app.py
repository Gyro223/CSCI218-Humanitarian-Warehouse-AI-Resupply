import streamlit as st
import pandas as pd
from src.fuzzy_engine import calc_safetyMultiplier, get_crisisCategory
from src.knowledge_base import evaluate_item

# 1. Page Setup
st.set_page_config(page_title="Humanitarian Warehouse AI", layout="wide")
st.title("Humanitarian Warehouse Expert System")
st.markdown("Automated stock replenishment decisions driven by Fuzzy Logic and IF-THEN Production Rules.")

# 2. Sidebar Controls (Connected to Member 2's Fuzzy Engine)
st.sidebar.header("Controls")
crisis_level = st.sidebar.slider("Crisis Severity Index", min_value=1.0, max_value=10.0, value=5.0, step=0.5)

safety_mult = calc_safetyMultiplier(crisis_level)
crisis_label = get_crisisCategory(crisis_level)

st.sidebar.metric("Crisis Status", crisis_label)
st.sidebar.metric("Safety Stock Multiplier", f"{safety_mult:.2f}x")

# 3. Load Inventory Dataset
try:
    df = pd.read_csv("data/inventory.csv")
except FileNotFoundError:
    st.error("Missing 'data/inventory.csv'. Make sure inventory.csv is inside the 'data' folder.")
    st.stop()

# Category Filter in Sidebar
categories = ["All"] + sorted(df["category"].unique().tolist())
selected_cat = st.sidebar.selectbox("Filter by Sector", categories)

# 4. Run Member 1's IF-THEN Rule Engine on Every Item
results = []
for _, row in df.iterrows():
    item_dict = row.to_dict()
    res = evaluate_item(item_dict, crisis_level, safety_mult)
    res["current_stock"] = row["current_stock"]
    res["min_stock"] = row["min_stock"]
    res["shelf_life_days"] = row["shelf_life_days"]
    res["unit_cost_usd"] = row["unit_cost_usd"]
    res["total_cost_usd"] = res["reorder_qty"] * row["unit_cost_usd"]
    results.append(res)

res_df = pd.DataFrame(results)

if selected_cat != "All":
    res_df = res_df[res_df["category"] == selected_cat]

# 5. Summary Metric Cards
col1, col2, col3, col4 = st.columns(4)
col1.metric("Items Needing Reorder", len(res_df[res_df["action"].isin(["URGENT_REPLENISH", "ROUTINE_REPLENISH"])]))
col2.metric("Urgent Crisis Alerts", len(res_df[res_df["action"] == "URGENT_REPLENISH"]))
col3.metric("Expiry Alerts", len(res_df[res_df["action"] == "REDISTRIBUTE_EXPIRING"]))
col4.metric("Est. Replenishment Budget", f"${res_df['total_cost_usd'].sum():,.2f}")

# 6. Color-Coded Decision Table
def highlight_action(col):
    colors = {
        "URGENT_REPLENISH": "background-color: #ffcccc; color: #900000; font-weight: bold;",
        "ROUTINE_REPLENISH": "background-color: #fff3cd; color: #856404; font-weight: bold;",
        "REDISTRIBUTE_EXPIRING": "background-color: #d1ecf1; color: #0c5460; font-weight: bold;",
        "HOLD": "background-color: #d4edda; color: #155724;",
    }
    return [colors.get(val, "") for val in col]

st.subheader("Inventory Evaluation & Explainable AI Decision Log")
display_cols = [
    "item_id", "item_name", "category", "current_stock",
    "dynamic_rop", "action", "reorder_qty", "total_cost_usd", "explanation"
]

styled_df = res_df[display_cols].style.apply(highlight_action, subset=["action"]).format({
    "dynamic_rop": "{:.0f}",
    "total_cost_usd": "${:,.2f}"
})

st.dataframe(styled_df, use_container_width=True)