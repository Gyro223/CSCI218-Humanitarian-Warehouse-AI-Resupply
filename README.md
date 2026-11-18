# Smart Humanitarian Warehouse Replenishment Expert System

## Project overview

The Smart Humanitarian Warehouse Replenishment Expert System is a prototype decision support system for inventory planning in humanitarian warehouses that has been implemented in Python. It assists a warehouse coordinator to check relief supplies under various crisis situations and to know what to replenish, how much to order and why a decision was taken.

The user chooses a **Crisis Severity Index (CSC) ranging from 1.0 to 10.0** in an interactive Streamlit dashboard. That severity is translated to a safety-stock multiplier using a fuzzy-logic controller. An IF-THEN production-rule engine then performs a calculation for each inventory item, and returns an action, a suggested reorder quantity, a dynamic reorder point, and a plain-English explanation.

The project is based on a sample set of 15 humanitarian relief items in the following categories: Health, Food, Shelter, Sanitation, and Power. It is an academic prototype that is not linked to a live warehouse, supplier, transport or emergency-management system.

## Main features

A slider for the severity is available on a dashboard with a range from 1.0 to 10.0 in steps of 0.5.
Fuzzy safety-stock multiplier: The multiplier is between 1.0x and 2.2x and rises with the severity of the crisis.
Dynamic reorder point: The dynamic reorder point for each item is set to be `min_stock * safety_multiplier`.
The rule engine determines one of four actions: URGENT_REPLENISH, ROUTINE_REPLENISH, REDISTRIBUTE_EXPIRING, or HOLD.
The dashboard shows the suggested quantity and estimated cost based on the unit cost in the sample data set for replenishment actions.
Explainable AI decision log: Every item is accompanied by a simple description in natural language of the condition that caused the decision.
- Inventory filtering and summary cards: Users can view reorder counts, urgent alerts, expiry alerts and the estimated replenishment budget.
A separate experiment script is used to compare the hybrid approach to a static baseline across four 30-day crisis scenarios.

## System architecture

There are two layers of decisions and a dashboard in the system:

The Fuzzy Logic Controller (`src/fuzzy_engine.py`) maps the severity of the crisis input to a safety-stock multiplier and a readable crisis category.
2. IF-THEN Production Rule Engine (`src/knowledge_base.py`) - Computes the dynamic reorder point, enforces replenishment and expiry rules, and provides an explanation for each item.
3. Streamlit Dashboard (app.py) - loads data/inventory.csv, feeds selected severity and multiplier into the rule engine and displays the output.
4. Experiment and benchmark module (`src/experiments.py`) - simulates demand and replenishment over 30 days, compares the hybrid system with a static baseline, and saves a summary in CSV format and plots in plots/ dir.

### Crisis severity mapping

| Emergency | High | High |
|---|---:|---:|
| Routine | 1.0-3.0 | 1.0x |
| Escalating | Above 3.0 to 7.0 | Increases linearly from 1.0x to 1.5x |
| Emergency | Above 7.0 to 10.0 | Increases linearly from 1.5x to 2.2x |

### Production-rule actions

- **`URGENT_REPLENISH`** - The current stock level is below or equal to the dynamic reorder point and the crisis severity is 7.0 or higher. The goal is to set the target at 2.5 times the dynamic reorder point.
- **`ROUTINE_REPLENISH`** - current stock is at or below the dynamic reorder point and the crisis severity is less than 7.0. Target is 2.0 x the dynamic reorder point.
- **`REDISTRIBUTE_EXPIRING`** - the item has 30 days or less on the shelf and inventory is above the base minimum level. The engine raises an expiry warning, and performs this action if no replenishment action has been given priority.
- **`HOLD`** - No replenishment or expiry action is triggered, stock level is considered safe.

## Repository structure

Run commands from the repository root. The project expects the files to be organised as follows:

```text
CSCI218-Humanitarian-Warehouse-AI/
├── data/
│   └── inventory.csv
├── src/
│   ├── fuzzy_engine.py
│   ├── knowledge_base.py
│   └── experiments.py
├── plots/                         # Created/updated by the experiment script
│   ├── benchmark_results.csv
│   ├── fill_rate_comparison.png
│   ├── stockouts_comparison.png
│   └── sudden_shock_trajectory.png
├── app.py
├── requirements.txt
├── run_app.bat                    # Optional Windows launcher
└── README.md
```

