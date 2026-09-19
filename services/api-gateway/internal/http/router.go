// Package http wires the REST API that the PlumTrader Mini App and bot
// consume, backed by the Python indexer service.
package http

import (
	"encoding/json"
	"net/http"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"

	"github.com/stalinesatola/plumtrader/services/api-gateway/internal/indexer"
	"github.com/stalinesatola/plumtrader/services/api-gateway/internal/tonscan"
)

func NewRouter(indexerClient *indexer.Client) http.Handler {
	r := chi.NewRouter()
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)

	r.Get("/health", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	})

	r.Route("/api/tokens", func(r chi.Router) {
		r.Get("/", func(w http.ResponseWriter, r *http.Request) {
			tokens, err := indexerClient.ListTokens()
			if err != nil {
				writeJSON(w, http.StatusBadGateway, map[string]string{"error": err.Error()})
				return
			}
			writeJSON(w, http.StatusOK, tokens)
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
	})

	return r
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}
