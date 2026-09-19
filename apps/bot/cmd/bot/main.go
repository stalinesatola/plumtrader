package main

import (
	"log"
	"net/http"
	"os"
	"time"

	tele "gopkg.in/telebot.v3"

	"github.com/stalinesatola/plumtrader/apps/bot/internal/handlers"
)

func getenv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func main() {
	token := os.Getenv("TELEGRAM_BOT_TOKEN")
	if token == "" {
		log.Fatal("TELEGRAM_BOT_TOKEN is required")
	}

	deps := handlers.Deps{
		MiniAppURL: getenv("MINIAPP_URL", "https://example.com"),
		APIBaseURL: getenv("API_GATEWAY_URL", "http://localhost:8080"),
	}

	bot, err := tele.NewBot(tele.Settings{
		Token:  token,
		Poller: &tele.LongPoller{Timeout: 60 * time.Second},
	})
	if err != nil {
		log.Fatalf("failed to start bot: %v", err)
	}

	bot.Handle("/start", deps.HandleStart)
	bot.Handle("/help", deps.HandleHelp)
	bot.Handle("/price", deps.HandlePrice)

	// O bot funciona por long-polling, sem precisar de porta HTTP. Mas
	// plataformas como o Render (no plano free) só rodam serviços do tipo
	// "Web Service", que exigem responder em $PORT — então expomos um
	// health-check mínimo só para satisfazer esse requisito de infra.
	go func() {
		port := getenv("PORT", "8081")
		http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
			w.WriteHeader(http.StatusOK)
			_, _ = w.Write([]byte("plumtrader bot is running"))
		})
		log.Printf("health-check server listening on :%s", port)
		if err := http.ListenAndServe(":"+port, nil); err != nil {
			log.Printf("health-check server error: %v", err)
		}
	}()

	log.Printf("plumtrader bot authorized as @%s", bot.Me.Username)
	bot.Start()
}
