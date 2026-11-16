import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BottomSheet, Button, ErrorState, Notice, PageHeader, PageSkeleton, SectionCard, TextAreaField, TextField } from "@nyxon/nasim";
import { useState } from "react";
import { fill, t } from "@/strings";
import { contactsQuery, moveContact, patchContact, saveSetting, settingsQuery, type Contact, type Setting } from "./api";

const s = t.settings;

export function SettingsPage() {
	const queryClient = useQueryClient();
	const settings = useQuery(settingsQuery);
	const contacts = useQuery(contactsQuery);
	const [editing, setEditing] = useState<Setting | null>(null);
	const [link, setLink] = useState<Contact | null>(null);
	const refresh = () => queryClient.invalidateQueries({ queryKey: ["admin"] });
	const toggle = useMutation({ mutationFn: (row: Setting) => saveSetting(row.key, row.value === "1" ? "0" : "1"), onSuccess: refresh });
	const activate = useMutation({ mutationFn: (row: Contact) => patchContact(row.id, { active: !row.active }), onSuccess: refresh });
	const move = useMutation({ mutationFn: ({ id, direction }: { id: number; direction: -1 | 1 }) => moveContact(id, direction), onSuccess: refresh });

	if (settings.isPending || contacts.isPending) return <PageSkeleton />;
	if (settings.isError || contacts.isError) return <ErrorState as="h1" onRetry={() => { void settings.refetch(); void contacts.refetch(); }} />;
	const error = toggle.error ?? activate.error ?? move.error;

	return (
		<div className="flex flex-col gap-6">
			<PageHeader title={s.title} description={s.hint} />
			{error ? <Notice tone="danger" role="alert">{error.message}</Notice> : null}
			<SectionCard title={s.title}>
				<ul className="flex flex-col gap-2">
					{settings.data.map((row) => (
						<li key={row.key}>
							{row.kind === "toggle" ? (
								<button type="button" className="flex min-h-14 w-full items-center justify-between gap-3 rounded-field border border-border bg-surface p-4 text-start hover:bg-surface-secondary" onClick={() => toggle.mutate(row)}>
									<span>{row.label}</span>
									<span className={row.value === "1" ? "text-sm font-medium text-accent" : "text-sm text-muted"}>{row.value === "1" ? s.on : s.off}</span>
								</button>
							) : (
								<button type="button" className="flex min-h-14 w-full items-center justify-between gap-3 rounded-field border border-border bg-surface p-4 text-start hover:bg-surface-secondary" onClick={() => setEditing(row)}>
									<span className="shrink-0">{row.label}</span>
									<span className="min-w-0 truncate text-sm text-muted" dir={row.kind === "text" || row.kind === "long" ? "auto" : "ltr"}>{row.value || "—"}</span>
								</button>
							)}
						</li>
					))}
				</ul>
			</SectionCard>

			<SectionCard title={s.contacts} description={s.contactsHint}>
				<ul className="flex flex-col gap-2">
					{contacts.data.map((row, index) => (
						<li key={row.id} className="flex flex-col gap-2 rounded-field border border-border bg-surface p-3">
							<button type="button" className="flex items-center justify-between gap-3 text-start" onClick={() => setLink(row)}>
								<span className={row.active ? "" : "text-muted"}>{`${row.icon ?? ""} ${row.label}`.trim()}</span>
								<span className="min-w-0 truncate text-xs text-muted" dir="ltr">{row.url}</span>
							</button>
							<div className="flex flex-wrap gap-2">
								<Button size="sm" variant="secondary" isPending={activate.isPending && activate.variables?.id === row.id} onPress={() => activate.mutate(row)}>{row.active ? s.active : s.inactive}</Button>
								<Button size="sm" variant="secondary" isDisabled={index === 0} onPress={() => move.mutate({ id: row.id, direction: -1 })}>{s.up}</Button>
								<Button size="sm" variant="secondary" isDisabled={index === contacts.data.length - 1} onPress={() => move.mutate({ id: row.id, direction: 1 })}>{s.down}</Button>
							</div>
						</li>
					))}
				</ul>
			</SectionCard>

			<SettingSheet setting={editing} onClose={() => setEditing(null)} />
			<ContactSheet contact={link} onClose={() => setLink(null)} />
		</div>
	);
}

function SettingSheet({ setting, onClose }: { setting: Setting | null; onClose: () => void }) {
	return (
		<BottomSheet isOpen={setting !== null} onOpenChange={(open) => !open && onClose()} title={setting ? fill(s.editValue, { label: setting.label }) : ""}>
			{setting ? <SettingForm key={setting.key} setting={setting} onClose={onClose} /> : null}
		</BottomSheet>
	);
}

function SettingForm({ setting, onClose }: { setting: Setting; onClose: () => void }) {
	const queryClient = useQueryClient();
	const [value, setValue] = useState(setting.value);
	const save = useMutation({
		mutationFn: () => saveSetting(setting.key, value),
		onSuccess: async () => {
			await queryClient.invalidateQueries({ queryKey: ["admin", "settings"] });
			onClose();
		},
	});
	const ltr = setting.kind === "number" || setting.kind === "link";
	return (
		<div className="flex flex-col gap-4">
			{save.isError ? <Notice tone="danger" role="alert">{save.error.message}</Notice> : null}
			{setting.kind === "long" ? (
				<TextAreaField label={s.value} value={value} onChange={setValue} rows={8} maxLength={4000} />
			) : (
				<TextField label={s.value} value={value} onChange={setValue} dir={ltr ? "ltr" : undefined} inputMode={setting.kind === "number" ? "numeric" : undefined} />
			)}
			<Button size="lg" isPending={save.isPending} onPress={() => save.mutate()}>{t.common.save}</Button>
		</div>
	);
}

function ContactSheet({ contact, onClose }: { contact: Contact | null; onClose: () => void }) {
	return (
		<BottomSheet isOpen={contact !== null} onOpenChange={(open) => !open && onClose()} title={contact?.label ?? ""}>
			{contact ? <ContactForm key={contact.id} contact={contact} onClose={onClose} /> : null}
		</BottomSheet>
	);
}

function ContactForm({ contact, onClose }: { contact: Contact; onClose: () => void }) {
	const queryClient = useQueryClient();
	const [label, setLabel] = useState(contact.label);
	const [url, setUrl] = useState(contact.url);
	const save = useMutation({
		mutationFn: () => patchContact(contact.id, { label, url }),
		onSuccess: async () => {
			await queryClient.invalidateQueries({ queryKey: ["admin", "contacts"] });
			onClose();
		},
	});
	return (
		<div className="flex flex-col gap-4">
			{save.isError ? <Notice tone="danger" role="alert">{save.error.message}</Notice> : null}
			<TextField label={s.label} value={label} onChange={setLabel} maxLength={120} />
			<TextField label={s.url} value={url} onChange={setUrl} dir="ltr" />
			<Button size="lg" isPending={save.isPending} onPress={() => save.mutate()}>{t.common.save}</Button>
		</div>
	);
}
