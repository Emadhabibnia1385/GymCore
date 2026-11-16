import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@/index.css";
import { registerWorker, watchInstallPrompt } from "@/features/pwa";
import { AppProviders } from "./app/providers";

watchInstallPrompt();

// After an update the files a long-open tab remembers are gone: reload once to get the new ones.
window.addEventListener("vite:preloadError", (event) => {
	event.preventDefault();
	try {
		if (sessionStorage.getItem("gc-reloaded")) return;
		sessionStorage.setItem("gc-reloaded", "1");
	} catch {
		/* storage blocked: reload anyway */
	}
	window.location.reload();
});

const root = document.getElementById("root");
if (!root) throw new Error("index.html has no #root");
createRoot(root).render(
	<StrictMode>
		<AppProviders />
	</StrictMode>,
);
registerWorker();
