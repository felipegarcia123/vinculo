"use client";

import { useEffect, useState } from "react";
import { api, type LoyaltyAnalytics } from "@/lib/api";
import { VinculoBrand } from "@/components/VinculoBrand";

export default function LoyaltyOwnerPage() {
  const [metrics, setMetrics] = useState<LoyaltyAnalytics | null>(null);
  const [explanation, setExplanation] = useState("");
  const [mode, setMode] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  async function load() {
    setLoading(true);
    try { setMetrics(await api.loyaltyAnalytics()); setError(""); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "No fue posible cargar el dashboard"); }
    finally { setLoading(false); }
  }
  useEffect(() => { void load(); }, []);
  async function explain(withLlm: boolean) {
    try { const result = await api.explainLoyaltyInsights(withLlm); setExplanation(result.explanation); setMode(result.mode === "llm" ? "Explicación con LLM" : "Explicación determinista"); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "No fue posible explicar los hallazgos"); }
  }
  return <main className="loyalty-home loyalty-dashboard">
    <header className="loyalty-brand-heading"><VinculoBrand compact /><p>Conecta con tus clientes. Premia su fidelidad.</p></header>
    <p className="auth-eyebrow">Fidelización · solo propietario</p><h1>Visitas y lealtad</h1>
    {error && <p role="alert">{error}</p>}
    {loading && <p role="status">Cargando métricas…</p>}
    {metrics && <>
      <p>Datos calculados al {new Date(metrics.as_of).toLocaleString("es-CO")}. Inactividad: {metrics.inactive_days} días.</p>
      <div className="loyalty-kpis">
        <article><strong>{metrics.members_active}</strong><span>miembros activos</span></article>
        <article><strong>{metrics.visits_last_30_days}</strong><span>visitas últimos 30 días</span></article>
        <article><strong>{metrics.stamps_earned_last_30_days}</strong><span>sellos acreditados</span></article>
        <article><strong>{metrics.redemptions_last_30_days}</strong><span>canjes completados</span></article>
      </div>
      <section><h2>Clientes inactivos</h2>{metrics.inactive_members.length ? <ul>{metrics.inactive_members.map(member => <li key={member.member_id}>{member.display_name} · {member.never_visited ? "sin visitas registradas" : `${member.days_inactive} días sin visita`}</li>)}</ul> : <p>No hay miembros inactivos según esta regla.</p>}</section>
      <section><h2>Ruptura de patrón habitual</h2>{metrics.pattern_breaks.length ? <ul>{metrics.pattern_breaks.map(member => <li key={member.member_id}>{member.display_name} · intervalo usual {member.usual_interval_days} días · última visita hace {member.days_since_visit} días</li>)}</ul> : <p>No se detectaron rupturas. Se requieren al menos tres visitas por cliente; {metrics.members_without_pattern_data} miembros aún no tienen historial suficiente.</p>}</section>
      <section><h2>Propuestas de campaña</h2><p>Todas quedan como borradores. No se envían promociones automáticamente.</p><ul>{metrics.campaign_drafts.map(item => <li key={item.id}><strong>{item.label}</strong><p>{item.basis}</p><p>{item.suggestion}</p>{item.message && <blockquote>{item.message}</blockquote>}<span className="loyalty-draft">BORRADOR</span></li>)}</ul></section>
      <section><h2>Explicar hallazgos</h2><button onClick={() => void explain(false)}>Explicar con reglas</button> <button disabled={!metrics.llm_available} onClick={() => void explain(true)}>Usar LLM opcional</button><p>{metrics.llm_available ? "Proveedor configurado; la llamada solo ocurre al solicitarla." : "LLM desactivado o sin credenciales: se usa explicación determinista."}</p>{explanation && <div aria-live="polite"><strong>{mode}</strong><p>{explanation}</p></div>}</section>
      <button onClick={() => void load()}>Actualizar métricas</button>
    </>}
  </main>;
}
