import { useSyncExternalStore } from "react";

type InstallEvent = Event & { prompt: () => Promise<void> };

let deferred: InstallEvent | null = null;
const listeners = new Set<() => void>();
const emit = () => listeners.forEach((listener) => listener());

// The browser offers its install prompt once, possibly before any screen is open.
export function watchInstallPrompt(): void {
	window.addEventListener("beforeinstallprompt", (event) => {
		event.preventDefault();
		deferred = event as InstallEvent;
		emit();
	});
	window.addEventListener("appinstalled", () => {
		deferred = null;
		emit();
	});
}

/** The install action while the browser offers one; null when installed or unsupported. */
export function useInstall(): (() => Promise<void>) | null {
	const offered = useSyncExternalStore(
		(listener) => {
			listeners.add(listener);
			return () => listeners.delete(listener);
		},
		() => deferred,
	);
	return offered ? () => offered.prompt() : null;
}

export function registerWorker(): void {
	if (import.meta.env.PROD && "serviceWorker" in navigator) {
		window.addEventListener("load", () => void navigator.serviceWorker.register("/sw.js"));
	}
}
