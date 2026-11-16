import { useMutation } from "@tanstack/react-query";
import { Button, ConfirmDialog, Notice } from "@nyxon/nasim";
import { useRef, useState } from "react";
import { ApiError, apiFetch } from "@/shared/api";
import { PersonAvatar } from "@/shared/PersonAvatar";
import { t } from "@/strings";

const k = t.avatar;

async function upload(base: string, file: File): Promise<{ version: number }> {
	const form = new FormData();
	form.set("file", file);
	const response = await fetch(base, { method: "POST", body: form, credentials: "same-origin" });
	if (!response.ok) {
		const body = (await response.json().catch(() => null)) as { detail?: unknown } | null;
		throw new ApiError(response.status, typeof body?.detail === "string" ? body.detail : t.errors.generic);
	}
	return (await response.json()) as { version: number };
}

/** A photo and the two things to do with it. It uploads the moment a file is chosen — no second button. */
export function AvatarEditor({ base, version, id, name, onChange }: { base: string; version: number; id: number; name: string; onChange: () => void }) {
	const input = useRef<HTMLInputElement>(null);
	const [confirm, setConfirm] = useState(false);
	const send = useMutation({ mutationFn: (file: File) => upload(base, file), onSuccess: onChange });
	const remove = useMutation({
		mutationFn: () => apiFetch<{ version: number }>(base, { method: "DELETE" }),
		onSuccess: () => {
			setConfirm(false);
			onChange();
		},
	});
	const error = send.error ?? remove.error;

	return (
		<div className="flex flex-col gap-3">
			<div className="flex items-center gap-4">
				<PersonAvatar id={id} name={name} size={80} src={version > 0 ? `${base}?v=${version}` : null} />
				<div className="flex flex-col gap-2">
					<Button size="sm" isPending={send.isPending} onPress={() => input.current?.click()}>{version > 0 ? k.change : k.choose}</Button>
					{version > 0 ? <Button size="sm" variant="danger-soft" onPress={() => setConfirm(true)}>{k.remove}</Button> : null}
				</div>
			</div>
			<p className="text-xs text-muted">{k.hint}</p>
			{error ? <Notice tone="danger" role="alert">{error.message}</Notice> : null}
			<input
				ref={input}
				type="file"
				className="sr-only"
				tabIndex={-1}
				accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp"
				onChange={(event) => {
					const file = event.target.files?.[0];
					event.target.value = ""; // choosing the same file again must still fire
					if (file) send.mutate(file);
				}}
			/>
			<ConfirmDialog isOpen={confirm} onOpenChange={setConfirm} tone="danger" title={k.removeTitle} description={k.removeBody} confirmLabel={t.manage.deleteGo} isPending={remove.isPending} onConfirm={() => remove.mutate()} />
		</div>
	);
}
