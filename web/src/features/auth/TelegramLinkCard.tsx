import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, Notice, SectionCard } from "@nyxon/nasim";
import { useEffect, useState } from "react";
import { t } from "@/strings";
import { meQuery, startTelegramLink, telegramLinkQuery, type TelegramLink } from "./api";

const k = t.account.telegram;

/** Connect Telegram to a password account: open the bot, approve there, and this card notices. */
export function TelegramLinkCard() {
	const queryClient = useQueryClient();
	const [request, setRequest] = useState<TelegramLink | null>(null);
	const state = useQuery({
		...telegramLinkQuery,
		// While waiting for the approval in Telegram, look again every couple of seconds.
		refetchInterval: (query) => (request && !query.state.data?.linked ? 2000 : false),
	});
	const start = useMutation({
		mutationFn: startTelegramLink,
		onSuccess: (made) => {
			setRequest(made);
			window.open(made.url, "_blank", "noopener");
		},
	});

	const linked = state.data?.linked ?? false;
	// Joining can hand this browser to the Telegram person, so what «me» says may change.
	useEffect(() => {
		if (linked && request) void queryClient.invalidateQueries({ queryKey: meQuery.queryKey });
	}, [linked, request, queryClient]);

	return (
		<SectionCard title={k.title} description={linked ? undefined : k.hint}>
			{linked ? (
				<Notice tone="success" role="status">{k.linked}</Notice>
			) : (
				<div className="flex flex-col gap-3">
					{start.isError ? <Notice tone="danger" role="alert">{start.error.message}</Notice> : null}
					{request ? (
						<Notice tone="info" role="status">
							{k.waiting}{" "}
							<a className="underline" href={request.url} target="_blank" rel="noopener noreferrer">{k.open}</a>
						</Notice>
					) : null}
					<Button isPending={start.isPending} onPress={() => start.mutate()}>{request ? k.again : k.connect}</Button>
				</div>
			)}
		</SectionCard>
	);
}
