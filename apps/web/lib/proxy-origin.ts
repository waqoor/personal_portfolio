function firstHeaderValue(value: string | null): string | undefined {
  const first = value?.split(",", 1)[0]?.trim();
  return first || undefined;
}

export function publicRequestOrigin(headers: Headers, fallbackOrigin: string): string {
  const protocol = firstHeaderValue(headers.get("x-forwarded-proto"));
  const host =
    firstHeaderValue(headers.get("x-forwarded-host")) ??
    firstHeaderValue(headers.get("host"));

  if (
    (protocol !== "http" && protocol !== "https") ||
    !host ||
    /[\s/\\]/.test(host)
  ) {
    return new URL(fallbackOrigin).origin;
  }
  return new URL(`${protocol}://${host}`).origin;
}

export function isSameOriginMutation(headers: Headers, fallbackOrigin: string): boolean {
  const origin = headers.get("origin");
  const fetchSite = headers.get("sec-fetch-site");
  if (fetchSite && fetchSite !== "same-origin" && fetchSite !== "none") return false;
  if (!origin) return true;
  try {
    return new URL(origin).origin === publicRequestOrigin(headers, fallbackOrigin);
  } catch {
    return false;
  }
}
