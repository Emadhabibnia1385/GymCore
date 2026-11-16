import { queryOptions } from "@tanstack/react-query";
import { ApiError, apiFetch } from "@/shared/api";

export type Brand = { name: string; title: string; wide: boolean; icon: boolean; version: number };
export type LogoKind = "wide" | "icon";

// What shows until the server answers (and if it can't): the product's own name, in English.
export const DEFAULT_BRAND: Brand = { name: "GymCore", title: "GymCore", wide: false, icon: false, version: 0 };

export const brandQuery = queryOptions({
	queryKey: ["brand"],
	queryFn: () => apiFetch<Brand>("/api/brand"),
	staleTime: 5 * 60_000,
	placeholderData: DEFAULT_BRAND,
});

export const logoUrl = (kind: LogoKind, brand: Brand) => `/api/brand/logo/${kind}?v=${brand.version}`;
export const iconUrl = (size: "192" | "180", brand: Brand) => `/api/brand/icon/${size}?v=${brand.version}`;

export const saveTexts = (body: { name: string; title: string }) =>
	apiFetch<Brand>("/api/admin/brand", { method: "PUT", body: JSON.stringify(body) });
export const removeLogo = (kind: LogoKind) => apiFetch<Brand>(`/api/admin/brand/logo/${kind}`, { method: "DELETE" });

/** The logo is a file, so multipart rather than JSON. */
export async function uploadLogo(kind: LogoKind, file: File): Promise<Brand> {
	const form = new FormData();
	form.set("file", file);
	const response = await fetch(`/api/admin/brand/logo/${kind}`, { method: "POST", body: form, credentials: "same-origin" });
	if (!response.ok) {
		const error = (await response.json().catch(() => null)) as { detail?: unknown } | null;
		throw new ApiError(response.status, typeof error?.detail === "string" ? error.detail : "مشکلی پیش آمد؛ دوباره امتحان کن.");
	}
	return (await response.json()) as Brand;
}
