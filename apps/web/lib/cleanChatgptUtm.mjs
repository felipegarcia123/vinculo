/** Remove only the exact ChatGPT source tag while preserving every other query part. */
export function stripChatgptUtmSource(url) {
  const rawParams = url.search.slice(1).split("&").filter(Boolean);
  let removed = false;
  const remaining = rawParams.filter((part) => {
    const entry = new URLSearchParams(part).entries().next().value;
    const [key, value] = entry ?? ["", ""];
    if (key === "utm_source" && value === "chatgpt.com") {
      removed = true;
      return false;
    }
    return true;
  });
  if (removed) url.search = remaining.length ? `?${remaining.join("&")}` : "";
  return removed;
}
