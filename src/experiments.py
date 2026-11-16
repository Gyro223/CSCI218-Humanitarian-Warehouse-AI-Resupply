import os
import sys
import random
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Safe non-interactive backend for saving PNG charts
import matplotlib.pyplot as plt

# Allow running either from project root (python src/experiments.py) or inside src/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from src.fuzzy_engine import calc_safetyMultiplier, get_crisisCategory
    from src.knowledge_base import evaluate_item
except ImportError:
    from fuzzy_engine import calc_safetyMultiplier, get_crisisCategory
    from knowledge_base import evaluate_item


def run_simulation(df: pd.DataFrame, scenario_name: str, crisis_schedule: list, use_ai: bool, seed: int = 42) -> dict:
    """
    Simulates multi-day warehouse operations under a given crisis schedule.
    Compares:
      - use_ai=True : Hybrid Fuzzy Logic + IF-THEN Rule Engine (with expiry redistribution)
      - use_ai=False: Static Baseline (fixed min_stock reorder point, no fuzzy buffer, no expiry rule)
    """
    random.seed(seed)

    # Initialize mutable inventory state per item
    inventory = []
    for _, row in df.iterrows():
        inventory.append({
            "item_id": row["item_id"],
            "item_name": row["item_name"],
            "category": row["category"],
            "current_stock": int(row["current_stock"]),
            "min_stock": int(row["min_stock"]),
            "lead_time_days": int(row["lead_time_days"]),
            "shelf_life_days": int(row["shelf_life_days"]),
            "unit_cost_usd": float(row["unit_cost_usd"]),
            "pending_orders": []  # list of (arrival_day, qty)
        })

    total_demanded = 0
    total_fulfilled = 0
    stockout_events = 0
    expired_units = 0
    redistributed_units = 0
    total_procurement_cost = 0.0
    daily_fill_rates = []

    for day, crisis_level in enumerate(crisis_schedule, start=1):
        day_demanded = 0
        day_fulfilled = 0
        safety_mult = calc_safetyMultiplier(crisis_level) if use_ai else 1.0

        for item in inventory:
            # 1. Receive any replenishment shipments arriving today
            arrived_qty = sum(qty for arr_day, qty in item["pending_orders"] if arr_day == day)
            item["pending_orders"] = [(arr_day, qty) for arr_day, qty in item["pending_orders"] if arr_day > day]
            if arrived_qty > 0:
                item["current_stock"] += arrived_qty
                # Fresh shipment resets batch shelf life to at least 90 days if previous batch was low
                item["shelf_life_days"] = max(item["shelf_life_days"], 90)

            # 2. Simulate daily humanitarian dispatch demand (scales with crisis severity)
            base_daily_demand = max(1, int(item["min_stock"] * 0.12))
            crisis_demand_factor = 0.6 + (crisis_level / 5.0)  # ~0.8x in routine, ~2.5x in emergency
            demand = max(1, int(round(base_daily_demand * crisis_demand_factor * random.uniform(0.8, 1.25))))

            fulfilled = min(item["current_stock"], demand)
            item["current_stock"] -= fulfilled

            if fulfilled < demand:
                stockout_events += 1

            day_demanded += demand
            day_fulfilled += fulfilled

            # 3. Advance shelf life by 1 day and check spoilage
            item["shelf_life_days"] -= 1
            if item["shelf_life_days"] <= 0 and item["current_stock"] > 0:
                expired_units += item["current_stock"]
                item["current_stock"] = 0
                item["shelf_life_days"] = 90  # Reset shelf tracking once empty

            # 4. Replenishment & Expiry Decision Policy
            has_open_order = len(item["pending_orders"]) > 0

            if use_ai:
                decision = evaluate_item(item, crisis_level, safety_mult)
                action = decision["action"]
                reorder_qty = decision["reorder_qty"]

                # Proactive redistribution prevents spoilage before shelf life hits 0
                if item["shelf_life_days"] <= 15 and item["current_stock"] > item["min_stock"]:
                    excess = item["current_stock"] - item["min_stock"]
                    redistributed_units += excess
                    item["current_stock"] -= excess
                    item["shelf_life_days"] = 60

                if action in ("URGENT_REPLENISH", "ROUTINE_REPLENISH") and reorder_qty > 0 and not has_open_order:
                    arrival_day = day + item["lead_time_days"]
                    item["pending_orders"].append((arrival_day, reorder_qty))
                    total_procurement_cost += reorder_qty * item["unit_cost_usd"]
            else:
                # Static Baseline Policy: fixed min_stock threshold, fixed 2.0x target, no expiry rule
                if item["current_stock"] <= item["min_stock"] and not has_open_order:
                    reorder_qty = max(0, int(round((item["min_stock"] * 2.0) - item["current_stock"])))
                    if reorder_qty > 0:
                        arrival_day = day + item["lead_time_days"]
                        item["pending_orders"].append((arrival_day, reorder_qty))
                        total_procurement_cost += reorder_qty * item["unit_cost_usd"]

        total_demanded += day_demanded
        total_fulfilled += day_fulfilled
        fill_rate = (day_fulfilled / day_demanded * 100.0) if day_demanded > 0 else 100.0
        daily_fill_rates.append(round(fill_rate, 2))

    overall_fill_rate = (total_fulfilled / total_demanded * 100.0) if total_demanded > 0 else 100.0

    return {
        "Scenario": scenario_name,
        "Model": "Hybrid Fuzzy + Rule AI" if use_ai else "Static Baseline",
        "Fill_Rate_Pct": round(overall_fill_rate, 2),
        "Stockout_Events": stockout_events,
        "Expired_Units": expired_units,
        "Redistributed_Units": redistributed_units,
        "Procurement_Cost_USD": round(total_procurement_cost, 2),
        "Daily_Fill_Rates": daily_fill_rates,
    }


