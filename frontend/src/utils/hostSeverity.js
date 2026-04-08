export function classifyHostSeverity(computer) {
  if (!computer?.last_seen) {
    return "offline";
  }

  const lastSeen = new Date(computer.last_seen);
  const now = new Date();
  const diffHours = (now - lastSeen) / (1000 * 60 * 60);

  if (diffHours > 24) {
    return "offline";
  }

  const cpu = computer.cpu_usage_percent ?? 0;
  const memory = computer.memory_usage_percent ?? 0;
  const diskFree = computer.disk_free_percent ?? 100;

  if (cpu >= 90 || memory >= 90 || diskFree <= 10) {
    return "critical";
  }

  if (cpu >= 75 || memory >= 80 || diskFree <= 20) {
    return "warning";
  }

  return "healthy";
}

export function severityLabel(severity) {
  switch (severity) {
    case "critical":
      return "Crítico";
    case "warning":
      return "Atenção";
    case "offline":
      return "Offline";
    default:
      return "Saudável";
  }
}

export function severityClassName(severity) {
  switch (severity) {
    case "critical":
      return "status-critical";
    case "warning":
      return "status-warning";
    case "offline":
      return "status-offline";
    default:
      return "status-online";
  }
}
