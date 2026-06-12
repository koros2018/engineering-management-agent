// EMA Service Worker v1
// 提供离线缓存 + 增量更新

const CACHE_NAME = "ema-v4-20260612";
const STATIC_ASSETS = [
  "/index.html",
  "/admin.html",
  "/login.html",
  "/manifest.json",
];

// Install: 预缓存核心页面
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS).catch(() => {}))
  );
  self.skipWaiting();
});

// Activate: 清理旧缓存
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
  // 注销旧SW
  self.registration.unregister();
});

// Fetch: 网络优先 + 缓存回退
self.addEventListener("fetch", (event) => {
  // 跳过非GET请求和API调用
  if (event.request.method !== "GET") return;
  if (event.request.url.includes("/api/")) return;

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // 只缓存静态资源，不缓存 admin.html（避免旧缓存导致JS错误）
        if (
          response.ok &&
          event.request.url.includes(".js") &&
          !event.request.url.includes("vue")
        ) {
          const cloned = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, cloned));
        }
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});
