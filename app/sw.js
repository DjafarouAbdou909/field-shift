// Fonctionnement hors connexion. L'interface est servie depuis le cache. Les
// recommandations sont demandées au réseau quand il est disponible, sinon au cache.
const CACHE = "conseil-rotation-v5";
const FICHIERS = ["./", "index.html", "style.css", "app.js", "icone.svg", "manifest.webmanifest",
                  "donnees/recommandations.json"];

// Les enregistrements vocaux listés dans les recommandations sont aussi mis en cache.
async function installer() {
  const cache = await caches.open(CACHE);
  await cache.addAll(FICHIERS);
  const donnees = await (await cache.match("donnees/recommandations.json")).json();
  const audios = Object.values(donnees.lieux).flatMap((l) => Object.values(l.resultats))
    .map((r) => r.audio).filter(Boolean);
  await cache.addAll(audios);
}

self.addEventListener("install", (e) => {
  e.waitUntil(installer().then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys()
    .then((cles) => Promise.all(cles.filter((c) => c !== CACHE).map((c) => caches.delete(c))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (url.pathname.endsWith("donnees/recommandations.json")) {
    e.respondWith(fetch(e.request)
      .then((r) => { const copie = r.clone(); caches.open(CACHE).then((c) => c.put(e.request, copie)); return r; })
      .catch(() => caches.match(e.request)));
    return;
  }
  e.respondWith(caches.match(e.request).then((r) => r || fetch(e.request)));
});
