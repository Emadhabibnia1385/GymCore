import { Link } from "@tanstack/react-router";
import { useBottomBar } from "@nyxon/nasim";
import { tv } from "tailwind-variants";
import type { Me } from "@/features/auth";
import { t } from "@/strings";
import { navFor } from "./nav";

const tab = tv({
	slots: {
		bar: "fixed inset-x-0 bottom-0 z-30 border-t border-separator bg-surface px-safe pb-(--nasim-safe-bottom) lg:hidden",
		list: "mx-auto flex max-w-xl items-stretch justify-around gap-1 px-2",
		link: "flex min-h-14 flex-1 flex-col items-center justify-center gap-1 rounded-field px-2 text-xs text-muted",
		current: "text-accent",
	},
});

// The phone's main menu, at the bottom within thumb reach and clear of the home indicator.
export function PhoneTabBar({ role }: { role: Me["role"] }) {
	const bar = useBottomBar<HTMLElement>();
	const slots = tab();
	return (
		<nav ref={bar} aria-label={t.nav.label} className={slots.bar()}>
			<ul className={slots.list()}>
				{navFor(role).map(({ to, label, Icon }) => (
					<li key={to} className="flex flex-1">
						<Link to={to} activeOptions={{ exact: to === "/" }} className={slots.link()} activeProps={{ className: slots.current(), "aria-current": "page" }}>
							<Icon className="size-6" aria-hidden />
							<span>{label}</span>
						</Link>
					</li>
				))}
			</ul>
		</nav>
	);
}
