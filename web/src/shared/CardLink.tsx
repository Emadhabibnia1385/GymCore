import { Link, type LinkProps } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { tv } from "tailwind-variants";

const card = tv({
	base: "flex items-center justify-between gap-3 rounded-field border border-border bg-surface p-4 outline-none transition-colors hover:bg-surface-secondary focus-visible:ring-2 focus-visible:ring-accent",
});

/** A whole row that is one link — the shape a phone wants for «open this». */
export function CardLink({ children, ...link }: LinkProps & { children: ReactNode }) {
	return (
		<Link {...link} className={card()}>
			{children}
		</Link>
	);
}
