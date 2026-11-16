import { queryOptions } from "@tanstack/react-query";
import { apiFetch } from "@/shared/api";
import type { PackageSummary, Program } from "@/features/students/api";

export type PackageItem = { id: number; title: string; kind: string; text: string | null; on_telegram: boolean };
export type PackageDetail = PackageSummary & { item_list: PackageItem[] };
export type Done = { ok: boolean; message: string };

export const myProgramsQuery = queryOptions({ queryKey: ["me", "programs"], queryFn: () => apiFetch<Program[]>("/api/me/programs") });
export const myPackagesQuery = queryOptions({ queryKey: ["me", "packages"], queryFn: () => apiFetch<PackageSummary[]>("/api/me/packages") });
export const packageQuery = (id: number) =>
	queryOptions({ queryKey: ["me", "package", id], queryFn: () => apiFetch<PackageDetail>(`/api/me/packages/${id}`) });

export const sendProgram = (id: number) => apiFetch<Done>(`/api/me/programs/${id}/send`, { method: "POST" });
export const sendPackageItem = (packageId: number, itemId: number) =>
	apiFetch<Done>(`/api/me/packages/${packageId}/items/${itemId}/send`, { method: "POST" });
