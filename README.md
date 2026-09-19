# PlumTrader

Telegram Mini App para acompanhar e operar memecoins/jettons na rede **TON**,
usando TonAPI, Toncenter, STON.fi/DeDust e deep-links do **Tonscan**. O app é
**não-custodial**: toda transação é assinada pela wallet do usuário via
[TonConnect](https://docs.ton.org/develop/dapps/ton-connect/overview) — o
PlumTrader nunca guarda chaves privadas.

Veja a arquitetura completa em [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Estrutura

```
apps/
  miniapp/        # TypeScript + React + Vite — Telegram Mini App
  bot/             # Go — bot do Telegram
services/
  api-gateway/     # Go — API REST consumida pela Mini App
  indexer/          # Python + FastAPI — agrega dados da TON
deploy/
  docker-compose.yml
docs/
  ARCHITECTURE.md
```

## Rodando localmente

1. Copie `.env.example` para `.env` e preencha `TELEGRAM_BOT_TOKEN` (crie um
   bot com o [@BotFather](https://t.me/BotFather)) e, opcionalmente,
   `TONAPI_KEY`.

2. Suba a infra com Docker:

   ```bash
   cd deploy
   docker compose up --build
   ```

   Isso sobe `postgres`, `redis`, `indexer` (porta 8000), `api-gateway`
   (porta 8080) e o `bot`.

3. Rode a Mini App em modo dev:

   ```bash
   cd apps/miniapp
   npm install
   npm run dev
   ```

## Configurando no Telegram

1. No [@BotFather](https://t.me/BotFather), use `/setmenubutton` no seu bot e
   aponte para a URL pública onde a Mini App está hospedada (precisa ser
   HTTPS — em produção, ou via túnel como `ngrok`/`cloudflared` em dev).
2. Atualize `MINIAPP_URL` no `.env` com essa mesma URL — é o que o comando
   `/start` do bot usa no botão "Abrir PlumTrader".
3. Ajuste `apps/miniapp/public/tonconnect-manifest.json` com a URL final e
   ícone do app (o TonConnect exige um manifest publicamente acessível).

## Desenvolvimento por serviço

| Serviço | Comando | Porta |
|---|---|---|
| `services/indexer` | `pip install -r requirements.txt && uvicorn app.main:app --reload` | 8000 |
| `services/api-gateway` | `go run ./cmd/api-gateway` | 8080 |
| `apps/bot` | `go run ./cmd/bot` | - |
| `apps/miniapp` | `npm run dev` | 5173 |

## Status

MVP arquitetural: integrações reais com APIs públicas da TON, fluxo de swap
não-custodial via TonConnect, sem execução automática de ordens (veja
"Fora de escopo" em `docs/ARCHITECTURE.md`).
