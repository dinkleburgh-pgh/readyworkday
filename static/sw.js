const CACHE_NAME = "truckapp-pwa-v2";
const STATIC_ROOT = new URL(".", self.location.href).pathname.replace(/\/$/, "");
const OFFLINE_URL = `${STATIC_ROOT}/offline.html`;
const APP_SHELL_URLS = [
  OFFLINE_URL,
  `${STATIC_ROOT}/manifest.webmanifest`,
  `${STATIC_ROOT}/icons/truckapp-icon-180.png`,
  `${STATIC_ROOT}/icons/truckapp-icon-192.png`,
  `${STATIC_ROOT}/icons/truckapp-icon-512.png`,
  `${STATIC_ROOT}/icons/truckapp-icon.svg`,
];

if (STATIC_ROOT === "/static") {
  APP_SHELL_URLS.unshift("/");
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(APP_SHELL_URLS))
      .catch(() => Promise.resolve())
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key !== CACHE_NAME)
            .map((key) => caches.delete(key))
        )
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") {
    return;
  }

  const requestUrl = new URL(event.request.url);
  if (requestUrl.origin !== self.location.origin) {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (!response || response.status !== 200 || response.type !== "basic") {
          return response;
        }
        const responseCopy = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, responseCopy));
        return response;
      })
      .catch(async () => {
        const cached = await caches.match(event.request);
        if (cached) {
          return cached;
        }
        return caches.match(OFFLINE_URL);
      })
  );
});
