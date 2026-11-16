import { useEffect, useRef, useState } from "react";
import { LoadingState, Notice } from "@nyxon/nasim";
import { t } from "@/strings";
import type { TelegramUser } from "./api";

type Props = { botUsername: string; onAuth: (user: TelegramUser) => void };

declare global {
	interface Window {
		onGymcoreTelegramAuth?: (user: TelegramUser) => void;
	}
}

/** Telegram's own «Login with Telegram» widget, mounted in a box we own. */
export function TelegramLoginButton({ botUsername, onAuth }: Props) {
	const box = useRef<HTMLDivElement>(null);
	const [failed, setFailed] = useState(false);
	const [ready, setReady] = useState(false);

	useEffect(() => {
		const host = box.current;
		if (!host) return;
		window.onGymcoreTelegramAuth = onAuth;
		const script = document.createElement("script");
		script.src = "https://telegram.org/js/telegram-widget.js?22";
		script.async = true;
		script.dataset.telegramLogin = botUsername;
		script.dataset.size = "large";
		script.dataset.radius = "12";
		script.dataset.requestAccess = "write";
		script.dataset.onauth = "onGymcoreTelegramAuth(user)";
		script.onload = () => setReady(true);
		script.onerror = () => setFailed(true);
		host.append(script);
		return () => {
			delete window.onGymcoreTelegramAuth;
			host.replaceChildren();
		};
	}, [botUsername, onAuth]);

	return (
		<div className="flex min-h-14 flex-col items-center gap-3">
			{failed ? <Notice tone="danger">{t.login.widgetFailed}</Notice> : null}
			{!ready && !failed ? <LoadingState label={t.login.loading} /> : null}
			<div ref={box} dir="ltr" className="flex justify-center" />
		</div>
	);
}
