export function formatMonthYear(value?: string): string | undefined {
  if (!value) return undefined;
  const match = /^(\d{4})-(\d{2})/.exec(value);
  if (!match) return value;
  const year = Number(match[1]);
  const month = Number(match[2]);
  if (!Number.isInteger(year) || month < 1 || month > 12) return value;
  return new Intl.DateTimeFormat("en", {
    month: "short",
    timeZone: "UTC",
    year: "numeric",
  }).format(new Date(Date.UTC(year, month - 1, 1)));
}

export function formatYear(value?: string): string | undefined {
  return value?.slice(0, 4) || undefined;
}
