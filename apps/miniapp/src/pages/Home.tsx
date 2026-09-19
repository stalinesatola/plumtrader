import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { listTokens, type Token } from "../lib/api";

export function Home() {
  const [tokens, setTokens] = useState<Token[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listTokens()
      .then(setTokens)
      .catch((err: Error) => setError(err.message));
  }, []);

  return (
    <main>
      <h1>PlumTrader</h1>
      <p>Memecoins e jettons em destaque na rede TON</p>

      {error && <p role="alert">Não foi possível carregar tokens: {error}</p>}

      <ul>
        {tokens.map((token) => (
          <li key={token.address}>
            <Link to={`/token/${token.address}`}>
              {token.symbol} — {token.name}
              {token.price_usd != null && <span> · ${token.price_usd.toFixed(6)}</span>}
            </Link>
          </li>
        ))}
      </ul>

      {tokens.length === 0 && !error && <p>Nenhum token na watchlist ainda.</p>}
    </main>
  );
}
