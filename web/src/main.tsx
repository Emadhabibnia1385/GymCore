import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@/index.css";
import { registerWorker, watchInstallPrompt } from "@/features/pwa";
import { AppProviders } from "./app/providers";

watchInstallPrompt();

const root = document.getElementById("root");
if (!root) throw new Error("index.html has no #root");
createRoot(root).render(
	<StrictMode>
		<AppProviders />
	</StrictMode>,
);
registerWorker();
