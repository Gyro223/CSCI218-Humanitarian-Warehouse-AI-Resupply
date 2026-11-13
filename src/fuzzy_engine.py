def calc_safetyMultiplier(crisisSeverity: float):
    """Converts the continuous Crisis Severity Index from a scale of (1 -> 10)
    into a Dynamic Safety Stock Multiplier (1x to 2.2x) using piecewise fuzzy sets:
        -Routinge (1 -> 3) : 1x
        -Escalating (3.1 -> 7.0): Smoothly scales from 1x to 1.5x
        -Catastrophic (7.1 -> 10.0): Smoothly scales from 1.5x to 2.2x """
    severity = max(1,min(10, float(crisisSeverity)))#resitricts input between 1 and 10 to prevent out of bounds errors

    if severity <= 3:
        multiplier = 1
    elif severity <= 7:
        #mult = min mult + ((severity - min severity)/severity range)* (max mult - min mult)
        multiplier = 1 + ((severity - 3)/4)*0.5 #linear interpolation from 1x(at 3) to 1.5x(at 7)
    else:
        multiplier = 1.5 + ((severity - 7)/3)*0.7 #linear interpolation from 1.5x(at 7) to 2.2x(at 10)

    return round(multiplier,2)


#maps crisis severity to a dynamic safety multiplier 
def get_crisisCategory(crisisSeverity: float) -> str:
    """Returns the fuzzy linguistic label for the dashboard (human readable)"""
    severity = max(1, min(10, float(crisisSeverity)))
    if severity <= 3:
        return "Routine"
    elif severity <= 7:
        return "Escalating"
    else:
        return "Emergency"


# local test block
if __name__ == "__main__":
    test_levels = [1.0, 3.0, 5.0, 7.0, 8.5, 10.0]
    for level in test_levels:
        mult = calc_safetyMultiplier(level)
        label = get_crisisCategory(level)
        print(f"Crisis Severity: {level:4.1f} ({label:<12}) -> Safety Multiplier: {mult:.2f}x")
