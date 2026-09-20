const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8080";

export interface Token {
  address: string;
  symbol: string;
  name: string;
  image?: string | null;
  description?: string | null;
  mintable?: boolean | null;
  verification?: string | null;
  price_usd?: number | null;
  liquidity_usd?: number | null;
  holders_count?: number | null;
  market_cap_usd?: number | null;
  change_24h?: number | null;
  change_7d?: number | null;
  change_30d?: number | null;
  tonscan_url: string;
}

export type TokenSort = "liquidity" | "market_cap";

export interface TokenPage {
  items: Token[];
  total: number;
}

export interface PricePoint {
  timestamp: string;
  price_usd: number;
}

export interface TonPrice {
  price_usd: number | null;
  diff_24h: string | null;
  diff_7d: string | null;
  diff_30d: string | null;
}

async function getJSON<T>(path: string): Promise<T> {
  const resp = await fetch(`${API_BASE_URL}${path}`);
  if (!resp.ok) {
    throw new Error(`API error ${resp.status} on ${path}`);
  }
  return resp.json() as Promise<T>;
}

export function listTokens(
  limit: number,
  offset: number,
  q?: string,
  sort: TokenSort = "liquidity",
): Promise<TokenPage> {
  const query = q ? `&q=${encodeURIComponent(q)}` : "";
  return getJSON<TokenPage>(`/api/tokens/?limit=${limit}&offset=${offset}&sort=${sort}${query}`);
}

export function getToken(address: string): Promise<Token> {
  return getJSON<Token>(`/api/tokens/${address}`);
}

export function getPriceHistory(address: string, days = 30): Promise<PricePoint[]> {
  return getJSON<PricePoint[]>(`/api/tokens/${address}/price-history?days=${days}`);
}

export function getTonPrice(): Promise<TonPrice> {
  return getJSON<TonPrice>("/api/ton-price");
}
