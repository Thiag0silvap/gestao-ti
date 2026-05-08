export function normalizeSector(value) {
  const normalized = (value || "").trim().toLocaleUpperCase("pt-BR");

  if (normalized === "TI") {
    return "TECNOLOGIA";
  }

  return normalized;
}

export function formatSector(value) {
  return normalizeSector(value) || "-";
}
