export function VinculoBrand({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`vinculo-brand${compact ? " vinculo-brand--compact" : ""}`}>
      <span className="vinculo-brand__mark" aria-hidden="true"><i /><i /><i /></span>
      <span className="vinculo-brand__name">Vínculo</span>
    </div>
  );
}
