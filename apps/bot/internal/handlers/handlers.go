// Package handlers implements the PlumTrader Telegram bot's commands.
package handlers

import (
	tele "gopkg.in/telebot.v3"
)

// Deps carries what handlers need to talk to the api-gateway and to build
// the Mini App launch button.
type Deps struct {
	MiniAppURL string
	APIBaseURL string
}

func (d Deps) HandleStart(c tele.Context) error {
	menu := &tele.ReplyMarkup{}
	openApp := menu.WebApp("🚀 Abrir PlumTrader", &tele.WebApp{URL: d.MiniAppURL})
	menu.Inline(menu.Row(openApp))

	return c.Send(
		"👋 Bem-vindo ao PlumTrader!\n\n"+
			"Acompanhe memecoins da rede TON e opere via TonConnect, "+
			"direto do Telegram. Toque no botão abaixo para abrir o app.",
		menu,
	)
}

func (d Deps) HandleHelp(c tele.Context) error {
	return c.Send(
		"/start - abrir o PlumTrader\n" +
			"/price <endereço_jetton> - ver preço e link do Tonscan\n" +
			"/watch <endereço_jetton> - adicionar à watchlist (em breve)",
	)
}

func (d Deps) HandlePrice(c tele.Context) error {
	address := c.Message().Payload
	if address == "" {
		return c.Send("Uso: /price <endereço_do_jetton>")
	}

	// A busca real de preço é feita via api-gateway -> indexer (TonAPI/DEXs).
	// Aqui devolvemos o link do Tonscan como referência imediata.
	return c.Send("🔎 Consultando " + address + "...\nVerifique também em: https://tonscan.org/jetton/" + address)
}
