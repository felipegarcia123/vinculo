"use client";

import { useCallback, useEffect, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { api, type LoyaltyAccount, type LoyaltyQr } from "@/lib/api";
import { VinculoBrand } from "@/components/VinculoBrand";

export default function LoyaltyHomePage() {
  const [account, setAccount] = useState<LoyaltyAccount | null>(null);
  const [error, setError] = useState("");
  const [qr, setQr] = useState<LoyaltyQr | null>(null);
  const [seconds, setSeconds] = useState(0);
  const [busy, setBusy] = useState(false);
  const refresh = useCallback(() => api.loyaltyMe().then(setAccount).catch(cause => setError(cause instanceof Error ? cause.message : "No fue posible cargar la cuenta")), []);
  useEffect(() => { void refresh(); const poll = window.setInterval(() => void refresh(), 5000); return () => window.clearInterval(poll); }, [refresh]);
  useEffect(() => { if (!qr) return; const tick = () => setSeconds(Math.max(0, Math.ceil((Date.parse(qr.expires_at) - Date.now()) / 1000))); tick(); const timer = window.setInterval(tick, 1000); return () => window.clearInterval(timer); }, [qr]);
  async function issue(purpose: "visit" | "redemption", reward_id?: string) {
    setBusy(true); setError("");
    try { setQr(await api.issueLoyaltyQr({ purpose, ...(reward_id ? { reward_id } : {}) })); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "No fue posible generar el QR"); }
    finally { setBusy(false); }
  }
  return <main className="loyalty-home">
    <header className="loyalty-brand-heading"><VinculoBrand compact /><p>Conecta con tus clientes. Premia su fidelidad.</p></header>
    <h1>Tu fidelidad</h1>
    {error && <p role="alert">{error}</p>}
    {account && <section><h2>Hola, {account.display_name}</h2><p>{account.program}</p>
      <p><strong>{account.balance}</strong> de {account.reward_stamps} sellos para el siguiente premio</p>
      <div className="loyalty-progress" role="progressbar" aria-label="Progreso al premio" aria-valuenow={Math.min(account.balance, account.reward_stamps)} aria-valuemin={0} aria-valuemax={account.reward_stamps}><span style={{ width: `${Math.min(100, account.balance / account.reward_stamps * 100)}%` }} /></div>
      <button disabled={busy} onClick={() => void issue("visit")}>Generar QR de visita</button>
      {qr && seconds > 0 && <section className="loyalty-qr" aria-label="Código QR temporal"><QRCodeSVG value={qr.token} size={224} level="M" marginSize={4} title="QR temporal de fidelización" /><p>{qr.purpose === "visit" ? "Muestra este código en caja para vincular la compra" : `Canje: ${qr.reward_name}`}</p><strong>Vence en {seconds} s</strong><details><summary>Mostrar código manual</summary><code>{qr.token}</code></details></section>}
      {qr && seconds === 0 && <p role="status">El QR venció. Genera uno nuevo.</p>}
      <h3>Premios</h3><ul>{account.rewards.map(reward => <li key={reward.id}>{reward.name} · {reward.stamps_cost} sellos{!reward.available ? " · Agotado" : ""} {reward.available && account.balance >= reward.stamps_cost && <button disabled={busy} onClick={() => void issue("redemption", reward.id)}>Generar QR de canje</button>}</li>)}</ul>
      <h3>Visitas</h3>{account.visits.length ? <ul>{account.visits.map(item => <li key={item.id}>{new Date(item.created_at).toLocaleString("es-CO")} · {item.stamps} sello(s) · ${Number(item.purchase_total).toLocaleString("es-CO")}</li>)}</ul> : <p>Aún no tienes visitas registradas.</p>}
      <h3>Canjes</h3>{account.redemptions.length ? <ul>{account.redemptions.map(item => <li key={item.id}>{new Date(item.created_at).toLocaleString("es-CO")} · {item.reward_name} · {item.stamps_spent} sellos</li>)}</ul> : <p>Aún no tienes premios canjeados.</p>}
    </section>}
  </main>;
}
