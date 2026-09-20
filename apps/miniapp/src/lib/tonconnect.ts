/**
 * Configuração do TonConnect: o PlumTrader nunca guarda chaves privadas.
 * O usuário conecta a própria wallet (Tonkeeper, MyTonWallet etc.) e assina
 * cada transação nela; aqui só montamos o payload a ser assinado.
 */
export const TONCONNECT_MANIFEST_URL = `${window.location.origin}/tonconnect-manifest.json`;
