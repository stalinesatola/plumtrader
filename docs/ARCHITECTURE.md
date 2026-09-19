# Arquitetura do PlumTrader

## Visão geral

O PlumTrader é um Telegram Mini App para acompanhar e operar memecoins/jettons
na rede TON. É **não-custodial**: o backend nunca guarda chave privada nem
assina transações — quem assina é sempre a wallet do usuário, conectada via
[TonConnect](https://docs.ton.org/develop/dapps/ton-connect/overview).

## Componentes

```
Telegram Client
   │
   ├── Bot (apps/bot, Go)
   │     comandos /start /help /price, botão "Abrir PlumTrader" (web_app)
   │
   └── Mini App (apps/miniapp, TS/React)
         Telegram WebApp SDK + TonConnect UI
         │
         ▼
   api-gateway (services/api-gateway, Go)
         REST: /api/tokens, /api/tokens/{address}, /api/tokens/{address}/tonscan
         │
         ▼
   indexer (services/indexer, Python/FastAPI)
         agrega TonAPI.io, Toncenter, STON.fi, DeDust
         cache em Postgres, agendamento com APScheduler
```

## Por que essa divisão de linguagens

- **Go** no `api-gateway` e no `bot`: concorrência simples, baixa latência,
  binários pequenos — bom para servir a Mini App e responder ao Telegram
  rapidamente.
- **Python** no `indexer`: ecossistema maduro para integração com APIs
  externas, parsing e futura análise de dados (ex.: detecção de rug-pulls,
  scoring de risco de tokens).
- **TypeScript/React** na Mini App: é a linguagem "nativa" do Telegram Web
  Apps (roda dentro do `telegram-web-app.js`) e do TonConnect UI.

## Fontes de dados TON

| Fonte | Uso |
|---|---|
| TonAPI.io | Metadados de jettons, holders, transações |
| Toncenter | RPC de fallback / consulta direta à blockchain |
| STON.fi / DeDust | Preços, pools de liquidez, rotas de swap |
| Tonscan | Deep-links de verificação (`/jetton/<addr>`, `/tx/<hash>`) — não usado para dados em massa, só para o usuário conferir por conta própria |

## Fluxo de "swap" (não-custodial)

1. Usuário abre o token na Mini App.
2. Conecta a wallet via `TonConnectButton`.
3. A Mini App monta o payload da transação (`buildSwapTransaction`).
4. O `tonConnectUI.sendTransaction(tx)` pede para a wallet do usuário assinar
   e enviar — o PlumTrader nunca vê a chave privada nem assina nada.

## Fora de escopo (próximos passos)

- Execução automática de ordens com custódia de chaves (exigiria HSM/KMS e
  controles de compliance muito mais rígidos).
- Deploy em produção — hoje só há `deploy/docker-compose.yml` para rodar
  localmente.
- Scoring de risco / detecção de rug-pull no `indexer` (estrutura pronta para
  receber isso em `app/tasks`).
