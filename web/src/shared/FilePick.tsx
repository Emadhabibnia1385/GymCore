import { useRef } from "react";
import { Button } from "@nyxon/nasim";
import { t } from "@/strings";

/** A file chosen from the computer or phone; shows the chosen name. */
export function FilePick({ label, file, onChange }: { label: string; file: File | null; onChange: (file: File | null) => void }) {
	const input = useRef<HTMLInputElement>(null);
	return (
		<div className="flex flex-col gap-2">
			<span className="text-sm font-medium">{label}</span>
			<div className="flex items-center gap-3">
				<Button size="sm" variant="secondary" onPress={() => input.current?.click()}>{t.plans.pickFile}</Button>
				<span className="min-w-0 truncate text-sm text-muted" dir="auto">{file?.name ?? t.plans.noFile}</span>
			</div>
			<input ref={input} type="file" className="sr-only" tabIndex={-1} accept=".pdf,.jpg,.jpeg,.png,.webp,.txt,.docx,.xlsx" onChange={(event) => onChange(event.target.files?.[0] ?? null)} />
		</div>
	);
}
