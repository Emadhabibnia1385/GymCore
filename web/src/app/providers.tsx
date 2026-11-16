import { QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "@tanstack/react-router";
import { NasimProvider, type NasimNavigateOptions } from "@nyxon/nasim";
import { palette } from "@/theme/palette";
import { queryClient, router } from "./router";

// Defined once so React Aria doesn't rebuild every link.
function navigate(href: string, options?: NasimNavigateOptions) {
	void router.navigate({ to: href, replace: options?.replace });
}

export function AppProviders() {
	return (
		<QueryClientProvider client={queryClient}>
			<NasimProvider navigate={navigate} palette={palette} defaultMode="dark">
				<RouterProvider router={router} />
			</NasimProvider>
		</QueryClientProvider>
	);
}
