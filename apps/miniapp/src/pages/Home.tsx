import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { listTokens, type Token } from "../lib/api";

function formatPrice(price: number): string {
  return price < 0.01 ? price.toFixed(8) : price.toFixed(4);
}

export function Home() {
  const [tokens, setTokens] = useState<Token[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listTokens()
      .then(setTokens)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="pt-app">
      <header className="pt-header">
        <div className="pt-logo">P</div>
        <div>
          <h1 className="pt-title">PlumTrader</h1>
          <p className="pt-subtitle">Memecoins e jettons na rede TON</p>
        </div>
      </header>

      {error && <div className="pt-alert">Não foi possível carregar tokens: {error}</div>}

      <section className="pt-section">
        {loading && <div className="pt-empty-state">Carregando tokens…</div>}

        {!loading && !error && tokens.length === 0 && (
          <div className="pt-empty-state">Nenhum token na watchlist ainda.</div>
        )}

        {tokens.length > 0 && (
          <ul className="pt-token-list">
            {tokens.map((token) => (
              <li key={token.address}>
                <Link to={`/token/${token.address}`} className="pt-token-row">
                  <div className="pt-token-identity">
                    <span className="pt-token-symbol">{token.symbol}</span>
                    <span className="pt-token-name">{token.name}</span>
                  </div>
                  {token.price_usd != null && (
                    <span className="pt-token-price">${formatPrice(token.price_usd)}</span>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
