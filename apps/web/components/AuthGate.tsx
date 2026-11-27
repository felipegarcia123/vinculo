"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, ApiError, type AuthSession } from "@/lib/api";
import { homeForRole } from "@/lib/auth-routing.mjs";
import { AuthSessionContext } from "@/components/AuthSessionContext";
import { VinculoBrand } from "@/components/VinculoBrand";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<AuthSession | null>(null);
  const [authError, setAuthError] = useState("");
  const [retry, setRetry] = useState(0);
  const [ready, setReady] = useState(pathname === "/login");

  useEffect(() => {
    if (pathname === "/login") { setReady(true); return; }
    let alive = true;
    setReady(false);
    setAuthError("");
    api.currentUser().then(session => {
      if (!alive) return;
      setUser(session);
      const home = homeForRole(session.role);
      if (pathname !== home) router.replace(home);
      setReady(true);
    }).catch(cause => {
      if (!alive) return;
      setUser(null);
      if (cause instanceof ApiError && cause.status === 401) {
        router.replace("/login");
        return;
      }
      setAuthError("No pudimos validar tu sesión. Comprueba tu conexión y vuelve a intentarlo.");
      setReady(true);
    });
    return () => { alive = false; };
  }, [pathname, router, retry]);

  if (pathname === "/login") return <>{children}</>;
  if (!ready) return <main className="auth-loading" aria-live="polite">Validando sesión…</main>;
  if (authError) return <main className="auth-loading" aria-live="polite">
    <section><p role="alert" className="auth-error">{authError}</p>
      <button type="button" onClick={() => setRetry(value => value + 1)}>Reintentar</button>
      <p><Link href="/login">Volver al inicio de sesión</Link></p>
    </section>
  </main>;
  if (!user) return <main className="auth-loading" aria-live="polite">Redirigiendo al inicio de sesión…</main>;
  const home = homeForRole(user.role);
  return <AuthSessionContext.Provider value={user}>
    <header className="app-bar"><Link href={home} aria-label="Inicio de Vínculo"><VinculoBrand compact /></Link>
      <span>{user.role === "owner" ? "Panel de fidelización" : user.role === "cashier" ? "Caja ficticia" : "Mi cartilla"}</span>
      <button type="button" onClick={() => { void api.logout().finally(() => window.location.assign("/login")); }}>Salir</button>
    </header>
    {children}
  </AuthSessionContext.Provider>;
}
