import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FormRoot, Notice, SectionCard, SubmitButton, TextField } from "@nyxon/nasim";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { apiFetch } from "@/shared/api";
import { fill, t } from "@/strings";

const p = t.profile;
const l = t.login;
const schema = z.object({ username: z.string().min(3, l.shortUsername).max(32, l.shortUsername), password: z.string().min(8, l.shortPassword).max(128) });

/** The coach gives a student a username and password for the panel, or resets them. */
export function WebAccessCard({ id, username }: { id: number; username: string | null }) {
	const queryClient = useQueryClient();
	const form = useForm({ resolver: zodResolver(schema), defaultValues: { username: username ?? "", password: "" } });
	const save = useMutation({
		mutationFn: (values: z.infer<typeof schema>) => apiFetch(`/api/admin/students/${id}/web-access`, { method: "POST", body: JSON.stringify(values) }),
		onSuccess: () => {
			form.reset({ username: form.getValues("username"), password: "" });
			return queryClient.invalidateQueries({ queryKey: ["admin", "student", id] });
		},
	});
	return (
		<SectionCard title={p.webAccess} description={username ? fill(p.webAccessHas, { username }) : p.webAccessNone}>
			<FormRoot form={form} onSubmit={(values) => save.mutate(values)} className="flex flex-col gap-4">
				{save.isError ? <Notice tone="danger" role="alert">{save.error.message}</Notice> : null}
				{save.isSuccess ? <Notice tone="success" role="status">{p.webAccessSaved}</Notice> : null}
				<TextField name="username" label={l.username} description={l.usernameHint} dir="ltr" autoComplete="off" isRequired />
				<TextField name="password" label={l.password} description={l.passwordHint} type="password" dir="ltr" autoComplete="new-password" isRequired />
				<SubmitButton>{p.webAccessCreate}</SubmitButton>
			</FormRoot>
		</SectionCard>
	);
}
