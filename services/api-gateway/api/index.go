// Package handler is the entrypoint Vercel's Go runtime expects: one
// exported Handler function per file under /api. It wraps the same chi
// router used by cmd/api-gateway so both the Docker deployment and the
// Vercel deployment share one implementation.
package handler

import (
	"net/http"
	"os"

	apphttp "github.com/stalinesatola/plumtrader/services/api-gateway/internal/http"
	"github.com/stalinesatola/plumtrader/services/api-gateway/internal/indexer"
)

var router http.Handler

func init() {
	indexerURL := os.Getenv("INDEXER_URL")
	if indexerURL == "" {
		indexerURL = "http://localhost:8000"
	}
	router = apphttp.NewRouter(indexer.NewClient(indexerURL))
}

func Handler(w http.ResponseWriter, r *http.Request) {
	router.ServeHTTP(w, r)
}
