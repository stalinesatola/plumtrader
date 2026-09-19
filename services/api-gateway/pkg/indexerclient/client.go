// Package indexerclient contains the HTTP client the api-gateway uses to
// talk to the Python indexer service, which aggregates data from TonAPI,
// STON.fi and DeDust.
package indexerclient

import (
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

type Client struct {
	baseURL string
	http    *http.Client
}

func NewClient(baseURL string) *Client {
	return &Client{
		baseURL: baseURL,
		http:    &http.Client{Timeout: 10 * time.Second},
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

func (c *Client) ListTokens(limit, offset int) (*TokenPage, error) {
	var page TokenPage
	path := fmt.Sprintf("/tokens?limit=%d&offset=%d", limit, offset)
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

type Token struct {
	Address      string   `json:"address"`
	Symbol       string   `json:"symbol"`
	Name         string   `json:"name"`
	Image        *string  `json:"image"`
	PriceUSD     *float64 `json:"price_usd"`
	PriceTON     *float64 `json:"price_ton"`
	LiquidityUSD *float64 `json:"liquidity_usd"`
	HoldersCount *int     `json:"holders_count"`
	TonscanURL   string   `json:"tonscan_url"`
}
