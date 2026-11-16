import { useMutation, useQuery } from "@tanstack/react-query";
import { Button, ConfirmDialog, Notice, PageHeader, SectionCard, TextAreaField } from "@nyxon/nasim";
import { useState } from "react";
import { formatNumber } from "@/shared/format";
import { fill, t } from "@/strings";
import { audienceQuery, broadcast, lowSessions } from "./api";

const m = t.messages;

export function MessagesPage() {
	const audience = useQuery(audienceQuery);
	const [text, setText] = useState("");
	const [confirm, setConfirm] = useState(false);
	const send = useMutation({ mutationFn: () => broadcast(text.trim()), onSuccess: () => { setText(""); setConfirm(false); } });
	const low = useMutation({ mutationFn: lowSessions });
	const count = formatNumber(audience.data?.count ?? 0);

	return (
		<div className="flex flex-col gap-6">
			<PageHeader title={m.title} description={m.hint} />
			<SectionCard title={m.broadcast} description={fill(m.audience, { n: count })}>
				<div className="flex flex-col gap-4">
					{send.isSuccess ? <Notice tone="success" role="status">{send.data.message}</Notice> : null}
					{send.isError ? <Notice tone="danger" role="alert">{send.error.message}</Notice> : null}
					<TextAreaField label={m.text} value={text} onChange={setText} rows={5} maxLength={3500} />
					<Button size="lg" isDisabled={!text.trim() || !audience.data?.count} onPress={() => setConfirm(true)}>{m.send}</Button>
				</div>
			</SectionCard>
			<SectionCard title={m.low} description={m.lowHint}>
				<div className="flex flex-col gap-3">
					{low.isSuccess ? <Notice tone="success" role="status">{low.data.message}</Notice> : null}
					{low.isError ? <Notice tone="danger" role="alert">{low.error.message}</Notice> : null}
					<Button variant="secondary" isPending={low.isPending} onPress={() => low.mutate()}>{m.lowGo}</Button>
				</div>
			</SectionCard>
			<ConfirmDialog isOpen={confirm} onOpenChange={setConfirm} title={fill(m.confirmTitle, { n: count })} description={m.confirmBody} confirmLabel={m.confirmGo} isPending={send.isPending} onConfirm={() => send.mutate()} />
		</div>
	);
}
