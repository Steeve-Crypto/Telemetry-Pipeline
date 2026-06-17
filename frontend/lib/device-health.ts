export type DeviceHealth = "online" | "stale" | "offline";

export function deviceHealth(lastSeen: string): DeviceHealth {
  const ageMs = Date.now() - new Date(lastSeen).getTime();
  if (ageMs < 60_000) {
    return "online";
  }
  if (ageMs < 300_000) {
    return "stale";
  }
  return "offline";
}

export function healthLabel(health: DeviceHealth): string {
  switch (health) {
    case "online":
      return "Online";
    case "stale":
      return "Stale";
    default:
      return "Offline";
  }
}

export function healthColor(health: DeviceHealth): string {
  switch (health) {
    case "online":
      return "bg-accent";
    case "stale":
      return "bg-severity-medium";
    default:
      return "bg-severity-critical";
  }
}