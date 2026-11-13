# Import Member 2's Fuzzy Logic functions (works both when imported and when run directly)
try:
    from src.fuzzy_engine import calc_safetyMultiplier, get_crisisCategory
except ImportError:
    from fuzzy_engine import calc_safetyMultiplier, get_crisisCategory


def evaluate_item(item: dict, crisis_severity: float, safety_multiplier: float = None) -> dict:
    """
    Evaluates a single warehouse item using IF-THEN production rules and returns
    the replenishment decision, order quantity, dynamic reorder point, and
    plain-English Explainable AI (XAI) reasoning.
    """
    # Use Member 2's fuzzy engine if safety_multiplier wasn't already passed in
    if safety_multiplier is None:
        safety_multiplier = calc_safetyMultiplier(crisis_severity)
    crisis_label = get_crisisCategory(crisis_severity)

    # Calculate Dynamic Reorder Point (dynamic_rop)
    base_min = item["min_stock"]
    dynamic_rop = base_min * safety_multiplier

    current_stock = item["current_stock"]
    shelf_life_days = item["shelf_life_days"]

    action = "HOLD"
    reorder_qty = 0
    explanations = []

    # Rule 1: URGENT REPLENISH (Stock at or below dynamic ROP during high crisis >= 7.0)
    if current_stock <= dynamic_rop and crisis_severity >= 7.0:
        action = "URGENT_REPLENISH"
        target_stock = dynamic_rop * 2.5
        reorder_qty = int(round(target_stock - current_stock))
        explanations.append(
            f"URGENT: Stock ({current_stock}) is below Dynamic ROP ({dynamic_rop:.0f}) "
            f"during {crisis_label} crisis (Level {crisis_severity}/10)."
        )

    # Rule 2: ROUTINE REPLENISH (Stock at or below dynamic ROP during moderate crisis < 7.0)
    elif current_stock <= dynamic_rop and crisis_severity < 7.0:
        action = "ROUTINE_REPLENISH"
        target_stock = dynamic_rop * 2.0
        reorder_qty = int(round(target_stock - current_stock))
        explanations.append(
            f"ROUTINE: Stock ({current_stock}) dropped below Dynamic ROP ({dynamic_rop:.0f}) "
            f"under {crisis_label} conditions (Level {crisis_severity}/10)."
        )

    # Rule 3: EXPIRY RISK ALERT (30 days or less remaining with excess stock on shelf)
    if shelf_life_days <= 30 and current_stock > base_min:
        if action == "HOLD":
            action = "REDISTRIBUTE_EXPIRING"
        explanations.append(
            f"EXPIRY WARNING: Only {shelf_life_days} days left before expiry for {current_stock} units; prioritize dispatch."
        )

    # Rule 4: SAFE STOCK LEVEL (No reorder or expiry action triggered)
    if not explanations:
        explanations.append(
            f"SAFE: Stock ({current_stock}) is above Dynamic ROP ({dynamic_rop:.0f}). No reorder needed."
        )

    return {
        "item_id": item.get("item_id", "UNKNOWN"),
        "item_name": item.get("item_name", "Unknown Item"),
        "category": item.get("category", "General"),
        "action": action,
        "reorder_qty": max(0, reorder_qty),
        "dynamic_rop": round(dynamic_rop, 1),
        "explanation": " | ".join(explanations)
    }


# Quick local test block
if __name__ == "__main__":
    sample_items = [
        {"item_id": "ITEM01", "item_name": "Trauma Medical Kit", "category": "Health", "current_stock": 120, "min_stock": 300, "shelf_life_days": 180},
        {"item_id": "ITEM02", "item_name": "High-Energy Rations", "category": "Food", "current_stock": 1500, "min_stock": 800, "shelf_life_days": 15},
        {"item_id": "ITEM04", "item_name": "Water Purification Tabs", "category": "Sanitation", "current_stock": 8000, "min_stock": 2000, "shelf_life_days": 365},
    ]

    print("--- Testing Rule Engine at Crisis Severity 8.5 (Emergency) ---")
    for item in sample_items:
        result = evaluate_item(item, crisis_severity=8.5)
        print(f"{result['item_id']} ({result['item_name']}): Action={result['action']}, Order={result['reorder_qty']}, ROP={result['dynamic_rop']}")
        print(f"  Reason: {result['explanation']}\n")