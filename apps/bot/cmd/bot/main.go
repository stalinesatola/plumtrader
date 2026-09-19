package main

import (
	"log"
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

	log.Printf("plumtrader bot authorized as @%s", bot.Me.Username)
	bot.Start()
}
