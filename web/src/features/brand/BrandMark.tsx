import { tv } from "tailwind-variants";
import { logoUrl } from "./api";
import { useBrand } from "./useBrand";

const mark = tv({
	slots: { image: "w-auto object-contain", text: "font-bold text-accent" },
	variants: {
		size: {
			menu: { image: "h-8 max-w-44", text: "text-lg" },
			hero: { image: "h-14 max-w-64", text: "text-3xl" },
		},
	},
});

/** The wide logo when there is one, else the site's name — the same mark everywhere it appears. */
export function BrandMark({ size = "menu" }: { size?: "menu" | "hero" }) {
	const brand = useBrand();
	const slots = mark({ size });
	return brand.wide ? <img src={logoUrl("wide", brand)} alt={brand.name} className={slots.image()} /> : <span className={slots.text()}>{brand.name}</span>;
}
