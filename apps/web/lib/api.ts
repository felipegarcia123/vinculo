const API = process.env.NEXT_PUBLIC_API_URL ?? (process.env.NODE_ENV === "development" ? "http://127.0.0.1:8000/api/v1" : "/api/v1");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const csrf = typeof document === "undefined" ? "" : document.cookie.split(";").map(v => v.trim())
    .find(v => v.startsWith("vinculo_csrf="))?.slice("vinculo_csrf=".length) ?? "";
  const method = (init?.method ?? "GET").toUpperCase();
  const headers: Record<string, string> = { "Content-Type": "application/json", ...(init?.headers as Record<string, string> | undefined) };
  if (csrf && !["GET", "HEAD", "OPTIONS"].includes(method)) headers["X-CSRF-Token"] = decodeURIComponent(csrf);
  const response = await fetch(`${API}${path}`, { ...init, credentials: "include", headers, cache: "no-store" });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(typeof body?.detail === "string" ? body.detail : "No fue posible completar la solicitud.");
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export type AuthSession = { id: string; name: string; username: string; role: "owner" | "cashier" | "customer"; expires_at?: string | null };
export type LoyaltyVisit = { id: string; created_at: string; purchase_total: string; stamps: number };
export type LoyaltyRedemption = { id: string; created_at: string; reward_name: string; stamps_spent: number };
export type LoyaltyAccount = { member_id: string; display_name: string; program: string; balance: number; reward_stamps: number; rewards: { id: string; name: string; stamps_cost: number; available: boolean }[]; visits: LoyaltyVisit[]; redemptions: LoyaltyRedemption[] };
export type LoyaltyQr = { token: string; purpose: "visit" | "redemption"; expires_at: string; expires_in_seconds: number; reward_name?: string | null };
export type LoyaltyAnalytics = { as_of: string; inactive_days: number; members_active: number; visits_last_30_days: number; stamps_earned_last_30_days: number; redemptions_last_30_days: number; inactive_members: { member_id: string; display_name: string; last_visit: string | null; days_inactive: number | null; never_visited: boolean }[]; pattern_breaks: { member_id: string; display_name: string; last_visit: string; usual_interval_days: number; days_since_visit: number }[]; members_without_pattern_data: number; members_never_visited: number; campaign_drafts: { id: string; status: "DRAFT"; label: string; basis: string; suggestion: string; message: string | null }[]; llm_available: boolean };
export type LoyaltyDemoCashierConfig = { product_name: string; purchase_total: string; minimum_purchase: string; stamps_per_purchase: number; reward_stamps: number; payment_label: string };
export type LoyaltyDemoPurchase = { purchase_id: string; member_id: string; display_name: string; purchase_total: string; stamps_awarded: number; balance: number; already_processed: boolean; simulated: true };

export const api = {
  login: (username: string, password: string) => request<AuthSession>("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  currentUser: () => request<AuthSession>("/auth/me"),
  logout: () => request<void>("/auth/logout", { method: "POST" }),
  loyaltyMe: () => request<LoyaltyAccount>("/loyalty/me"),
  issueLoyaltyQr: (body: { purpose: "visit" | "redemption"; reward_id?: string }) => request<LoyaltyQr>("/loyalty/qr", { method: "POST", body: JSON.stringify(body) }),
  consumeLoyaltyRedemption: (token: string) => request<{ redemption_id: string; reward_name: string; balance: number; already_consumed: boolean }>("/loyalty/qr/redemption/consume", { method: "POST", body: JSON.stringify({ token }) }),
  loyaltyAnalytics: () => request<LoyaltyAnalytics>("/loyalty/analytics"),
  explainLoyaltyInsights: (explain_with_llm = false) => request<{ mode: "deterministic" | "llm"; explanation: string }>("/loyalty/insights/explain", { method: "POST", body: JSON.stringify({ explain_with_llm }) }),
  loyaltyDemoCashierConfig: () => request<LoyaltyDemoCashierConfig>("/loyalty/demo/cashier/config"),
  loyaltyDemoPurchase: (token: string) => request<LoyaltyDemoPurchase>("/loyalty/demo/cashier/purchase", { method: "POST", body: JSON.stringify({ token }) }),
};
