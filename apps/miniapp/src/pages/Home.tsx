import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { listTokens, type Token } from "../lib/api";

const PAGE_SIZE = 10;
const FEATURED_COUNT = 8;

function formatPrice(price: number): string {
  return price < 0.01 ? price.toFixed(8) : price.toFixed(4);
}

function formatLiquidity(value: number): string {
  return `$${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

type Tab = "featured" | "all";

export function Home() {
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>("featured");
  const [page, setPage] = useState(0);
  const [tokens, setTokens] = useState<Token[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setError(null);
    listTokens(PAGE_SIZE, page * PAGE_SIZE)
      .then((result) => {
        setTokens(result.items);
        setTotal(result.total);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [page]);

  // A API já ordena por liquidez desc, então os primeiros da página 0 são
  // os "destaques" de verdade — não é uma lista escolhida à mão.
  const featured = page === 0 ? tokens.slice(0, FEATURED_COUNT) : [];
  const tableRows = tab === "featured" ? tokens.slice(0, FEATURED_COUNT) : tokens;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  function openToken(address: string) {
    navigate(`/token/${address}`);
  }

  return (
    <div className="pt-app">
      <header className="pt-header">
        <img src="/icon.png" alt="PlumTrader" className="pt-logo-img" />
        <div>
          <h1 className="pt-title">PlumTrader</h1>
          <p className="pt-subtitle">Memecoins e jettons na rede TON</p>
        </div>
      </header>

      {error && <div className="pt-alert">Não foi possível carregar tokens: {error}</div>}

      {page === 0 && featured.length > 0 && (
        <div className="pt-featured-grid">
          {featured.map((token, i) => (
            <div
              key={token.address}
              className="pt-featured-card"
              onClick={() => openToken(token.address)}
              role="button"
            >
              <span className="pt-featured-rank">#{i + 1}</span>
              <span className="pt-featured-symbol">{token.symbol}</span>
              <span className="pt-featured-price">
                {token.price_usd != null ? `$${formatPrice(token.price_usd)}` : "—"}
              </span>
              {token.liquidity_usd != null && (
                <span className="pt-featured-liquidity">
                  Liquidez {formatLiquidity(token.liquidity_usd)}
                </span>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="pt-tabs">
        <button
          className="pt-tab"
          data-active={tab === "featured"}
          onClick={() => setTab("featured")}
        >
          Destaques
        </button>
        <button className="pt-tab" data-active={tab === "all"} onClick={() => setTab("all")}>
          Todos
        </button>
      </div>

      {loading && <div className="pt-empty-state">Carregando tokens…</div>}

      {!loading && !error && tableRows.length === 0 && (
        <div className="pt-empty-state">Nenhum token na watchlist ainda.</div>
      )}

      {!loading && tableRows.length > 0 && (
        <div className="pt-table-wrapper">
          <table className="pt-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Nome</th>
                <th style={{ textAlign: "right" }}>Preço</th>
                <th style={{ textAlign: "right" }}>Liquidez</th>
              </tr>
            </thead>
            <tbody>
              {tableRows.map((token, i) => (
                <tr key={token.address} onClick={() => openToken(token.address)}>
                  <td className="pt-table-rank">{page * PAGE_SIZE + i + 1}</td>
                  <td>
                    <div className="pt-table-name-cell">
                      <span className="pt-token-symbol">{token.symbol}</span>
                      <span className="pt-token-name">{token.name}</span>
                    </div>
                  </td>
                  <td className="pt-table-price">
                    {token.price_usd != null ? (
                      `$${formatPrice(token.price_usd)}`
                    ) : (
                      <span className="pt-muted">—</span>
                    )}
                  </td>
                  <td className="pt-table-liquidity">
                    {token.liquidity_usd != null ? (
                      formatLiquidity(token.liquidity_usd)
                    ) : (
                      <span className="pt-muted">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "all" && !loading && total > PAGE_SIZE && (
        <div className="pt-pagination">
          <span className="pt-pagination-info">
            Página {page + 1} de {totalPages} · {total} tokens
          </span>
          <div className="pt-pagination-controls">
            <button
              className="pt-button"
              disabled={page === 0}
              onClick={() => setPage((p) => Math.max(0, p - 1))}
            >
              ← Anterior
            </button>
            <button
              className="pt-button"
              disabled={page + 1 >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              Próxima →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
