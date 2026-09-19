import WebApp from "@twa-dev/sdk";

/** Inicializa o Telegram WebApp SDK e aplica o tema nativo do cliente. */
export function initTelegram(): void {
  WebApp.ready();
  WebApp.expand();

  document.documentElement.style.setProperty(
    "--tg-bg-color",
    WebApp.themeParams.bg_color ?? "#ffffff",
  );
  document.documentElement.style.setProperty(
    "--tg-text-color",
    WebApp.themeParams.text_color ?? "#000000",
  );
}

export function getInitData(): string {
  return WebApp.initData;
}

export { WebApp };