## Requirements

- A working Python 3 installation (use a version supported by your installed Streamlit release).
- The Python packages listed in `requirements.txt`:
  - `streamlit`
  - `pandas`
  - `matplotlib`

## Setup and installation

1. Clone or download the team repository.
2. Open a terminal in the repository root (the folder containing `app.py` and `requirements.txt`).
3. Create and activate a virtual environment.

**Windows (Command Prompt):**

```bash
python -m venv .venv
.venv\Scripts\activate
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

4. Install the dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

5. Confirm that `data/inventory.csv` is in the `data/` folder and the two engine modules are in `src/`.

## Run the dashboard

From the repository root, run:

```bash
python -m streamlit run app.py
```

Streamlit prints a local URL in the terminal. Open that address in a browser. On Windows, the optional `run_app.bat` file can also be used from the repository root.

## Use the dashboard

2. Run the dashboard as shown above.
Set the **Crisis Severity Index** slider to a value between 1.0 and 10.0.
Go to the sidebar and read the crisis category and safety-stock multiplier.
Filter the inventory by sector (optional).
5. Reread the summary cards and the Inventory Evaluation & Explainable AI Decision Log table.
6. Review the action, dynamic reorder point, suggested reorder quantity, estimated cost and explanation of each item.

The estimated budget is a model output and is not a supplier quote/purchase order.

## Run the benchmark experiments

From the repository root, run:

```bash
python -m src.experiments
```

The script runs for 30 days for each of the following crisis schedules with seed `42`:

- Routine (Level 2.0)
- Escalating (Level 5.5)
- Emergency (Level 9.0)
- Sudden Crisis Shock (Levels 2.5, 6.0, 9.5, and 4.0 across the 30-day period)

It compares the **Static Baseline** with the **Hybrid Fuzzy + Rule AI** and saves the results in the file `benchmark_results.csv`, and three visualisations in the directory `plots/`.

### Verified benchmark summary

| 100% fill rate | 50%/50% fill rate | 0 stockout incidents | 0 stockout incidents |
|---|---:|---:|---:|---:|
| Routine (Level 2.0) | 96.13% | 96.09% | 61 | 62 |
| Escalating (Level 5.5) | 85.31% | 90.62% | 123 | 91 |
| Emergency (Level 9.0) | 74.04% | 90.74% | 192 | 88 |
| Sudden Crisis Shock | 80.66% | 87.11% | 142 | 104 |

In the routine scenario, the hybrid system will record 51 fewer expired units (51 for the baseline and 0 for the hybrid system) and distribute 622 units. In that scenario, its fill rate is 0.04 percentage points lower than the baseline; its procurement-cost difference is only USD 102.50 (about 0.01%). The hybrid system achieves a 104-point reduction in stockout incidents and a 16.70 % increase in fill rate at level 9.0, while the procurement cost premium is about 70.5%.

The results presented are the results of the project seeded 30-day simulation, and are considered to be prototype benchmark results and not as proof of actual operational performance.

## Limitations and future work

The dashboard is based on a sample dataset instead of a warehouse database.
The simulation or representation of lead time, demand and supplier lead time is based on fixed dataset values, and does not relate to the live operation.
Current shelf-life logic is Item-level not Batch-level. A production implementation should allow for batch level FEFO (First-Expired, First-Out) tracking.
Severity of the crisis is manually selected. It could be estimated in the future using humanitarian situation reports and adding transport disruption and supplier reliability as additional inputs.
- The system is only a decision support system. Any real procurement or distribution decision needs to be approved by a warehouse manager, who must validate recommendations.

## Team contributions

| Member | Main contribution |
|---|---|
| Anas | IF-THEN production-rule engine and Explainable AI; report Section (b) |
| Jonathan Kidson | Fuzzy Logic safety-stock multiplier controller; report Section (c) |
| Syed Arsal Saeed | 15-item dataset, Streamlit dashboard, and integration; report Sections (d) and (e) |
| Naim | 30-day simulation, benchmarking, and charts; report Section (f) |
| Calvin | Domain framing, conclusion, README, appendices, and final report formatting; report Sections (a) and (g) |

## Course project

**Course:** CSCI218 - Foundations of Artificial Intelligence  
**Project:** Smart Humanitarian Warehouse Replenishment Expert System
