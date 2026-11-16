import { useEffect } from "react";
import { iconUrl } from "./api";
import { useBrand } from "./useBrand";

function setLink(rel: string, href: string, type?: string) {
	const link = document.querySelector<HTMLLinkElement>(`link[rel="${rel}"]`);
	if (!link) return;
	link.href = href;
	if (type) link.type = type;
}

/** Keeps the tab title and the icons in step with the brand; renders nothing. */
export function BrandHead() {
	const brand = useBrand();
	useEffect(() => {
		document.title = brand.title;
		const apple = document.querySelector<HTMLMetaElement>('meta[name="apple-mobile-web-app-title"]');
		if (apple) apple.content = brand.name;
		if (brand.icon) {
			setLink("icon", iconUrl("192", brand), "image/png");
			setLink("apple-touch-icon", iconUrl("180", brand));
		}
	}, [brand]);
	return null;
}
