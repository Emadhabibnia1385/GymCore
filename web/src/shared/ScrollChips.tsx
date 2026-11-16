import { FilterChips } from "@nyxon/nasim";
import { type ComponentProps, useEffect, useRef } from "react";

/**
 * Filter chips that stay on ONE row on a phone and scroll sideways, the chosen one kept in view;
 * from `sm` up they wrap like the plain chips do. (Nasim's own chips always wrap, which on a
 * phone stacked seven filters into three rows.)
 */
export function ScrollChips({ inset = "page", ...props }: ComponentProps<typeof FilterChips> & { inset?: "page" | "card" }) {
	const box = useRef<HTMLDivElement>(null);
	useEffect(() => {
		const chosen = box.current?.querySelector<HTMLElement>('[aria-checked="true"], [data-selected="true"], [aria-pressed="true"]');
		chosen?.scrollIntoView({ inline: "center", block: "nearest" });
	}, [props.value]);
	return (
		<div
			ref={box}
			className={`${inset === "card" ? "-mx-3 px-3" : "-mx-4 px-4"} overflow-x-auto pb-1 [scrollbar-width:none] sm:mx-0 sm:overflow-visible sm:px-0 [&::-webkit-scrollbar]:hidden [&>*]:!flex-nowrap sm:[&>*]:!flex-wrap [&_button]:shrink-0 [&_button]:whitespace-nowrap`}
		>
			<FilterChips {...props} />
		</div>
	);
}
