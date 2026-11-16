import babel from "@rolldown/plugin-babel";
import tailwindcss from "@tailwindcss/vite";
import { tanstackRouter } from "@tanstack/router-plugin/vite";
import react, { reactCompilerPreset } from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";
import Icons from "unplugin-icons/vite";
import { defineConfig } from "vite";

// In development the browser stays same-origin: /api goes to the local GymCore API.
const api = process.env.VITE_DEV_API_TARGET ?? "http://127.0.0.1:8815";

export default defineConfig({
	// The router plugin must come before the React plugin (TanStack Router docs).
	plugins: [
		tanstackRouter({ target: "react", autoCodeSplitting: true }),
		react(),
		babel({ presets: [reactCompilerPreset()] }),
		tailwindcss(),
		// Solar icons as tree-shaken, offline SVG components (~icons/solar/*).
		Icons({ compiler: "jsx", jsx: "react", autoInstall: false }),
	],
	resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
	server: { proxy: { "/api": { target: api, changeOrigin: true } } },
});
