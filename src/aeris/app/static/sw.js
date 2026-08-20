const CACHE = "aeris-field-v1";
const FILES = ["/", "/static/styles.css", "/static/app.js", "/static/manifest.json"];
self.addEventListener("install", event => event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(FILES))));
self.addEventListener("fetch", event => {
  if (event.request.method === "GET") event.respondWith(fetch(event.request).catch(() => caches.match(event.request)));
});
