import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { BottomSheet, Button, ConfirmDialog, EmptyState, ErrorState, MultiSelect, Notice, PageHeader, PageSkeleton, SectionCard, StatusChip, TextAreaField, TextField } from "@nyxon/nasim";
import { useState } from "react";
import { studentsQuery } from "@/features/students";
import { formatNumber } from "@/shared/format";
import { fill, t } from "@/strings";
import { addTextItem, assignPackage, deleteItem, deletePackage, moveItem, packageQuery, patchItem, patchPackage, revoke, type Item } from "./api";

const p = t.plans;

export function PackagePage({ id }: { id: number }) {
	const queryClient = useQueryClient();
	const navigate = useNavigate();
	const { data, isPending, isError, refetch } = useQuery(packageQuery(id));
	const students = useQuery(studentsQuery(null, ""));
	const [itemTitle, setItemTitle] = useState("");
	const [itemText, setItemText] = useState("");
	const [editing, setEditing] = useState<Item | null>(null);
	const [picked, setPicked] = useState<string[]>([]);
	const [revokeId, setRevokeId] = useState<number | null>(null);
	const [confirmDelete, setConfirmDelete] = useState(false);
	const refresh = () => queryClient.invalidateQueries({ queryKey: ["admin"] });

	const add = useMutation({ mutationFn: () => addTextItem(id, { title: itemTitle.trim() || null, text: itemText.trim() }), onSuccess: async () => { setItemTitle(""); setItemText(""); await refresh(); } });
	const move = useMutation({ mutationFn: ({ item, direction }: { item: number; direction: -1 | 1 }) => moveItem(item, direction), onSuccess: refresh });
	const remove = useMutation({ mutationFn: (item: number) => deleteItem(item), onSuccess: refresh });
	const toggle = useMutation({ mutationFn: (active: boolean) => patchPackage(id, { active }), onSuccess: refresh });
	const assign = useMutation({ mutationFn: () => assignPackage(id, picked.map(Number)), onSuccess: async () => { setPicked([]); await refresh(); } });
	const unassign = useMutation({ mutationFn: (assignmentId: number) => revoke(assignmentId), onSuccess: async () => { setRevokeId(null); await refresh(); } });
	const destroy = useMutation({ mutationFn: () => deletePackage(id), onSuccess: async () => { await refresh(); await navigate({ to: "/plans" }); } });

	if (isPending) return <PageSkeleton />;
	if (isError) return <ErrorState as="h1" onRetry={() => void refetch()} />;
	const error = add.error ?? move.error ?? remove.error ?? toggle.error ?? assign.error ?? unassign.error ?? destroy.error;
	const already = new Set(data.recipient_list.map((r) => String(r.person_id)));
	const candidates = (students.data?.rows ?? []).filter((row) => !already.has(String(row.id)));

	return (
		<div className="flex flex-col gap-6">
			<PageHeader title={data.title} description={data.description ?? undefined} backHref="/plans" meta={data.active ? undefined : <StatusChip size="sm" tone="neutral" label={p.inactive} />} />
			{error ? <Notice tone="danger" role="alert">{error.message}</Notice> : null}

			<SectionCard title={p.itemsTitle} description={p.itemsHint}>
				<div className="flex flex-col gap-4">
					{data.item_list.length === 0 ? <EmptyState title={p.itemsNone} /> : (
						<ul className="flex flex-col gap-2">
							{data.item_list.map((item, index) => (
								<li key={item.id} className="flex flex-col gap-2 rounded-field border border-border p-3">
									<div className="flex items-center justify-between gap-2">
										<span className="font-medium">{item.title || (item.kind === "text" ? "📝" : item.kind)}</span>
										<StatusChip size="sm" tone="neutral" label={t.programs.itemKind[item.kind as keyof typeof t.programs.itemKind] ?? item.kind} />
									</div>
									{item.text ? <p className="whitespace-pre-line text-sm text-muted">{item.text}</p> : null}
									{item.kind !== "text" ? <p className="text-xs text-muted">{fill(p.fileOnBot, { where: [item.on_telegram ? p.telegram : "", item.on_bale ? p.bale : ""].filter(Boolean).join(" · ") })}</p> : null}
									<div className="flex flex-wrap gap-2">
										<Button size="sm" variant="secondary" isDisabled={index === 0} onPress={() => move.mutate({ item: item.id, direction: -1 })}>{p.up}</Button>
										<Button size="sm" variant="secondary" isDisabled={index === data.item_list.length - 1} onPress={() => move.mutate({ item: item.id, direction: 1 })}>{p.down}</Button>
										{item.kind === "text" ? <Button size="sm" variant="secondary" onPress={() => setEditing(item)}>{p.editText}</Button> : null}
										<Button size="sm" variant="danger-soft" onPress={() => remove.mutate(item.id)}>{t.common.delete}</Button>
									</div>
								</li>
							))}
						</ul>
					)}
					<TextField label={p.itemTitle} value={itemTitle} onChange={setItemTitle} maxLength={150} />
					<TextAreaField label={p.itemText} value={itemText} onChange={setItemText} rows={3} maxLength={3500} />
					<Button isDisabled={!itemText.trim()} isPending={add.isPending} onPress={() => add.mutate()}>{p.addItem}</Button>
				</div>
			</SectionCard>

			<SectionCard title={p.assign}>
				<div className="flex flex-col gap-4">
					<MultiSelect label={p.assignPick} value={picked} onChange={setPicked} options={candidates.map((row) => ({ value: String(row.id), label: row.name }))} />
					<Button isDisabled={picked.length === 0 || !data.active || data.items === 0} isPending={assign.isPending} onPress={() => assign.mutate()}>{`${p.assignGo} (${formatNumber(picked.length)})`}</Button>
					<h3 className="font-medium">{p.assignedCount}</h3>
					{data.recipient_list.length === 0 ? <p className="text-sm text-muted">{p.noRecipients}</p> : (
						<ul className="flex flex-col gap-2">
							{data.recipient_list.map((r) => (
								<li key={r.assignment_id} className="flex items-center justify-between gap-2 rounded-field border border-border p-3">
									<span>{r.name}</span>
									<Button size="sm" variant="secondary" onPress={() => setRevokeId(r.assignment_id)}>{p.revoke}</Button>
								</li>
							))}
						</ul>
					)}
				</div>
			</SectionCard>

			<div className="flex flex-wrap gap-2">
				<Button variant="secondary" isPending={toggle.isPending} onPress={() => toggle.mutate(!data.active)}>{data.active ? p.deactivate : p.activate}</Button>
				<Button variant="danger-soft" onPress={() => setConfirmDelete(true)}>{p.deletePackage}</Button>
			</div>

			<ConfirmDialog isOpen={revokeId !== null} onOpenChange={(open) => !open && setRevokeId(null)} title={p.revokeTitle} description={p.revokeBody} confirmLabel={p.revokeGo} isPending={unassign.isPending} onConfirm={() => { if (revokeId !== null) unassign.mutate(revokeId); }} />
			<ConfirmDialog isOpen={confirmDelete} onOpenChange={setConfirmDelete} tone="danger" title={p.deletePackageTitle} description={p.deletePackageBody} confirmLabel={t.manage.deleteGo} isPending={destroy.isPending} onConfirm={() => destroy.mutate()} />
			<EditItem item={editing} onClose={() => setEditing(null)} />
		</div>
	);
}

function EditItem({ item, onClose }: { item: Item | null; onClose: () => void }) {
	return (
		<BottomSheet isOpen={item !== null} onOpenChange={(open) => !open && onClose()} title={p.editText}>
			{item ? <EditForm key={item.id} item={item} onClose={onClose} /> : null}
		</BottomSheet>
	);
}

function EditForm({ item, onClose }: { item: Item; onClose: () => void }) {
	const queryClient = useQueryClient();
	const [title, setTitle] = useState(item.title ?? "");
	const [text, setText] = useState(item.text ?? "");
	const save = useMutation({ mutationFn: () => patchItem(item.id, { title, text }), onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ["admin"] }); onClose(); } });
	return (
		<div className="flex flex-col gap-4">
			{save.isError ? <Notice tone="danger" role="alert">{save.error.message}</Notice> : null}
			<TextField label={p.itemTitle} value={title} onChange={setTitle} maxLength={150} />
			<TextAreaField label={p.itemText} value={text} onChange={setText} rows={5} maxLength={3500} />
			<Button size="lg" isDisabled={!text.trim()} isPending={save.isPending} onPress={() => save.mutate()}>{t.common.save}</Button>
		</div>
	);
}
