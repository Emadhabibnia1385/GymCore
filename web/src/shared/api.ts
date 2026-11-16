import { t } from "@/strings";

export class ApiError extends Error {
	readonly status: number;
	constructor(status: number, message: string) {
		super(message);
		this.status = status;
	}
}

/** The one way to call the API; the session rides in an httpOnly cookie. */
export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
	const response = await fetch(path, {
		credentials: "same-origin",
		...init,
		headers: { "Content-Type": "application/json", ...init?.headers },
	});
	if (!response.ok) {
		const body = (await response.json().catch(() => null)) as { detail?: unknown } | null;
		throw new ApiError(response.status, typeof body?.detail === "string" ? body.detail : t.errors.generic);
	}
	return (await response.json()) as T;
}
