// Package httpapi wires the REST API that the PlumTrader Mini App and bot
// consume, backed by the Python indexer service.
package httpapi

import (
	"encoding/json"
	"net/http"
	"strconv"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/go-chi/cors"

	"github.com/stalinesatola/plumtrader/services/api-gateway/pkg/indexerclient"
	"github.com/stalinesatola/plumtrader/services/api-gateway/pkg/tonscan"
)

const defaultPageLimit = 20
const defaultHistoryDays = 30

func parseIntParam(r *http.Request, name string, fallback int) int {
	raw := r.URL.Query().Get(name)
	if raw == "" {
		return fallback
	}
	v, err := strconv.Atoi(raw)
	if err != nil || v < 0 {
		return fallback
	}
	return v
}

func NewRouter(indexerClient *indexerclient.Client) http.Handler {
	r := chi.NewRouter()
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)
	r.Use(cors.Handler(cors.Options{
		// A Mini App roda em domínio próprio (Vercel) diferente do
		// api-gateway; sem CORS liberado o navegador bloqueia o fetch.
		AllowedOrigins: []string{"*"},
		AllowedMethods: []string{"GET"},
	}))

	r.Get("/health", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	})

	r.Get("/api/ton-price", func(w http.ResponseWriter, r *http.Request) {
		price, err := indexerClient.GetTonPrice()
		if err != nil {
			writeJSON(w, http.StatusBadGateway, map[string]string{"error": err.Error()})
			return
		}
		writeJSON(w, http.StatusOK, price)
	})

	r.Route("/api/tokens", func(r chi.Router) {
		r.Get("/", func(w http.ResponseWriter, r *http.Request) {
			limit := parseIntParam(r, "limit", defaultPageLimit)
			offset := parseIntParam(r, "offset", 0)
			q := r.URL.Query().Get("q")
			sort := r.URL.Query().Get("sort")

			page, err := indexerClient.ListTokens(limit, offset, q, sort)
			if err != nil {
				writeJSON(w, http.StatusBadGateway, map[string]string{"error": err.Error()})
				return
			}
			writeJSON(w, http.StatusOK, page)
		})

		r.Get("/{address}", func(w http.ResponseWriter, r *http.Request) {
			address := chi.URLParam(r, "address")
			token, err := indexerClient.GetToken(address)
			if err != nil {
				writeJSON(w, http.StatusNotFound, map[string]string{"error": err.Error()})
				return
			}
			writeJSON(w, http.StatusOK, token)
		})

		r.Get("/{address}/tonscan", func(w http.ResponseWriter, r *http.Request) {
			address := chi.URLParam(r, "address")
			writeJSON(w, http.StatusOK, map[string]string{"url": tonscan.JettonURL(address)})
		})

		r.Get("/{address}/price-history", func(w http.ResponseWriter, r *http.Request) {
			address := chi.URLParam(r, "address")
			days := parseIntParam(r, "days", defaultHistoryDays)

			points, err := indexerClient.GetPriceHistory(address, days)
			if err != nil {
				writeJSON(w, http.StatusBadGateway, map[string]string{"error": err.Error()})
				return
			}
			writeJSON(w, http.StatusOK, points)
		})
	})

	return r
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}
