import { TonConnectButton, TonConnectUIProvider } from "@tonconnect/ui-react";
import { Route, Routes } from "react-router-dom";

import { TONCONNECT_MANIFEST_URL } from "./lib/tonconnect";
import { Home } from "./pages/Home";
import { Token } from "./pages/Token";

export function App() {
  return (
    <TonConnectUIProvider manifestUrl={TONCONNECT_MANIFEST_URL}>
      <div className="pt-topbar">
        <TonConnectButton />
      </div>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/token/:address" element={<Token />} />
      </Routes>
    </TonConnectUIProvider>
  );
}
