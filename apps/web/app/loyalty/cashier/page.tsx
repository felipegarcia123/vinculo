"use client";

import { useEffect, useState, type FormEvent } from "react";
import { api, type LoyaltyDemoCashierConfig, type LoyaltyDemoPurchase } from "@/lib/api";

export default function VinculoDemoCashierPage() {
  const [config, setConfig] = useState<LoyaltyDemoCashierConfig | null>(null);
  const [visitToken, setVisitToken] = useState("");
  const [redemptionToken, setRedemptionToken] = useState("");
  const [purchase, setPurchase] = useState<LoyaltyDemoPurchase | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => { void api.loyaltyDemoCashierConfig().then(setConfig).catch(cause => setError(cause instanceof Error ? cause.message : "No fue posible cargar la caja ficticia")); }, []);

  async function simulatePurchase(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(""); setMessage(""); setPurchase(null);
    try {
      const result = await api.loyaltyDemoPurchase(visitToken.trim());
      setPurchase(result);
      setMessage(result.already_processed ? "Este QR ya se había procesado; no se agregó otro sello." : "Compra ficticia completada. El sello ya aparece en la cartilla.");
      setVisitToken("");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "No fue posible procesar la compra ficticia"); }
    finally { setBusy(false); }
  }

  async function validateRedemption(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(""); setMessage(""); setPurchase(null);
    try {
      const result = await api.consumeLoyaltyRedemption(redemptionToken.trim());
      setMessage(result.already_consumed ? `Canje ya validado: ${result.reward_name}. No se descontaron sellos otra vez.` : `Canje validado: ${result.reward_name}. Saldo restante: ${result.balance} sellos.`);
      setRedemptionToken("");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "No fue posible validar el canje"); }
    finally { setBusy(false); }
  }

  return <main className="loyalty-home vinculo-demo-cashier">
    <p className="loyalty-eyebrow">Caja de demostración</p>
    <h1>Registra una compra ficticia</h1>
    <p className="vinculo-demo-intro">Valida el QR del cliente y simula una compra elegible. No se mueve dinero ni se contactan servicios externos.</p>
    {config && <section className="vinculo-demo-product" aria-label="Compra simulada">
      <span>Artículo de prueba</span><strong>{config.product_name}</strong>
      <p>${Number(config.purchase_total).toLocaleString("es-CO")} COP · {config.stamps_per_purchase} sello por compra · mínimo ${Number(config.minimum_purchase).toLocaleString("es-CO")} COP</p>
      <small>{config.payment_label}</small>
    </section>}
    <form onSubmit={simulatePurchase} className="vinculo-demo-form">
      <label htmlFor="vinculo-demo-visit-qr">QR temporal de visita</label>
      <input id="vinculo-demo-visit-qr" autoComplete="off" value={visitToken} onChange={event => setVisitToken(event.target.value)} placeholder="Escanea o pega el código del cliente" required />
      <button type="submit" disabled={busy || !config}>{busy ? "Procesando…" : "Simular compra y acreditar sello"}</button>
    </form>
    <form onSubmit={validateRedemption} className="vinculo-demo-form vinculo-demo-form--secondary">
      <label htmlFor="vinculo-demo-redemption-qr">QR de canje</label>
      <input id="vinculo-demo-redemption-qr" autoComplete="off" value={redemptionToken} onChange={event => setRedemptionToken(event.target.value)} placeholder="Escanea o pega el código del premio" required />
      <button type="submit" className="vinculo-demo-secondary-button" disabled={busy}>Validar canje</button>
    </form>
    {error && <p className="auth-error" role="alert">{error}</p>}
    {message && <p className="vinculo-demo-result" role="status">{message}</p>}
    {purchase && <section className="vinculo-demo-receipt" aria-label="Compra ficticia registrada">
      <h2>Compra simulada</h2>
      <p>Cliente: {purchase.display_name}</p>
      <p>Total ficticio: ${Number(purchase.purchase_total).toLocaleString("es-CO")} COP</p>
      <p>Saldo de sellos: {purchase.balance}</p>
      <small>Referencia de prueba: {purchase.purchase_id.slice(0, 8)}</small>
    </section>}
  </main>;
}
