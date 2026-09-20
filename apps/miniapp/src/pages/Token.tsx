import { TonConnectButton } from "@tonconnect/ui-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { PriceSparkline } from "../components/PriceSparkline";
import { getPriceHistory, getToken, type PricePoint, type Token as TokenData } from "../lib/api";

function truncateAddress(address: string): string {
  if (address.length <= 14) return address;
  return `${address.slice(0, 6)}…${address.slice(-6)}`;
}

// STON.fi é o mesmo DEX de onde já lemos pools/liquidez no backend — aqui só
// montamos o link público do swap deles (ft = token de origem, tt = destino),
// sem tentar montar a transação de swap nós mesmos (protocolo de roteamento
// do DEX é complexo demais pra arriscar um payload incorreto).
const STONFI_SWAP_URL = "https://app.ston.fi/swap";

const HISTORY_PERIODS = [
  { label: "1D", days: 1 },
  { label: "7D", days: 7 },
  { label: "30D", days: 30 },
] as const;

export function Token() {
  const { address = "" } = useParams();
  const [token, setToken] = useState<TokenData | null>(null);
  const [history, setHistory] = useState<PricePoint[]>([]);
  const [periodDays, setPeriodDays] = useState<number>(30);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getToken(address)
      .then(setToken)
      .catch((err: Error) => setError(err.message));
  }, [address]);

  useEffect(() => {
    // Histórico é "melhor esforço": se falhar, o resto da tela do token
    // continua funcionando normalmente, só sem o gráfico.
    getPriceHistory(address, periodDays)
      .then(setHistory)
      .catch(() => setHistory([]));
  }, [address, periodDays]);

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
            {token.image ? (
              <img src={token.image} alt={token.symbol} className="pt-logo-img" />
            ) : (
              <div className="pt-logo">{token.symbol.slice(0, 1)}</div>
            )}
            <div>
              <h1 className="pt-title">{token.symbol}</h1>
              <p className="pt-subtitle">{token.name}</p>
            </div>
          </header>

          <div className="pt-price-row">
            <span className="pt-price-big">
              {token.price_usd != null ? `$${token.price_usd.toFixed(6)}` : "—"}
            </span>
            {token.change_24h != null && (
              <span className={token.change_24h >= 0 ? "pt-positive-text" : "pt-negative-text"}>
                {token.change_24h >= 0 ? "▲" : "▼"} {Math.abs(token.change_24h).toFixed(2)}%
              </span>
            )}
          </div>

          {(token.verification || token.mintable != null) && (
            <div className="pt-badge-row">
              {token.verification === "whitelist" && (
                <span className="pt-positive-text">✓ Verificado pela TonAPI</span>
              )}
              {token.verification === "blacklist" && (
                <span className="pt-negative-text">⚠ Sinalizado pela TonAPI</span>
              )}
              {token.mintable === true && (
                <span className="pt-negative-text">⚠ Supply mutável (admin pode criar mais)</span>
              )}
            </div>
          )}

          {token.description && <p className="pt-token-description">{token.description}</p>}

          <div className="pt-card">
            <div className="pt-info-row">
              <span className="pt-stat-label">Cap. de Mercado</span>
              <span>{token.market_cap_usd != null ? `$${token.market_cap_usd.toLocaleString()}` : "—"}</span>
            </div>
            <div className="pt-info-row">
              <span className="pt-stat-label">Liquidez</span>
              <span>{token.liquidity_usd != null ? `$${token.liquidity_usd.toLocaleString()}` : "—"}</span>
            </div>
            <div className="pt-info-row">
              <span className="pt-stat-label">Holders</span>
              <span>{token.holders_count != null ? token.holders_count.toLocaleString() : "—"}</span>
            </div>
            <div className="pt-info-row">
              <span className="pt-stat-label">Total Supply</span>
              <span>
                {token.total_supply != null
                  ? `${token.total_supply.toLocaleString()} ${token.symbol}`
                  : "—"}
              </span>
            </div>
            <div className="pt-info-row">
              <span className="pt-stat-label">Mutável</span>
              <span>{token.mintable == null ? "—" : token.mintable ? "Sim" : "Não"}</span>
            </div>
          </div>

          <div className="pt-card" style={{ marginTop: 12 }}>
            <div className="pt-chart-header">
              <span className="pt-stat-label">Histórico de preço</span>
              <div className="pt-period-tabs">
                {HISTORY_PERIODS.map((period) => (
                  <button
                    key={period.days}
                    className={`pt-period-tab ${periodDays === period.days ? "pt-period-tab-active" : ""}`}
                    onClick={() => setPeriodDays(period.days)}
                  >
                    {period.label}
                  </button>
                ))}
              </div>
            </div>
            <PriceSparkline points={history} />
          </div>

          <div className="pt-card" style={{ marginTop: 12 }}>
            <div className="pt-info-row">
              <span className="pt-stat-label">Endereço</span>
              <span className="pt-address">{truncateAddress(token.address)}</span>
            </div>
            {token.admin_address && (
              <div className="pt-info-row">
                <span className="pt-stat-label">Owner</span>
                <span className="pt-address">{truncateAddress(token.admin_address)}</span>
              </div>
            )}
            <a href={token.tonscan_url} target="_blank" rel="noreferrer">
              Ver no Tonscan ↗
            </a>
          </div>

          <section className="pt-section">
            <TonConnectButton />
            <div className="pt-buy-sell-row">
              <a
                className="pt-button pt-buy-button"
                href={`${STONFI_SWAP_URL}?tt=${encodeURIComponent(token.address)}`}
                target="_blank"
                rel="noreferrer"
              >
                Comprar
              </a>
              <a
                className="pt-button pt-sell-button"
                href={`${STONFI_SWAP_URL}?ft=${encodeURIComponent(token.address)}`}
                target="_blank"
                rel="noreferrer"
              >
                Vender
              </a>
            </div>
            <p className="pt-token-description">
              Abre o swap no STON.fi (mesma fonte de liquidez usada aqui) — você assina direto na sua
              wallet conectada lá, o PlumTrader nunca guarda suas chaves.
            </p>
          </section>
        </>
      )}
    </div>
  );
}
