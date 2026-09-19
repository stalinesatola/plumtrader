/**
 * Configuração do TonConnect: o PlumTrader nunca guarda chaves privadas.
 * O usuário conecta a própria wallet (Tonkeeper, MyTonWallet etc.) e assina
 * cada transação nela; aqui só montamos o payload a ser assinado.
 */
export const TONCONNECT_MANIFEST_URL = `${window.location.origin}/tonconnect-manifest.json`;

export interface SwapRequest {
  fromAddress: string;
  toJetton: string;
  amountNano: string;
  validUntil: number;
}

/** Monta o payload de transação TON para o TonConnect assinar (não assina). */
export function buildSwapTransaction(req: SwapRequest) {
  return {
    validUntil: req.validUntil,
    messages: [
      {
        address: req.toJetton,
        amount: req.amountNano,
      },
    ],
  };
}
