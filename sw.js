/* Service worker de l'application installable.

   Objectif : que le simulateur s'ouvre aussi hors connexion, sans jamais
   servir une version périmée quand on est en ligne.

   - Page (navigation) : réseau d'abord, copie locale en secours. En ligne, on
     a donc toujours la dernière version poussée ; hors ligne, la dernière vue.
   - Fichiers du site et polices Google : copie locale d'abord, rafraîchie en
     arrière-plan.
   - Tout le reste (dont le compteur de connexions) n'est pas intercepté.

   Changer VERSION seulement si la liste PRECACHE change. */
const VERSION = 'retraites-v1';
const PRECACHE = ['/', '/manifest.webmanifest', '/icons/icon-192.png',
                  '/icons/icon-512.png', '/icons/apple-touch-icon.png'];
const POLICES = ['https://fonts.googleapis.com', 'https://fonts.gstatic.com'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(cles => Promise.all(cles.filter(k => k !== VERSION).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  if (req.mode === 'navigate' && url.origin === location.origin) {
    e.respondWith(fetch(req).then(rep => {
      if (rep.ok && url.pathname === '/') {
        const copie = rep.clone();
        caches.open(VERSION).then(c => c.put('/', copie));
      }
      return rep;
    }).catch(() => caches.match('/')));
    return;
  }

  if (url.origin === location.origin || POLICES.includes(url.origin)) {
    e.respondWith(caches.open(VERSION).then(c => c.match(req).then(enCache => {
      const reseau = fetch(req).then(rep => {
        if (rep.ok || rep.type === 'opaque') c.put(req, rep.clone());
        return rep;
      }).catch(() => enCache);
      return enCache || reseau;
    })));
  }
});
