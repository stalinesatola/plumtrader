package main

import (
	"log"
	"net/http"
	"os"

	apphttp "github.com/stalinesatola/plumtrader/services/api-gateway/internal/http"
	"github.com/stalinesatola/plumtrader/services/api-gateway/internal/indexer"
)

func getenv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func main() {
	indexerURL := getenv("INDEXER_URL", "http://localhost:8000")
	port := getenv("PORT", "8080")

	indexerClient := indexer.NewClient(indexerURL)
	router := apphttp.NewRouter(indexerClient)

	log.Printf("plumtrader api-gateway listening on :%s (indexer=%s)", port, indexerURL)
	if err := http.ListenAndServe(":"+port, router); err != nil {
		log.Fatal(err)
	}
}
