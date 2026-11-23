"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { api } from "@/lib/api";
import { VinculoBrand } from "@/components/VinculoBrand";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const user = await api.login(username, password);
      const demoOnly = process.env.NEXT_PUBLIC_VINCULO_DEMO_ONLY === "true";
      window.location.assign(user.role === "customer" ? "/loyalty"
        : demoOnly ? (user.role === "owner" ? "/loyalty/owner" : "/loyalty/cashier") : "/");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No fue posible iniciar sesión");
      setBusy(false);
    }
  }

  return <main className="auth-page">
    <section className="auth-story" aria-labelledby="auth-story-title">
      <VinculoBrand />
      <div className="auth-story__copy">
        <p className="auth-story__eyebrow">Fidelización para tiendas de barrio</p>
        <h1 id="auth-story-title">Cada visita puede convertirse en una recompensa.</h1>
        <p className="auth-story__tagline">Conecta con tus clientes. Premia su fidelidad.</p>
      </div>
      <div className="auth-stamp-card" aria-hidden="true">
        <span className="auth-stamp-card__label">Una relación que crece</span>
        <div className="auth-stamp-card__path"><i /><i /><i /><i /><i /><span /></div>
        <span className="auth-stamp-card__caption">visita&nbsp; · &nbsp;compra&nbsp; · &nbsp;premio</span>
      </div>
    </section>
    <section className="auth-panel" aria-label="Acceso a Vínculo">
      <form className="auth-card" onSubmit={submit}>
        <p className="auth-form-kicker">Tu espacio de fidelización</p>
        <h2>Inicia sesión</h2>
        <p className="auth-form-intro">Ingresa con la cuenta que te compartieron para esta demostración.</p>
        <label htmlFor="vinculo-username">Usuario<input id="vinculo-username" name="username" autoComplete="username" autoCapitalize="none" value={username} onChange={event => setUsername(event.target.value)} required /></label>
        <label htmlFor="vinculo-password">Contraseña<input id="vinculo-password" name="password" type="password" autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)} required /></label>
        {error && <p className="auth-error" role="alert" aria-live="polite">{error}</p>}
        <button type="submit" disabled={busy}>{busy ? "Ingresando…" : "Entrar a Vínculo"}</button>
        <p className="auth-note">Demostración alojada con datos ficticios. Si necesitas acceso, contacta a quien organiza la evaluación.</p>
      </form>
      <footer className="auth-panel__footer">Acceso protegido · Vínculo</footer>
    </section>
  </main>;
}
