// Package indexerclient contains the HTTP client the api-gateway uses to
// talk to the Python indexer service, which aggregates data from TonAPI,
// STON.fi and DeDust.
package indexerclient

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"time"
)

type Client struct {
	baseURL string
	http    *http.Client
}

func NewClient(baseURL string) *Client {
	return &Client{
		baseURL: baseURL,
		// O indexer roda no plano free do Render, que "dorme" depois de
		// ociosidade e leva ~30-50s pra acordar (cold start). Um timeout
		// curto faria o gateway desistir e devolver 502 antes disso.
		http: &http.Client{Timeout: 60 * time.Second},
	}
}

func (c *Client) get(path string, out any) error {
	resp, err := c.http.Get(c.baseURL + path)
	if err != nil {
		return fmt.Errorf("indexer request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("indexer returned status %d for %s", resp.StatusCode, path)
	}

	return json.NewDecoder(resp.Body).Decode(out)
}

func (c *Client) ListTokens(limit, offset int, q, sort string) (*TokenPage, error) {
	var page TokenPage
	path := fmt.Sprintf("/tokens?limit=%d&offset=%d", limit, offset)
	if q != "" {
		path += "&q=" + url.QueryEscape(q)
	}
	if sort != "" {
		path += "&sort=" + url.QueryEscape(sort)
	}
	if err := c.get(path, &page); err != nil {
		return nil, err
	}
	return &page, nil
}

type TokenPage struct {
	Items []Token `json:"items"`
	Total int     `json:"total"`
}

func (c *Client) GetToken(address string) (*Token, error) {
	var token Token
	if err := c.get("/tokens/"+address, &token); err != nil {
		return nil, err
	}
	return &token, nil
}

func (c *Client) GetPriceHistory(address string, days int) ([]PricePoint, error) {
	var points []PricePoint
	path := fmt.Sprintf("/tokens/%s/price-history?days=%d", address, days)
	if err := c.get(path, &points); err != nil {
		return nil, err
	}
	return points, nil
}

type PricePoint struct {
	Timestamp string  `json:"timestamp"`
	PriceUSD  float64 `json:"price_usd"`
}

func (c *Client) GetPools(address string) (*Pools, error) {
	var pools Pools
	if err := c.get("/tokens/"+address+"/pools", &pools); err != nil {
		return nil, err
	}
	return &pools, nil
}

// StonfiPools/DedustPools ficam como `any` porque o indexer repassa o pool
// bruto de cada DEX (formato diferente entre STON.fi e DeDust) — o gateway
// só encaminha, não precisa tipar campo a campo.
type Pools struct {
	Address     string `json:"address"`
	StonfiPools []any  `json:"stonfi_pools"`
	DedustPools []any  `json:"dedust_pools"`
}

func (c *Client) GetTonPrice() (*TonPrice, error) {
	var price TonPrice
	if err := c.get("/ton-price", &price); err != nil {
		return nil, err
	}
	return &price, nil
}

type TonPrice struct {
	PriceUSD *float64 `json:"price_usd"`
	Diff24h  *string  `json:"diff_24h"`
	Diff7d   *string  `json:"diff_7d"`
	Diff30d  *string  `json:"diff_30d"`
}

type Token struct {
	Address      string   `json:"address"`
	Symbol       string   `json:"symbol"`
	Name         string   `json:"name"`
	Decimals     *int     `json:"decimals"`
	Image        *string  `json:"image"`
	Description  *string  `json:"description"`
	Mintable     *bool    `json:"mintable"`
	Verification *string  `json:"verification"`
	AdminAddress *string  `json:"admin_address"`
	TotalSupply  *float64 `json:"total_supply"`
	PriceUSD     *float64 `json:"price_usd"`
	PriceTON     *float64 `json:"price_ton"`
	LiquidityUSD *float64 `json:"liquidity_usd"`
	HoldersCount *int     `json:"holders_count"`
	MarketCapUSD *float64 `json:"market_cap_usd"`
	Change24h    *float64 `json:"change_24h"`
	Change7d     *float64 `json:"change_7d"`
	Change30d    *float64 `json:"change_30d"`
	TonscanURL   string   `json:"tonscan_url"`
}
