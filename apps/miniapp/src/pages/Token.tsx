import { TonConnectButton, useTonConnectUI } from "@tonconnect/ui-react";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { getToken, type Token as TokenData } from "../lib/api";
import { buildSwapTransaction } from "../lib/tonconnect";

export function Token() {
  const { address = "" } = useParams();
  const [token, setToken] = useState<TokenData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tonConnectUI] = useTonConnectUI();

  useEffect(() => {
    getToken(address)
      .then(setToken)
      .catch((err: Error) => setError(err.message));
  }, [address]);

  async function handleSwap() {
    if (!token) return;

    // O PlumTrader nunca assina por conta própria: monta a transação e pede
    // para a wallet conectada (via TonConnect) assinar e enviar.
    const tx = buildSwapTransaction({
      fromAddress: tonConnectUI.account?.address ?? "",
      toJetton: token.address,
      amountNano: "50000000", // 0.05 TON de exemplo
      validUntil: Math.floor(Date.now() / 1000) + 300,
    });

    await tonConnectUI.sendTransaction(tx);
  }

  if (error) return <p role="alert">Erro: {error}</p>;
  if (!token) return <p>Carregando...</p>;

  return (
    <main>
      <h1>
        {token.symbol} — {token.name}
      </h1>
      {token.price_usd != null && <p>Preço: ${token.price_usd.toFixed(6)}</p>}
      <p>
        <a href={token.tonscan_url} target="_blank" rel="noreferrer">
          Ver no Tonscan
        </a>
      </p>

      <TonConnectButton />
      <button onClick={handleSwap} disabled={!tonConnectUI.connected}>
        Comprar via wallet conectada
      </button>
    </main>
  );
}
