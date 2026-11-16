import { queryOptions } from "@tanstack/react-query";
import { ApiError, apiFetch } from "@/shared/api";

export type ProgramType = { id: number; title: string; active: boolean };
export type PackageRow = { id: number; title: string; active: boolean; items: number; recipients: number };
export type Item = { id: number; title: string | null; kind: string; text: string | null; on_telegram: boolean; on_bale: boolean };
export type Recipient = { assignment_id: number; person_id: number; name: string };
export type PackageDetail = PackageRow & { description: string | null; item_list: Item[]; recipient_list: Recipient[]; ever_assigned: boolean };
export type Saved = { ok: boolean; message: string };
export type Created = { id: number; message: string };

export const typesQuery = queryOptions({ queryKey: ["admin", "program-types"], queryFn: () => apiFetch<ProgramType[]>("/api/admin/program-types") });
export const packagesQuery = queryOptions({ queryKey: ["admin", "packages"], queryFn: () => apiFetch<PackageRow[]>("/api/admin/packages") });
export const packageQuery = (id: number) => queryOptions({ queryKey: ["admin", "package", id], queryFn: () => apiFetch<PackageDetail>(`/api/admin/packages/${id}`) });

const send = <T>(method: string, path: string, body?: unknown) => apiFetch<T>(path, { method, body: body === undefined ? undefined : JSON.stringify(body) });
export const createType = (title: string) => send<Created>("POST", "/api/admin/program-types", { title });
export const patchType = (id: number, body: { title?: string; active?: boolean }) => send<Saved>("PATCH", `/api/admin/program-types/${id}`, body);
export const deleteType = (id: number) => send<Saved>("DELETE", `/api/admin/program-types/${id}`);
export const createPackage = (body: { title: string; description: string | null }) => send<Created>("POST", "/api/admin/packages", body);
export const patchPackage = (id: number, body: { title?: string; description?: string; active?: boolean }) => send<PackageDetail>("PATCH", `/api/admin/packages/${id}`, body);
export const deletePackage = (id: number) => send<Saved>("DELETE", `/api/admin/packages/${id}`);
export const addTextItem = (id: number, body: { title: string | null; text: string }) => send<PackageDetail>("POST", `/api/admin/packages/${id}/items`, body);
export const patchItem = (id: number, body: { title?: string; text?: string }) => send<PackageDetail>("PATCH", `/api/admin/package-items/${id}`, body);
export const moveItem = (id: number, direction: -1 | 1) => send<PackageDetail>("POST", `/api/admin/package-items/${id}/move`, { direction });
export const deleteItem = (id: number) => send<PackageDetail>("DELETE", `/api/admin/package-items/${id}`);
export const assignPackage = (id: number, personIds: number[]) => send<{ count: number; message: string }>("POST", `/api/admin/packages/${id}/assign`, { person_ids: personIds });
export const revoke = (assignmentId: number) => send<Saved>("POST", `/api/admin/package-assignments/${assignmentId}/revoke`);

/** A program for one student is a form with an optional file, so it is multipart, not JSON. */
export async function sendProgram(body: { personId: number; typeId: number; note: string; file: File | null }): Promise<Created> {
	const form = new FormData();
	form.set("person_id", String(body.personId));
	form.set("plan_type_id", String(body.typeId));
	form.set("note", body.note);
	if (body.file) form.set("file", body.file);
	const response = await fetch("/api/admin/programs", { method: "POST", body: form, credentials: "same-origin" });
	if (!response.ok) {
		const error = (await response.json().catch(() => null)) as { detail?: unknown } | null;
		throw new ApiError(response.status, typeof error?.detail === "string" ? error.detail : "مشکلی پیش آمد؛ دوباره امتحان کن.");
	}
	return (await response.json()) as Created;
}
