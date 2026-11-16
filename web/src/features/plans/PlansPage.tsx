import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { BottomSheet, Button, ConfirmDialog, EmptyState, ErrorState, Notice, PageHeader, PageSkeleton, SectionCard, SelectField, StatusChip, TextAreaField, TextField } from "@nyxon/nasim";
import { ScrollChips } from "@/shared/ScrollChips";
import { useState } from "react";
import { studentsQuery } from "@/features/students";
import { CardLink } from "@/shared/CardLink";
import { FilePick } from "@/shared/FilePick";
import { formatNumber } from "@/shared/format";
import { fill, t } from "@/strings";
import { createPackage, createType, deleteType, packagesQuery, patchType, sendProgram, typesQuery, type ProgramType } from "./api";

const p = t.plans;
type Tab = "send" | "packages" | "types";

export function PlansPage() {
	const [tab, setTab] = useState<Tab>("send");
	return (
		<div className="flex flex-col gap-4">
			<PageHeader title={p.title} description={p.hint} />
			<ScrollChips label={p.title} value={tab} onChange={(value) => setTab(value as Tab)} options={[{ value: "send", label: p.tabSend }, { value: "packages", label: p.tabPackages }, { value: "types", label: p.tabTypes }]} />
			{tab === "send" ? <SendProgram /> : tab === "packages" ? <Packages /> : <Types />}
		</div>
	);
}

function SendProgram() {
	const queryClient = useQueryClient();
	const students = useQuery(studentsQuery(null, ""));
	const types = useQuery(typesQuery);
	const [person, setPerson] = useState<string | null>(null);
	const [kind, setKind] = useState<string | null>(null);
	const [note, setNote] = useState("");
	const [file, setFile] = useState<File | null>(null);
	const send = useMutation({
		mutationFn: () => sendProgram({ personId: Number(person), typeId: Number(kind), note, file }),
		onSuccess: async () => {
			setNote("");
			setFile(null);
			await queryClient.invalidateQueries({ queryKey: ["admin"] });
		},
	});
	return (
		<SectionCard title={p.tabSend} description={p.sendHint}>
			<div className="flex flex-col gap-4">
				{send.isSuccess ? <Notice tone="success" role="status">{p.sent}</Notice> : null}
				{send.isError ? <Notice tone="danger" role="alert">{send.error.message}</Notice> : null}
				<SelectField label={p.student} value={person} onChange={setPerson} options={(students.data?.rows ?? []).map((row) => ({ value: String(row.id), label: row.name }))} />
				<SelectField label={p.type} value={kind} onChange={setKind} options={(types.data ?? []).filter((x) => x.active).map((x) => ({ value: String(x.id), label: x.title }))} />
				<TextAreaField label={p.note} value={note} onChange={setNote} rows={4} maxLength={3500} />
				<FilePick label={p.file} file={file} onChange={setFile} />
				<Button size="lg" isDisabled={!person || !kind || (!note.trim() && !file)} isPending={send.isPending} onPress={() => send.mutate()}>{p.send}</Button>
			</div>
		</SectionCard>
	);
}

function Packages() {
	const navigate = useNavigate();
	const queryClient = useQueryClient();
	const { data, isPending, isError, refetch } = useQuery(packagesQuery);
	const [open, setOpen] = useState(false);
	const [title, setTitle] = useState("");
	const [description, setDescription] = useState("");
	const add = useMutation({
		mutationFn: () => createPackage({ title: title.trim(), description: description.trim() || null }),
		onSuccess: async (made) => {
			await queryClient.invalidateQueries({ queryKey: ["admin"] });
			setOpen(false);
			setTitle("");
			setDescription("");
			await navigate({ to: "/plans/package/$id", params: { id: String(made.id) } });
		},
	});
	return (
		<>
			<Button size="sm" onPress={() => setOpen(true)}>{p.addPackage}</Button>
			{isPending ? <PageSkeleton /> : isError ? <ErrorState onRetry={() => void refetch()} /> : data.length === 0 ? <EmptyState title={p.packagesNone} /> : (
				<ul className="flex flex-col gap-2">
					{data.map((row) => (
						<li key={row.id}>
							<CardLink to="/plans/package/$id" params={{ id: String(row.id) }}>
								<span className="flex flex-col">
									<span className="font-medium">📦 {row.title}</span>
									<span className="text-xs text-muted">{fill(p.items, { n: formatNumber(row.items) })} · {fill(p.recipients, { n: formatNumber(row.recipients) })}</span>
								</span>
								{row.active ? null : <StatusChip size="sm" tone="neutral" label={p.inactive} />}
							</CardLink>
						</li>
					))}
				</ul>
			)}
			<BottomSheet isOpen={open} onOpenChange={setOpen} title={p.addPackage}>
				<div className="flex flex-col gap-4">
					{add.isError ? <Notice tone="danger" role="alert">{add.error.message}</Notice> : null}
					<TextField label={p.packageTitle} value={title} onChange={setTitle} maxLength={150} isRequired />
					<TextAreaField label={p.packageDescription} value={description} onChange={setDescription} rows={3} maxLength={1500} />
					<Button size="lg" isDisabled={!title.trim()} isPending={add.isPending} onPress={() => add.mutate()}>{t.common.save}</Button>
				</div>
			</BottomSheet>
		</>
	);
}

