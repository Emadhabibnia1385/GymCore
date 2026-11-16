import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { BottomSheet, Button, ConfirmDialog, Notice, SelectField, TextAreaField, TextField } from "@nyxon/nasim";
import { useState } from "react";
import { DatePick, isoDay } from "@/shared/DatePick";
import { t } from "@/strings";
import { convertLead, createLead, deleteLead, leadOptionsQuery, patchLead, type Lead } from "./api";

const f = t.follow;

/** A new lead (null id) or an existing one: change its status, add a note, schedule a call, make it a student. */
export function LeadSheet({ lead, isNew, onClose }: { lead: Lead | null; isNew: boolean; onClose: () => void }) {
	const open = isNew || lead !== null;
	return (
		<BottomSheet isOpen={open} onOpenChange={(value) => !value && onClose()} title={isNew ? f.addLead : (lead?.name ?? "")}>
			{open ? (isNew ? <NewLead onClose={onClose} /> : lead ? <Existing key={lead.id} lead={lead} onClose={onClose} /> : null) : null}
		</BottomSheet>
	);
}

function NewLead({ onClose }: { onClose: () => void }) {
	const queryClient = useQueryClient();
	const options = useQuery(leadOptionsQuery);
	const [name, setName] = useState("");
	const [phone, setPhone] = useState("");
	const [source, setSource] = useState<string | null>("OTHER");
	const [interest, setInterest] = useState("");
	const save = useMutation({
		mutationFn: () => createLead({ name: name.trim(), phone: phone.trim() || null, source: source ?? "OTHER", interest: interest.trim() || null }),
		onSuccess: async () => {
			await queryClient.invalidateQueries({ queryKey: ["admin"] });
			onClose();
		},
	});
	return (
		<div className="flex flex-col gap-4">
			{save.isError ? <Notice tone="danger" role="alert">{save.error.message}</Notice> : null}
			<TextField label={f.leadName} value={name} onChange={setName} maxLength={150} isRequired />
			<TextField label={f.leadPhone} value={phone} onChange={setPhone} dir="ltr" inputMode="tel" />
			<SelectField label={f.leadSource} value={source} onChange={setSource} options={options.data?.sources ?? []} />
			<TextField label={f.leadInterest} value={interest} onChange={setInterest} maxLength={200} />
			<Button size="lg" isDisabled={!name.trim()} isPending={save.isPending} onPress={() => save.mutate()}>{t.common.save}</Button>
		</div>
	);
}

function Existing({ lead, onClose }: { lead: Lead; onClose: () => void }) {
	const queryClient = useQueryClient();
	const navigate = useNavigate();
	const options = useQuery(leadOptionsQuery);
	const [status, setStatus] = useState<string | null>(lead.status);
	const [note, setNote] = useState("");
	const [next, setNext] = useState("");
	const [kind, setKind] = useState<string | null>("IN_PERSON");
	const [confirm, setConfirm] = useState(false);
	const refresh = () => queryClient.invalidateQueries({ queryKey: ["admin"] });
	const save = useMutation({
		mutationFn: () => patchLead(lead.id, { status: status ?? undefined, note: note.trim() || undefined, follow_up_on: next || undefined }),
		onSuccess: async () => {
			await refresh();
			onClose();
		},
	});
	const convert = useMutation({
		mutationFn: () => convertLead(lead.id, kind ?? "IN_PERSON"),
		onSuccess: async (done) => {
			await refresh();
			onClose();
			await navigate({ to: "/students/$id", params: { id: String(done.person_id) } });
		},
	});
	const remove = useMutation({ mutationFn: () => deleteLead(lead.id), onSuccess: async () => { await refresh(); setConfirm(false); onClose(); } });
	const error = save.error ?? convert.error ?? remove.error;

	return (
		<div className="flex flex-col gap-4">
			<p className="text-sm text-muted">{[lead.phone, lead.source_label, lead.interest].filter(Boolean).join(" · ")}</p>
			{lead.note ? <p className="whitespace-pre-line rounded-field border border-border p-3 text-sm">{lead.note}</p> : null}
			{error ? <Notice tone="danger" role="alert">{error.message}</Notice> : null}
			<SelectField label={f.leadStatus} value={status} onChange={setStatus} options={options.data?.statuses ?? []} />
			<TextAreaField label={f.leadNote} value={note} onChange={setNote} rows={2} maxLength={500} />
			<DatePick label={f.leadNext} value={next || isoDay(1)} onChange={setNext} />
			<Button size="lg" isPending={save.isPending} onPress={() => save.mutate()}>{t.common.save}</Button>

			{lead.person_id ? null : (
				<div className="flex flex-col gap-3 border-t border-separator pt-4">
					{lead.existing_student ? <Notice tone="info">{f.existing}</Notice> : null}
					<SelectField label={f.convertKind} value={kind} onChange={setKind} options={[{ value: "IN_PERSON", label: t.manage.inPerson }, { value: "ONLINE", label: t.manage.online }]} />
					<Button variant="secondary" isPending={convert.isPending} onPress={() => convert.mutate()}>{f.convert}</Button>
				</div>
			)}
			<Button variant="danger-soft" onPress={() => setConfirm(true)}>{f.deleteLead}</Button>
			<ConfirmDialog isOpen={confirm} onOpenChange={setConfirm} tone="danger" title={f.deleteLeadTitle} description={f.deleteLeadBody} confirmLabel={t.manage.deleteGo} isPending={remove.isPending} onConfirm={() => remove.mutate()} />
		</div>
	);
}
