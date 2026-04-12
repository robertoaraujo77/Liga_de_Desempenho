// O navegador exige um Service Worker para exibir o banner de instalação
self.addEventListener('install', (e) => {
  console.log('[Service Worker] Instalado com sucesso.');
});

self.addEventListener('fetch', (e) => {
  // Deixa a requisição passar normalmente (necessário para o PWA)
});
