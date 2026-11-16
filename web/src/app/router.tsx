import { QueryClient } from "@tanstack/react-query";
import { ApiError } from "@/shared/api";
import { createRouter } from "@tanstack/react-router";
import { routeTree } from "@/routeTree.gen";

// A 4xx is the server's real answer; anything else (a network blip, a 502 while the server restarts for an
// update) is worth a few patient tries before an error is shown.
const transient = (error: unknown) => !(error instanceof ApiError) || error.status >= 500;

export const queryClient = new QueryClient({
	defaultOptions: {
		queries: {
			staleTime: 30_000,
			refetchOnWindowFocus: false,
			retry: (attempt, error) => transient(error) && attempt < 4,
			retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 8000),
		},
	},
});

export const router = createRouter({
	routeTree,
	context: { queryClient },
	defaultPreload: "intent",
	scrollRestoration: true,
});

declare module "@tanstack/react-router" {
	interface Register {
		router: typeof router;
	}
}
