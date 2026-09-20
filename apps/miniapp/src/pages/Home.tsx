import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getTonPrice, listTokens, type Token, type TokenSort, type TonPrice } from "../lib/api";

const PAGE_SIZE = 10;
const FEATURED_COUNT = 8;
const SEARCH_DEBOUNCE_MS = 300;

function formatPrice(price: number): string {
  return price < 0.01 ? price.toFixed(8) : price.toFixed(4);
}

function formatLiquidity(value: number): string {
  return `$${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

function ChangeCell({ pct }: { pct: number | null | undefined }) {
  if (pct == null) return <span className="pt-muted">—</span>;
  const isUp = pct >= 0;
  return (
    <span className={isUp ? "pt-positive-text" : "pt-negative-text"}>
      {isUp ? "▲" : "▼"} {Math.abs(pct).toFixed(2)}%
    </span>
  );
}

export function Home() {
  const navigate = useNavigate();
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [tokens, setTokens] = useState<Token[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tonPrice, setTonPrice] = useState<TonPrice | null>(null);
  const [sort, setSort] = useState<TokenSort>("liquidity");

  useEffect(() => {
    // GRAM (ticker desde o rebrand de jun/2026, ex-Toncoin/TON) é a moeda
    // nativa da rede — não é um jetton, então não aparece na tabela de
    // tokens e vem de um endpoint à parte. A rede continua se chamando
    // TON (The Open Network); só o nome de exibição da moeda mudou, por
    // isso a API (TonAPI) continua usando "ton" como identificador.
    getTonPrice()
      .then(setTonPrice)
      .catch(() => setTonPrice(null));
  }, []);

  // Debounce: só dispara a busca no backend depois que o usuário para de
  // digitar, e volta pra página 0 a cada nova busca.
  useEffect(() => {
    const timer = setTimeout(() => {
      setPage(0);
      setSearch(searchInput.trim());
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    setLoading(true);
    setError(null);
    listTokens(PAGE_SIZE, page * PAGE_SIZE, search || undefined, sort)
      .then((result) => {
        setTokens(result.items);
        setTotal(result.total);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [page, search, sort]);

  // A API já ordena por liquidez desc, então os primeiros da página 0 (sem
  // busca ativa) são os "destaques" de verdade — não é uma lista escolhida
  // à mão. Com busca ativa, os cards de destaque não fazem sentido.
  const featured = page === 0 && !search ? tokens.slice(0, FEATURED_COUNT) : [];
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  function openToken(address: string) {
    navigate(`/token/${address}`);
  }

  function changeSort(next: TokenSort) {
    setSort(next);
    setPage(0);
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

      {tonPrice?.price_usd != null && (
        <div className="pt-card pt-ton-banner">
          <div>
            <div className="pt-stat-label">GRAM (rede TON)</div>
            <div className="pt-stat-value">${formatPrice(tonPrice.price_usd)}</div>
          </div>
          {tonPrice.diff_24h && (
            <span className={tonPrice.diff_24h.startsWith("-") ? "pt-negative-text" : "pt-positive-text"}>
              {tonPrice.diff_24h.startsWith("-") ? "▼" : "▲"} {tonPrice.diff_24h.replace(/^[+-]/, "")} (24h)
            </span>
          )}
        </div>
      )}

      <div className="pt-tabs">
        <button
          className="pt-tab"
          data-active={sort === "liquidity"}
          onClick={() => changeSort("liquidity")}
        >
          Liquidez
        </button>
        <button
          className="pt-tab"
          data-active={sort === "market_cap"}
          onClick={() => changeSort("market_cap")}
        >
          Capitalização
        </button>
      </div>

      <input
        type="search"
        className="pt-search"
        placeholder="Buscar por nome, símbolo ou endereço…"
        value={searchInput}
        onChange={(e) => setSearchInput(e.target.value)}
      />

      {error && <div className="pt-alert">Não foi possível carregar tokens: {error}</div>}

      {featured.length > 0 && (
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

      {loading && <div className="pt-empty-state">Carregando tokens…</div>}

      {!loading && !error && tokens.length === 0 && (
        <div className="pt-empty-state">
          {search ? `Nenhum token encontrado para "${search}".` : "Nenhum token na watchlist ainda."}
        </div>
      )}

      {!loading && tokens.length > 0 && (
        <div className="pt-table-wrapper">
          <table className="pt-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Nome</th>
                <th style={{ textAlign: "right" }}>Preço</th>
                <th style={{ textAlign: "right" }}>24h</th>
                <th style={{ textAlign: "right" }}>Cap. de Mercado</th>
                <th style={{ textAlign: "right" }}>Liquidez</th>
              </tr>
            </thead>
            <tbody>
              {tokens.map((token, i) => (
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
                  <td className="pt-table-price">
                    <ChangeCell pct={token.change_24h} />
                  </td>
                  <td className="pt-table-liquidity">
                    {token.market_cap_usd != null ? (
                      formatLiquidity(token.market_cap_usd)
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

      {!loading && total > PAGE_SIZE && (
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
