import { tv } from "tailwind-variants";
import { iconUrl, logoUrl } from "./api";
import { useBrand } from "./useBrand";

const mark = tv({
	slots: { image: "w-auto object-contain", icon: "rounded-field object-contain", text: "font-bold text-accent", row: "flex items-center gap-2" },
	variants: {
		size: {
			menu: { image: "h-8 max-w-44", icon: "size-8", text: "text-lg" },
			hero: { image: "h-14 max-w-64", icon: "size-14", text: "text-3xl" },
		},
	},
});

/** The wide logo when there is one; else the square logo beside the name; else the name alone. */
export function BrandMark({ size = "menu" }: { size?: "menu" | "hero" }) {
	const brand = useBrand();
	const slots = mark({ size });
	if (brand.wide) return <img src={logoUrl("wide", brand)} alt={brand.name} className={slots.image()} />;
	if (brand.icon) {
		return (
			<span className={slots.row()}>
				<img src={iconUrl("192", brand)} alt="" className={slots.icon()} />
				<span className={slots.text()}>{brand.name}</span>
			</span>
		);
	}
	return <span className={slots.text()}>{brand.name}</span>;
}
