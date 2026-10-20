// Tipagem do @env (react-native-dotenv), que lê o .env na hora do build.
//
// GNEWS_API_KEY saiu daqui junto com a chamada direta ao GNews. Qualquer
// valor declarado neste arquivo é EMBUTIDO no aplicativo publicado, então
// ele serve para configuração, nunca para segredo: quem instalar o APK
// consegue ler.
//
// Chave de serviço pago mora em variável de ambiente do SERVIDOR — no caso
// do GNews, no painel do Render, lida pelo noticias_api.py.

declare module '@env' {
  // Vazio de propósito. Se algum dia precisar de algo aqui, que seja
  // configuração pública: uma URL de ambiente, um sinalizador de recurso.
  const _nada: never;
  export { _nada };
}
