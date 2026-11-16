import { queryOptions } from "@tanstack/react-query";
import { apiFetch } from "@/shared/api";

export type Me = { name: string; role: "admin" | "student"; username: string | null; avatar: number | null };
export type LoginConfig = { bot_username: string; dev_login: boolean; registration_open: boolean };
export type Done = { ok: boolean; message: string };

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
	staleTime: 60_000,
});

const post = <T>(path: string, body?: unknown) =>
	apiFetch<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

export const loginWithTelegram = (user: TelegramUser) => post<Me>("/api/auth/telegram", user);
export const loginWithPassword = (body: { username: string; password: string }) => post<Me>("/api/auth/password", body);
export const register = (body: { name: string; username: string; password: string }) => post<Me>("/api/auth/register", body);
export const loginDev = (student = false) => post<Me>(`/api/auth/dev?student=${student}`);
export const setPassword = (body: { username: string; password: string }) => post<Me>("/api/auth/password/set", body);
export const changePassword = (body: { old_password: string; new_password: string }) => post<Done>("/api/auth/password/change", body);
export const logout = () => post<unknown>("/api/auth/logout");

export type BotLogin = { url: string; secret: string; expires_in: number };
export type BotLoginState = { state: "pending" | "approved" | "denied" | "expired"; me: Me | null };
export const startBotLogin = () => post<BotLogin>("/api/auth/bot-login");
export const pollBotLogin = (secret: string) => post<BotLoginState>("/api/auth/bot-login/status", { secret });

export type TelegramLink = { url: string; expires_in: number };
export const telegramLinkQuery = queryOptions({
	queryKey: ["telegram-link"],
	queryFn: () => apiFetch<{ linked: boolean }>("/api/auth/telegram-link"),
	staleTime: 0,
});
export const startTelegramLink = () => post<TelegramLink>("/api/auth/telegram-link");
