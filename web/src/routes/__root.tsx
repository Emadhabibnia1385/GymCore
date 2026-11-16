import type { QueryClient } from "@tanstack/react-query";
import { createRootRouteWithContext, Outlet } from "@tanstack/react-router";
import { EmptyState } from "@nyxon/nasim";
import { t } from "@/strings";

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
	component: Outlet,
	notFoundComponent: () => (
		<div className="p-6">
			<EmptyState as="h1" title={t.errors.notFoundTitle} description={t.errors.notFoundHint} action={{ label: t.errors.backHome, href: "/" }} />
		</div>
	),
});
