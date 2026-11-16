// Keeps the app's own files so the panel opens fast and offline; user data is never cached.
const VERSION = "gymcore-v1";
const STATIC = ["/assets/", "/fonts/", "/icons/"];

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", (event) => {
	event.waitUntil(
		caches
			.keys()
			.then((keys) => Promise.all(keys.filter((key) => key !== VERSION).map((key) => caches.delete(key))))
			.then(() => self.clients.claim()),
	);
});

self.addEventListener("fetch", (event) => {
	const { request } = event;
	const url = new URL(request.url);
	// The API carries the person's data and session: always the network, never a copy.
	if (request.method !== "GET" || url.origin !== location.origin || url.pathname.startsWith("/api/")) return;

	if (STATIC.some((prefix) => url.pathname.startsWith(prefix))) {
		// Hashed, immutable files: the copy on disk is always right.
		event.respondWith(
			caches.match(request).then(
				(hit) =>
					hit ||
					fetch(request).then((response) => {
						const copy = response.clone();
						if (response.ok) caches.open(VERSION).then((cache) => cache.put(request, copy));
						return response;
					}),
			),
		);
	} else if (request.mode === "navigate") {
		// The app shell: fresh when online, the last one when not.
		event.respondWith(
			fetch(request)
				.then((response) => {
					const copy = response.clone();
					if (response.ok) caches.open(VERSION).then((cache) => cache.put("/", copy));
					return response;
				})
				.catch(() => caches.match("/")),
		);
	}
});
