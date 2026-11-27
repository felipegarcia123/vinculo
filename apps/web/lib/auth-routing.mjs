/** @typedef {"owner" | "cashier" | "customer"} UserRole */

const homeByRole = Object.freeze({
  owner: "/loyalty/owner",
  cashier: "/loyalty/cashier",
  customer: "/loyalty",
});

/** @param {UserRole} role */
export function homeForRole(role) {
  return homeByRole[role] ?? "/login";
}
