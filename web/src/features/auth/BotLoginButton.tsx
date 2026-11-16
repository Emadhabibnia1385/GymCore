import { useMutation, useQuery } from "@tanstack/react-query";
import { Button, Notice } from "@nyxon/nasim";
import { type ReactNode, useEffect, useRef, useState } from "react";
import { t } from "@/strings";
import { pollBotLogin, startBotLogin, type BotLogin, type Me } from "./api";

const l = t.login;

/** «Log in with the bot»: open the bot, approve there, and this page signs in by itself. */
export function BotLoginButton({ onDone, aside }: { onDone: (me: Me) => void; aside?: ReactNode }) {
	const [request, setRequest] = useState<BotLogin | null>(null);
	const start = useMutation({
		mutationFn: startBotLogin,
		onSuccess: (made) => {
			setRequest(made);
			// A phone opens Telegram straight away; where a popup is blocked the link below does it.
			window.open(made.url, "_blank", "noopener");
		},
	});
	const answer = useQuery({
		queryKey: ["bot-login", request?.secret],
		enabled: request !== null,
		queryFn: () => pollBotLogin(request!.secret),
		refetchInterval: (query) => (query.state.data?.state === "pending" || !query.state.data ? 2000 : false),
		retry: false,
		gcTime: 0,
	});

	const state = answer.data?.state;
	const signedIn = useRef(false);
	useEffect(() => {
		// The server hands the session out once; guard against a second delivery.
		if (state === "approved" && answer.data?.me && !signedIn.current) {
			signedIn.current = true;
			onDone(answer.data.me);
		}
	}, [state, answer.data, onDone]);

	if (request && (state === undefined || state === "pending")) {
		return (
			<div className="flex flex-col gap-3">
				<Notice tone="info" role="status">{l.botWaiting}</Notice>
				<a href={request.url} target="_blank" rel="noopener" className="text-center text-accent underline">{l.openBot}</a>
				<Button variant="secondary" onPress={() => setRequest(null)}>{l.botCancel}</Button>
			</div>
		);
	}
	return (
		<div className="flex flex-col gap-3">
			{state === "denied" ? <Notice tone="danger" role="alert">{l.botDenied}</Notice> : null}
			{state === "expired" ? <Notice tone="warning" role="alert">{l.botExpired}</Notice> : null}
			{start.isError ? <Notice tone="danger" role="alert">{start.error.message}</Notice> : null}
			<div className="flex gap-2">
				<Button size="lg" className="min-w-0 flex-1" isPending={start.isPending} onPress={() => { signedIn.current = false; start.mutate(); }}>{l.botLogin}</Button>
				{aside}
			</div>
			<p className="text-center text-sm text-muted">{l.botHint}</p>
		</div>
	);
}