function Types() {
	const queryClient = useQueryClient();
	const { data, isPending, isError, refetch } = useQuery(typesQuery);
	const [title, setTitle] = useState("");
	const [renaming, setRenaming] = useState<{ id: number; title: string } | null>(null);
	const [removing, setRemoving] = useState<ProgramType | null>(null);
	const refresh = () => queryClient.invalidateQueries({ queryKey: ["admin", "program-types"] });
	const add = useMutation({ mutationFn: () => createType(title.trim()), onSuccess: async () => { setTitle(""); await refresh(); } });
	const rename = useMutation({ mutationFn: () => patchType(renaming!.id, { title: renaming!.title.trim() }), onSuccess: async () => { setRenaming(null); await refresh(); } });
	const toggle = useMutation({ mutationFn: (row: ProgramType) => patchType(row.id, { active: !row.active }), onSuccess: refresh });
	const remove = useMutation({ mutationFn: (row: ProgramType) => deleteType(row.id), onSuccess: async () => { setRemoving(null); await refresh(); } });
	if (isPending) return <PageSkeleton />;
	if (isError) return <ErrorState onRetry={() => void refetch()} />;
	const error = add.error ?? rename.error ?? toggle.error ?? remove.error;
	return (
		<div className="flex flex-col gap-4">
			{error ? <Notice tone="danger" role="alert">{error.message}</Notice> : null}
			<div className="flex items-end gap-2">
				<div className="flex-1"><TextField label={p.typeName} value={title} onChange={setTitle} maxLength={150} /></div>
				<Button isDisabled={!title.trim()} isPending={add.isPending} onPress={() => add.mutate()}>{p.addType}</Button>
			</div>
			{data.length === 0 ? <EmptyState title={p.typeNone} /> : (
				<ul className="flex flex-col gap-2">
					{data.map((row) => (
						<li key={row.id} className="flex flex-wrap items-center justify-between gap-2 rounded-field border border-border bg-surface p-4">
							{renaming?.id === row.id ? (
								<div className="flex w-full items-end gap-2">
									<div className="flex-1"><TextField label={p.typeName} value={renaming.title} onChange={(value) => setRenaming({ id: row.id, title: value })} maxLength={150} /></div>
									<Button isDisabled={!renaming.title.trim()} isPending={rename.isPending} onPress={() => rename.mutate()}>{t.common.save}</Button>
									<Button variant="secondary" onPress={() => setRenaming(null)}>{t.common.cancel}</Button>
								</div>
							) : (
								<>
									<span className={row.active ? "font-medium" : "font-medium text-muted"}>{row.title}</span>
									<div className="flex gap-2">
										<Button size="sm" variant="secondary" isPending={toggle.isPending && toggle.variables?.id === row.id} onPress={() => toggle.mutate(row)}>{row.active ? t.manage.classActive : t.manage.classInactive}</Button>
										<Button size="sm" variant="secondary" onPress={() => setRenaming({ id: row.id, title: row.title })}>{t.common.edit}</Button>
										<Button size="sm" variant="danger-soft" onPress={() => setRemoving(row)}>{t.common.delete}</Button>
									</div>
								</>
							)}
						</li>
					))}
				</ul>
			)}
			<ConfirmDialog isOpen={removing !== null} onOpenChange={(open) => !open && setRemoving(null)} tone="danger" title={p.deleteTypeTitle} description={p.deleteTypeBody} confirmLabel={t.manage.deleteGo} isPending={remove.isPending} onConfirm={() => { if (removing) remove.mutate(removing); }} />
		</div>
	);
}