def main():
    os.makedirs("plots", exist_ok=True)
    df = pd.read_csv("data/inventory.csv")

    # Define 30-day crisis test scenarios
    scenarios = {
        "Routine (Lvl 2.0)": [2.0] * 30,
        "Escalating (Lvl 5.5)": [5.5] * 30,
        "Emergency (Lvl 9.0)": [9.0] * 30,
        "Sudden Crisis Shock": [2.5] * 8 + [6.0] * 7 + [9.5] * 10 + [4.0] * 5,
    }

    summary_rows = []
    shock_series = {}

    for name, schedule in scenarios.items():
        base_res = run_simulation(df, name, schedule, use_ai=False)
        ai_res = run_simulation(df, name, schedule, use_ai=True)

        summary_rows.append({k: v for k, v in base_res.items() if k != "Daily_Fill_Rates"})
        summary_rows.append({k: v for k, v in ai_res.items() if k != "Daily_Fill_Rates"})

        if name == "Sudden Crisis Shock":
            shock_series["Static Baseline"] = base_res["Daily_Fill_Rates"]
            shock_series["Hybrid Fuzzy + Rule AI"] = ai_res["Daily_Fill_Rates"]

    results_df = pd.DataFrame(summary_rows)
    results_df.to_csv("plots/benchmark_results.csv", index=False)

    print("\n=== DUBAI HUMANITARIAN WAREHOUSE AI: 30-DAY BENCHMARK RESULTS ===")
    print(results_df.to_string(index=False))

    # --- CHART 1: Service Fill Rate (%) Across Scenarios ---
    scenario_labels = list(scenarios.keys())
    base_fills = [results_df[(results_df["Scenario"] == s) & (results_df["Model"] == "Static Baseline")]["Fill_Rate_Pct"].values[0] for s in scenario_labels]
    ai_fills = [results_df[(results_df["Scenario"] == s) & (results_df["Model"] == "Hybrid Fuzzy + Rule AI")]["Fill_Rate_Pct"].values[0] for s in scenario_labels]

    x = range(len(scenario_labels))
    width = 0.35

    plt.figure(figsize=(9, 5))
    plt.bar([i - width / 2 for i in x], base_fills, width, label="Static Baseline", color="#95a5a6")
    plt.bar([i + width / 2 for i in x], ai_fills, width, label="Hybrid Fuzzy + Rule AI", color="#1b4f72")
    plt.ylabel("Demand Fill Rate (%)")
    plt.title("Humanitarian Demand Fill Rate: Static Baseline vs. Hybrid AI")
    plt.xticks(list(x), scenario_labels, rotation=10)
    plt.ylim(0, 110)
    plt.legend()
    plt.grid(axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.savefig("plots/fill_rate_comparison.png", dpi=300)
    plt.close()

    # --- CHART 2: Stockout Events Comparison ---
    base_outs = [results_df[(results_df["Scenario"] == s) & (results_df["Model"] == "Static Baseline")]["Stockout_Events"].values[0] for s in scenario_labels]
    ai_outs = [results_df[(results_df["Scenario"] == s) & (results_df["Model"] == "Hybrid Fuzzy + Rule AI")]["Stockout_Events"].values[0] for s in scenario_labels]

    plt.figure(figsize=(9, 5))
    plt.bar([i - width / 2 for i in x], base_outs, width, label="Static Baseline", color="#c0392b")
    plt.bar([i + width / 2 for i in x], ai_outs, width, label="Hybrid Fuzzy + Rule AI", color="#27ae60")
    plt.ylabel("Total Stockout Incidents (30 Days)")
    plt.title("Stockout Incidents Prevented by Dynamic Fuzzy Safety Buffers")
    plt.xticks(list(x), scenario_labels, rotation=10)
    plt.legend()
    plt.grid(axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.savefig("plots/stockouts_comparison.png", dpi=300)
    plt.close()

    # --- CHART 3: Daily Fill Rate Trajectory During Sudden Crisis Shock ---
    days = list(range(1, 31))
    plt.figure(figsize=(9, 5))
    plt.plot(days, shock_series["Static Baseline"], marker="o", linewidth=2, label="Static Baseline", color="#c0392b")
    plt.plot(days, shock_series["Hybrid Fuzzy + Rule AI"], marker="s", linewidth=2, label="Hybrid Fuzzy + Rule AI", color="#1b4f72")
    plt.axvspan(16, 25, color="#f9e79f", alpha=0.45, label="Peak Emergency Window (Lvl 9.5)")
    plt.xlabel("Simulation Day")
    plt.ylabel("Daily Service Fill Rate (%)")
    plt.title("System Resilience Under Sudden Crisis Shock (Days 1–30)")
    plt.ylim(0, 108)
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.savefig("plots/sudden_shock_trajectory.png", dpi=300)
    plt.close()

    print("\nCharts saved successfully inside 'plots/' folder:")
    print("  - plots/fill_rate_comparison.png")
    print("  - plots/stockouts_comparison.png")
    print("  - plots/sudden_shock_trajectory.png")
    print("  - plots/benchmark_results.csv")


if __name__ == "__main__":
    main()
