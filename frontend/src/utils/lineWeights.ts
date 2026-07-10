import { CalcResult, LineItem } from "../api/client";

function round2(value: number): number {
  return Math.round(value * 100) / 100;
}

export function recalcTotals(lines: LineItem[]): CalcResult["totals"] {
  const included = lines.filter((line) => line.include);
  const withWeight = included.filter((line) => line.weight_total_kg != null);
  return {
    line_count: lines.length,
    included_count: included.length,
    total_quantity: included.reduce((sum, line) => sum + (line.quantity || 0), 0),
    total_weight_kg: round2(withWeight.reduce((sum, line) => sum + (line.weight_total_kg || 0), 0)),
    total_material_volume_m3: round2(included.reduce((sum, line) => sum + (line.material_volume_m3 || 0), 0)),
    total_transport_volume_m3: round2(included.reduce((sum, line) => sum + (line.transport_volume_m3 || 0), 0)),
    warning_count: lines.filter((line) => line.status === "warning" || line.status === "needs_review").length,
    error_count: lines.filter((line) => line.status === "error").length,
  };
}

export function applyLineWeightChange(
  lines: LineItem[],
  lineId: number,
  field: "weight_each_kg" | "weight_total_kg",
  value: number | null,
): LineItem[] {
  return lines.map((line) => {
    if (line.line_id !== lineId) return line;
    const qty = line.quantity && line.quantity > 0 ? line.quantity : 1;
    if (value == null || Number.isNaN(value)) {
      return { ...line, weight_each_kg: null, weight_total_kg: null };
    }
    if (field === "weight_each_kg") {
      return {
        ...line,
        weight_each_kg: round2(value),
        weight_total_kg: round2(value * qty),
      };
    }
    return {
      ...line,
      weight_total_kg: round2(value),
      weight_each_kg: round2(value / qty),
    };
  });
}

export function scaleLinesToTotalWeight(lines: LineItem[], newTotal: number): LineItem[] {
  if (newTotal < 0 || Number.isNaN(newTotal)) return lines;
  const included = lines.filter((line) => line.include);
  if (included.length === 0) return lines;

  const currentTotal = included.reduce((sum, line) => sum + (line.weight_total_kg || 0), 0);
  if (currentTotal <= 0) {
    const perLine = newTotal / included.length;
    return lines.map((line) => {
      if (!line.include) return line;
      const qty = line.quantity && line.quantity > 0 ? line.quantity : 1;
      const total = round2(perLine);
      return { ...line, weight_total_kg: total, weight_each_kg: round2(total / qty) };
    });
  }

  const factor = newTotal / currentTotal;
  return lines.map((line) => {
    if (!line.include) return line;
    const qty = line.quantity && line.quantity > 0 ? line.quantity : 1;
    const base = line.weight_total_kg ?? 0;
    const total = round2(base * factor);
    return { ...line, weight_total_kg: total, weight_each_kg: round2(total / qty) };
  });
}

export function weightOverridesFromLines(lines: LineItem[]) {
  return lines
    .filter((line) => line.weight_each_kg != null || line.weight_total_kg != null)
    .map((line) => ({
      line_id: line.line_id,
      ...(line.weight_each_kg != null ? { weight_each_kg: line.weight_each_kg } : {}),
      ...(line.weight_total_kg != null ? { weight_total_kg: line.weight_total_kg } : {}),
    }));
}
