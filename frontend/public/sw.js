/* Self-destructing service worker used to clear old NoobTrade caches. */

self.addEventListener('install', (event) => {
  self.skipWaiting()
  event.waitUntil(Promise.resolve())
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys()
      await Promise.all(keys.filter((key) => key.startsWith('noobtrade-')).map((key) => caches.delete(key)))
      await self.clients.claim()
      await self.registration.unregister()
    })()
  )
})

self.addEventListener('fetch', () => {
  // Intentionally empty: this worker exists only to unregister itself and clear stale caches.
})
