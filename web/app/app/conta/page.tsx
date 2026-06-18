export default function ContaPage() {
  return (
    <div>
      <div className="badge">CONTA · ASSINATURA</div>
      <div className="box panel-card">
        <div className="plan">
          <div className="plan-name">ZOROTHAX PRO</div>
          <div className="plan-price">
            R$11,90<span>/mês</span>
          </div>
          <ul className="dash-list">
            <li>✓ Clips ilimitados (você usa sua própria chave de IA)</li>
            <li>✓ Sem créditos — custo de IA é o real, direto na OpenRouter</li>
            <li>✓ Análise viral multimodal, legenda karaokê, reframe automático</li>
          </ul>
          <button className="btn" style={{ alignSelf: "flex-start" }} disabled>
            ASSINAR (em breve)
          </button>
        </div>
      </div>
      <p className="hint">Pagamento em construção (Fase 5).</p>
    </div>
  );
}
