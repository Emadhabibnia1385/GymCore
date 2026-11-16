import { queryOptions } from "@tanstack/react-query";
import { apiFetch } from "@/shared/api";

export type Me = { name: string; role: "admin" | "student" };
export type LoginConfig = { bot_username: string };

/** What Telegram's widget hands over; the server verifies the signature. */
export type TelegramUser = Record<string, string | number>;

export const meQuery = queryOptions({
	queryKey: ["me"],
	queryFn: () => apiFetch<Me>("/api/auth/me"),
	retry: false,
	staleTime: 5 * 60_000,
});

export const loginConfigQuery = queryOptions({
	queryKey: ["login-config"],
	queryFn: () => apiFetch<LoginConfig>("/api/auth/config"),
	staleTime: Infinity,
});

export function loginWithTelegram(user: TelegramUser): Promise<Me> {
	return apiFetch<Me>("/api/auth/telegram", { method: "POST", body: JSON.stringify(user) });
}

export function logout(): Promise<unknown> {
	return apiFetch("/api/auth/logout", { method: "POST" });
}
