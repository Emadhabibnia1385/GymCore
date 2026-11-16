import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, EmptyState, Notice, SectionCard, TextAreaField } from "@nyxon/nasim";
import { useState } from "react";
import { addNote, FollowUpSheet, notesQuery, type FollowUpTarget } from "@/features/followups";
import { t } from "@/strings";

const f = t.follow;

/** The notes timeline of a student (append-only) and a shortcut to schedule a follow-up. */
export function NotesCard({ id, name }: { id: number; name: string }) {
	const queryClient = useQueryClient();
	const notes = useQuery(notesQuery(id));
	const [text, setText] = useState("");
	const [target, setTarget] = useState<FollowUpTarget | null>(null);
	const add = useMutation({
		mutationFn: () => addNote(id, text.trim()),
		onSuccess: async () => {
			setText("");
			await queryClient.invalidateQueries({ queryKey: ["admin"] });
		},
	});
	return (
		<SectionCard title={f.notes} description={f.notesHint} actions={<Button size="sm" variant="secondary" onPress={() => setTarget({ name, personId: id })}>{f.followUp}</Button>}>
			<div className="flex flex-col gap-4">
				<TextAreaField label={f.noteText} value={text} onChange={setText} rows={2} maxLength={1000} />
				{add.isError ? <Notice tone="danger" role="alert">{add.error.message}</Notice> : null}
				<Button isDisabled={!text.trim()} isPending={add.isPending} onPress={() => add.mutate()}>{f.noteAdd}</Button>
				{notes.data && notes.data.length > 0 ? (
					<ul className="flex flex-col gap-2">
						{notes.data.map((note) => (
							<li key={note.id} className="rounded-field border border-border p-3">
								<p className="whitespace-pre-line text-sm">{note.text}</p>
								<p className="mt-1 text-xs text-muted">{note.date}</p>
							</li>
						))}
					</ul>
				) : (
					<EmptyState title={f.notesNone} />
				)}
			</div>
			<FollowUpSheet target={target} onClose={() => setTarget(null)} />
		</SectionCard>
	);
}
