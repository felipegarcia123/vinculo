"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type AuthSession } from "@/lib/api";
import { AuthSessionContext } from "@/components/AuthSessionContext";
import { VinculoBrand } from "@/components/VinculoBrand";

const homeByRole = { owner: "/loyalty/owner", cashier: "/loyalty/cashier", customer: "/loyalty" } as const;

export function AuthGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<AuthSession | null>(null);
  const [ready, setReady] = useState(pathname === "/login");

  useEffect(() => {
    if (pathname === "/login") { setReady(true); return; }
    let alive = true;
    setReady(false);
    api.currentUser().then(session => {
      if (!alive) return;
      setUser(session);
      const home = homeByRole[session.role];
      if (pathname !== home) router.replace(home);
      setReady(true);
    }).catch(() => {
      if (!alive) return;
      setUser(null); router.replace("/login");
    });
    return () => { alive = false; };
  }, [pathname, router]);

  if (pathname === "/login") return <>{children}</>;
  if (!ready || !user) return <main className="auth-loading" aria-live="polite">Validando sesión…</main>;
  const home = homeByRole[user.role];
  return <AuthSessionContext.Provider value={user}>
    <header className="app-bar"><Link href={home} aria-label="Inicio de Vínculo"><VinculoBrand compact /></Link>
      <span>{user.role === "owner" ? "Panel de fidelización" : user.role === "cashier" ? "Caja ficticia" : "Mi cartilla"}</span>
      <button type="button" onClick={() => { void api.logout().finally(() => window.location.assign("/login")); }}>Salir</button>
    </header>
    {children}
  </AuthSessionContext.Provider>;
}
