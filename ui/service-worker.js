// EMA Service Worker v1
// 提供离线缓存 + 增量更新

const CACHE_NAME = "ema-v2-20260520";
const STATIC_ASSETS = [
  "/ui/index.html",
  "/ui/admin.html",
  "/ui/login.html",
  "/ui/manifest.json",
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
});

// Fetch: 网络优先 + 缓存回退
self.addEventListener("fetch", (event) => {
  // 跳过非GET请求和API调用
  if (event.request.method !== "GET") return;
  if (event.request.url.includes("/api/")) return;

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // 缓存成功的HTML/JS/CSS响应
        if (
          response.ok &&
          (event.request.url.includes("/ui/") || event.request.url.includes(".js"))
        ) {
          const cloned = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, cloned));
        }
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});
