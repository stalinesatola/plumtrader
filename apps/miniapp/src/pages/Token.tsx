import { TonConnectButton, useTonConnectUI } from "@tonconnect/ui-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getToken, type Token as TokenData } from "../lib/api";
import { buildSwapTransaction } from "../lib/tonconnect";

function truncateAddress(address: string): string {
  if (address.length <= 14) return address;
  return `${address.slice(0, 6)}…${address.slice(-6)}`;
}

export function Token() {
  const { address = "" } = useParams();
  const [token, setToken] = useState<TokenData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tonConnectUI] = useTonConnectUI();

  useEffect(() => {
    getToken(address)
      .then(setToken)
      .catch((err: Error) => setError(err.message));
  }, [address]);

  async function handleSwap() {
    if (!token) return;

    // O PlumTrader nunca assina por conta própria: monta a transação e pede
    // para a wallet conectada (via TonConnect) assinar e enviar.
    const tx = buildSwapTransaction({
      fromAddress: tonConnectUI.account?.address ?? "",
      toJetton: token.address,
      amountNano: "50000000", // 0.05 TON de exemplo
      validUntil: Math.floor(Date.now() / 1000) + 300,
    });

    await tonConnectUI.sendTransaction(tx);
  }

  return (
    <div className="pt-app">
      <Link to="/" className="pt-back-link">
        ← Voltar
      </Link>

      {error && <div className="pt-alert">Erro: {error}</div>}
      {!token && !error && <div className="pt-empty-state">Carregando…</div>}

      {token && (
        <>
          <header className="pt-header">
            <div className="pt-logo">{token.symbol.slice(0, 1)}</div>
            <div>
              <h1 className="pt-title">{token.symbol}</h1>
              <p className="pt-subtitle">{token.name}</p>
            </div>
          </header>

          <div className="pt-card">
            <span className="pt-address">{truncateAddress(token.address)}</span>

            <div className="pt-stat-grid">
              <div className="pt-stat">
                <div className="pt-stat-label">Preço</div>
                <div className="pt-stat-value">
                  {token.price_usd != null ? `$${token.price_usd.toFixed(6)}` : "—"}
                </div>
              </div>
              <div className="pt-stat">
                <div className="pt-stat-label">Liquidez</div>
                <div className="pt-stat-value">
                  {token.liquidity_usd != null ? `$${token.liquidity_usd.toLocaleString()}` : "—"}
                </div>
              </div>
            </div>

            <a href={token.tonscan_url} target="_blank" rel="noreferrer">
              Ver no Tonscan ↗
            </a>
          </div>

          <section className="pt-section">
            <TonConnectButton />
            <button className="pt-button" onClick={handleSwap} disabled={!tonConnectUI.connected}>
              Comprar via wallet conectada
            </button>
          </section>
        </>
      )}
    </div>
  );
}
