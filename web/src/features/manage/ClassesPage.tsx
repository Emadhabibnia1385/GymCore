import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, ConfirmDialog, EmptyState, ErrorState, Notice, PageHeader, PageSkeleton, SectionCard, TextField } from "@nyxon/nasim";
import { useState } from "react";
import { t } from "@/strings";
import { classesQuery, createClass, deleteClass, updateClass, type ClassType } from "./api";

const g = t.manage;

export function ClassesPage() {
	const queryClient = useQueryClient();
	const { data, isPending, isError, refetch } = useQuery(classesQuery);
	const [title, setTitle] = useState("");
	const [editing, setEditing] = useState<{ id: number; title: string } | null>(null);
	const [removing, setRemoving] = useState<ClassType | null>(null);
	const refresh = () => queryClient.invalidateQueries({ queryKey: ["admin", "classes"] });
	const add = useMutation({ mutationFn: () => createClass(title.trim()), onSuccess: async () => { setTitle(""); await refresh(); } });
	const rename = useMutation({ mutationFn: () => updateClass(editing!.id, { title: editing!.title.trim() }), onSuccess: async () => { setEditing(null); await refresh(); } });
	const toggle = useMutation({ mutationFn: (row: ClassType) => updateClass(row.id, { active: !row.active }), onSuccess: refresh });
	const remove = useMutation({ mutationFn: (row: ClassType) => deleteClass(row.id), onSuccess: async () => { setRemoving(null); await refresh(); } });

	if (isPending) return <PageSkeleton />;
	if (isError) return <ErrorState as="h1" onRetry={() => void refetch()} />;
	const error = add.error ?? rename.error ?? toggle.error ?? remove.error;

	return (
		<div className="flex flex-col gap-6">
			<PageHeader title={g.classes} description={g.classesHint} />
			{error ? <Notice tone="danger" role="alert">{error.message}</Notice> : null}
			<SectionCard title={g.addClass}>
				<div className="flex items-end gap-2">
					<div className="flex-1">
						<TextField label={g.className} value={title} onChange={setTitle} maxLength={150} />
					</div>
					<Button isDisabled={!title.trim()} isPending={add.isPending} onPress={() => add.mutate()}>{t.common.save}</Button>
				</div>
			</SectionCard>
			{data.length === 0 ? (
				<EmptyState title={g.classNone} />
			) : (
				<ul className="flex flex-col gap-2">
					{data.map((row) => (
						<li key={row.id} className="flex flex-col gap-3 rounded-field border border-border bg-surface p-4">
							{editing?.id === row.id ? (
								<div className="flex items-end gap-2">
									<div className="flex-1"><TextField label={g.className} value={editing.title} onChange={(value) => setEditing({ id: row.id, title: value })} maxLength={150} /></div>
									<Button isDisabled={!editing.title.trim()} isPending={rename.isPending} onPress={() => rename.mutate()}>{t.common.save}</Button>
									<Button variant="secondary" onPress={() => setEditing(null)}>{t.common.cancel}</Button>
								</div>
							) : (
								<div className="flex flex-wrap items-center justify-between gap-2">
									<span className={row.active ? "font-medium" : "font-medium text-muted"}>{row.title}</span>
									<div className="flex gap-2">
										<Button size="sm" variant="secondary" isPending={toggle.isPending && toggle.variables?.id === row.id} onPress={() => toggle.mutate(row)}>{row.active ? g.classActive : g.classInactive}</Button>
										<Button size="sm" variant="secondary" onPress={() => setEditing({ id: row.id, title: row.title })}>{t.common.edit}</Button>
										<Button size="sm" variant="danger-soft" onPress={() => setRemoving(row)}>{t.common.delete}</Button>
									</div>
								</div>
							)}
						</li>
					))}
				</ul>
			)}
			<ConfirmDialog isOpen={removing !== null} onOpenChange={(open) => !open && setRemoving(null)} tone="danger" title={g.deleteClassTitle} description={g.deleteClassBody} confirmLabel={g.deleteGo} isPending={remove.isPending} onConfirm={() => { if (removing) remove.mutate(removing); }} />
		</div>
	);
}
