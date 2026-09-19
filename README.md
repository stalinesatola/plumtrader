# PlumTrader

Telegram Mini App para acompanhar e operar memecoins/jettons na rede **TON**,
usando TonAPI, Toncenter, STON.fi/DeDust e deep-links do **Tonscan**. O app é
**não-custodial**: toda transação é assinada pela wallet do usuário via
[TonConnect](https://docs.ton.org/develop/dapps/ton-connect/overview) — o
PlumTrader nunca guarda chaves privadas.

Veja a arquitetura completa em [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Link de teste (preview)

Bot oficial de teste, já configurado no BotFather com o Mini App:
👉 https://t.me/plum_app_bot/plumtrader

Mini App em deploy de teste:
👉 https://plumtrader-app.vercel.app

O link do `t.me` acima é a forma recomendada de testar — abre o Mini App
dentro do próprio Telegram, com o SDK do WebApp funcionando por completo
(tema nativo, botões, `initData`). O link do Vercel serve para testar só
o front-end no navegador: fora do Telegram o SDK roda em modo de
compatibilidade e a tela de conexão TonConnect funciona normalmente.

O backend (api-gateway + indexer) também está publicado como demo na
Vercel (`plumtrader-gateway.vercel.app` e `plumtrader-indexer.vercel.app`),
mas lá roda **sem Postgres real** — cada serverless function é sem
estado, então `/tokens` sempre responde lista vazia e o `APScheduler` do
indexer não persiste entre chamadas. Para rodar com banco e watchlist de
verdade, use o Blueprint do Render (próxima seção) ou o
`deploy/docker-compose.yml` local.

## Deploy com banco de verdade (Render)

Este repo tem um [`render.yaml`](render.yaml) (Render Blueprint) com
Postgres + os 3 serviços (`indexer`, `api-gateway`, `bot` como Background
Worker). Diferente da demo na Vercel, aqui o Postgres é real e o
`APScheduler` do indexer roda continuamente.

1. No dashboard do Render, **New → Blueprint** e aponte para este
   repositório (`stalinesatola/plumtrader`).
2. O Render vai pedir os valores dos env vars marcados `sync: false`:
   `TELEGRAM_BOT_TOKEN` (do @BotFather), e opcionalmente `TONAPI_KEY` /
   `TONCENTER_API_KEY`.
3. `render.yaml` assume que o `plumtrader-gateway` e o `plumtrader-indexer`
   ficam em `https://<nome-do-serviço>.onrender.com` — se o Render sufixar
   o nome (porque já está em uso), ajuste `INDEXER_URL` no serviço
   `plumtrader-gateway` manualmente no dashboard após o primeiro deploy.
4. Atualize `VITE_API_BASE_URL` do projeto do miniapp (na Vercel ou onde
   estiver hospedado) para a URL do `plumtrader-gateway` no Render.

O plano `free` do Postgres do Render expira depois de um tempo — bom para
testar, não para produção.

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
