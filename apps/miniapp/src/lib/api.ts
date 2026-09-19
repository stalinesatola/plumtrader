const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8080";

export interface Token {
  address: string;
  symbol: string;
  name: string;
  image?: string | null;
  price_usd?: number | null;
  liquidity_usd?: number | null;
  tonscan_url: string;
}

export interface TokenPage {
  items: Token[];
  total: number;
}

export interface PricePoint {
  timestamp: string;
  price_usd: number;
}

async function getJSON<T>(path: string): Promise<T> {
  const resp = await fetch(`${API_BASE_URL}${path}`);
  if (!resp.ok) {
    throw new Error(`API error ${resp.status} on ${path}`);
  }
  return resp.json() as Promise<T>;
}

export function listTokens(limit: number, offset: number, q?: string): Promise<TokenPage> {
  const query = q ? `&q=${encodeURIComponent(q)}` : "";
  return getJSON<TokenPage>(`/api/tokens/?limit=${limit}&offset=${offset}${query}`);
}

export function getToken(address: string): Promise<Token> {
  return getJSON<Token>(`/api/tokens/${address}`);
}

export function getPriceHistory(address: string, days = 30): Promise<PricePoint[]> {
  return getJSON<PricePoint[]>(`/api/tokens/${address}/price-history?days=${days}`);
}
