import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, ConfirmDialog, Notice, SectionCard, TextField } from "@nyxon/nasim";
import { useState } from "react";
import { FilePick } from "@/shared/FilePick";
import { t } from "@/strings";
import { brandQuery, logoUrl, removeLogo, saveTexts, uploadLogo, type Brand, type LogoKind } from "./api";

const b = t.brand;

/** The panel's identity: its name, its browser-tab title, and the two logos. */
export function BrandCard() {
	const brand = useQuery(brandQuery).data;
	if (!brand) return null;
	// Remounted when the saved values change, so the boxes show what is stored.
	return <Texts key={`${brand.name}|${brand.title}`} brand={brand} />;
}

function Texts({ brand }: { brand: Brand }) {
	const queryClient = useQueryClient();
	const [name, setName] = useState(brand.name);
	const [title, setTitle] = useState(brand.title);
	const save = useMutation({ mutationFn: () => saveTexts({ name, title }), onSuccess: (next) => queryClient.setQueryData(brandQuery.queryKey, next) });
	return (
		<SectionCard title={b.title} description={b.hint}>
			<div className="flex flex-col gap-6">
				<div className="flex flex-col gap-4">
					{save.isError ? <Notice tone="danger" role="alert">{save.error.message}</Notice> : null}
					{save.isSuccess ? <Notice tone="success" role="status">{t.common.saved}</Notice> : null}
					<TextField label={b.name} description={b.nameHint} value={name} onChange={setName} maxLength={60} />
					<TextField label={b.pageTitle} description={b.pageTitleHint} value={title} onChange={setTitle} maxLength={80} />
					<Button isDisabled={!name.trim()} isPending={save.isPending} onPress={() => save.mutate()}>{t.common.save}</Button>
				</div>
				<Logo kind="wide" brand={brand} label={b.wide} hint={b.wideHint} />
				<Logo kind="icon" brand={brand} label={b.icon} hint={b.iconHint} />
			</div>
		</SectionCard>
	);
}

function Logo({ kind, brand, label, hint }: { kind: LogoKind; brand: Brand; label: string; hint: string }) {
	const queryClient = useQueryClient();
	const [file, setFile] = useState<File | null>(null);
	const [confirm, setConfirm] = useState(false);
	const store = (next: Brand) => queryClient.setQueryData(brandQuery.queryKey, next);
	const upload = useMutation({ mutationFn: () => uploadLogo(kind, file!), onSuccess: (next) => { setFile(null); store(next); } });
	const remove = useMutation({ mutationFn: () => removeLogo(kind), onSuccess: (next) => { setConfirm(false); store(next); } });
	const has = kind === "wide" ? brand.wide : brand.icon;
	const error = upload.error ?? remove.error;

	return (
		<div className="flex flex-col gap-3 border-t border-separator pt-4">
			<h3 className="font-medium">{label}</h3>
			<p className="text-sm text-muted">{hint}</p>
			{has ? (
				<div className="flex items-center gap-3 rounded-field border border-border bg-surface-secondary p-3">
					<img src={logoUrl(kind, brand)} alt={label} className={kind === "wide" ? "h-12 w-auto max-w-56 object-contain" : "size-14 rounded-field object-contain"} />
					<Button size="sm" variant="danger-soft" onPress={() => setConfirm(true)}>{t.common.delete}</Button>
				</div>
			) : (
				<p className="text-sm text-muted">{b.none}</p>
			)}
			{error ? <Notice tone="danger" role="alert">{error.message}</Notice> : null}
			<FilePick label={b.choose} file={file} onChange={setFile} accept=".png,.jpg,.jpeg,.webp" />
			<Button isDisabled={!file} isPending={upload.isPending} onPress={() => upload.mutate()}>{has ? b.replace : b.upload}</Button>
			<ConfirmDialog isOpen={confirm} onOpenChange={setConfirm} tone="danger" title={b.removeTitle} description={b.removeBody} confirmLabel={t.manage.deleteGo} isPending={remove.isPending} onConfirm={() => remove.mutate()} />
		</div>
	);
}
