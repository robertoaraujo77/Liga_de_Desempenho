self.addEventListener('install', (e) => {
    self.skipWaiting(); // Força a atualização imediata
});

self.addEventListener('activate', (e) => {
    return self.clients.claim(); // Assume o controle da página
});

self.addEventListener('fetch', (e) => {
    // Responde às requisições corretamente para o Chrome validar o PWA
    e.respondWith(fetch(e.request).catch(() => new Response("PWA Offline")));
});
