import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FormRoot, Notice, SubmitButton, TextField } from "@nyxon/nasim";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { t } from "@/strings";
import { changePassword, loginWithPassword, meQuery, register, setPassword, type Me } from "./api";

const l = t.login;
const username = z.string().min(3, l.shortUsername).max(32, l.shortUsername);
const password = z.string().min(8, l.shortPassword).max(128);

function ServerError({ error }: { error: Error | null }) {
	return error ? (
		<Notice tone="danger" title={l.failed} role="alert">
			{error.message}
		</Notice>
	) : null;
}

export function PasswordLoginForm({ onDone }: { onDone: (me: Me) => void }) {
	const form = useForm({
		resolver: zodResolver(z.object({ username: z.string().min(1, l.needUsername), password: z.string().min(1, l.needPassword) })),
		defaultValues: { username: "", password: "" },
	});
	const login = useMutation({ mutationFn: loginWithPassword, onSuccess: onDone });
	return (
		<FormRoot form={form} onSubmit={(values) => login.mutate(values)} className="flex flex-col gap-4">
			<ServerError error={login.error} />
			<TextField name="username" label={l.username} dir="ltr" autoComplete="username" isRequired />
			<TextField name="password" label={l.password} type="password" dir="ltr" autoComplete="current-password" isRequired />
			<SubmitButton>{l.submitIn}</SubmitButton>
		</FormRoot>
	);
}

export function RegisterForm({ onDone }: { onDone: (me: Me) => void }) {
	const form = useForm({
		resolver: zodResolver(z.object({ name: z.string().trim().min(1, l.needName).max(80), username, password })),
		defaultValues: { name: "", username: "", password: "" },
	});
	const signUp = useMutation({ mutationFn: register, onSuccess: onDone });
	return (
		<FormRoot form={form} onSubmit={(values) => signUp.mutate(values)} className="flex flex-col gap-4">
			<ServerError error={signUp.error} />
			<TextField name="name" label={l.name} autoComplete="name" isRequired />
			<TextField name="username" label={l.username} description={l.usernameHint} dir="ltr" autoComplete="username" isRequired />
			<TextField name="password" label={l.password} description={l.passwordHint} type="password" dir="ltr" autoComplete="new-password" isRequired />
			<SubmitButton>{l.submitUp}</SubmitButton>
		</FormRoot>
	);
}

/** A Telegram-only person adds a username and password of their own. */
export function CreatePasswordForm() {
	const queryClient = useQueryClient();
	const form = useForm({ resolver: zodResolver(z.object({ username, password })), defaultValues: { username: "", password: "" } });
	const create = useMutation({ mutationFn: setPassword, onSuccess: (me) => queryClient.setQueryData(meQuery.queryKey, me) });
	return (
		<FormRoot form={form} onSubmit={(values) => create.mutate(values)} className="flex flex-col gap-4">
			<ServerError error={create.error} />
			<TextField name="username" label={l.username} description={l.usernameHint} dir="ltr" autoComplete="username" isRequired />
			<TextField name="password" label={l.password} description={l.passwordHint} type="password" dir="ltr" autoComplete="new-password" isRequired />
			<SubmitButton>{t.account.createSubmit}</SubmitButton>
		</FormRoot>
	);
}

export function ChangePasswordForm() {
	const a = t.account;
	const form = useForm({
		resolver: zodResolver(z.object({ old_password: z.string().min(1, l.needPassword), new_password: password })),
		defaultValues: { old_password: "", new_password: "" },
	});
	const change = useMutation({ mutationFn: changePassword, onSuccess: () => form.reset() });
	return (
		<FormRoot form={form} onSubmit={(values) => change.mutate(values)} className="flex flex-col gap-4">
			<ServerError error={change.error} />
			{change.isSuccess ? <Notice tone="success" role="status">{a.saved}</Notice> : null}
			<TextField name="old_password" label={a.oldPassword} type="password" dir="ltr" autoComplete="current-password" isRequired />
			<TextField name="new_password" label={a.newPassword} description={l.passwordHint} type="password" dir="ltr" autoComplete="new-password" isRequired />
			<SubmitButton>{a.changeSubmit}</SubmitButton>
		</FormRoot>
	);
}
