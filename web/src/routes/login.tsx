import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, redirect, useNavigate } from "@tanstack/react-router";
import { Button, Notice, SectionCard } from "@nyxon/nasim";
import { loginConfigQuery, loginDev, loginWithTelegram, meQuery, TelegramLoginButton, type TelegramUser } from "@/features/auth";
import { t } from "@/strings";

export const Route = createFileRoute("/login")({
	// Already signed in on this device: straight to the app.
	beforeLoad: async ({ context }) => {
		const me = await context.queryClient.fetchQuery(meQuery).catch(() => null);
		if (me) throw redirect({ to: "/" });
	},
	component: Login,
});

function Login() {
	const queryClient = useQueryClient();
	const navigate = useNavigate();
	const config = useQuery(loginConfigQuery);
	const signIn = useMutation({
		mutationFn: (user: TelegramUser | "coach" | "student") => (typeof user === "object" ? loginWithTelegram(user) : loginDev(user === "student")),
		onSuccess: async (me) => {
			queryClient.setQueryData(meQuery.queryKey, me);
			await navigate({ to: "/" });
		},
	});

	return (
		<main className="grid min-h-dvh place-items-center px-page py-8">
			<div className="flex w-full max-w-md flex-col gap-4">
				<h1 className="text-center text-3xl font-bold text-accent">{t.brand}</h1>
				<SectionCard title={t.login.title} description={t.login.hint}>
					<div className="flex flex-col gap-4">
						{signIn.isError ? (
							<Notice tone="danger" title={t.login.failed}>
								{signIn.error.message}
							</Notice>
						) : null}
						{config.data?.dev_login ? (
							<div className="flex flex-col gap-2">
								<Button isPending={signIn.isPending} onPress={() => signIn.mutate("coach")}>
									{t.login.dev}
								</Button>
								<Button variant="secondary" isPending={signIn.isPending} onPress={() => signIn.mutate("student")}>
									{t.login.devStudent}
								</Button>
							</div>
						) : config.data ? (
							<TelegramLoginButton botUsername={config.data.bot_username} onAuth={(user) => signIn.mutate(user)} />
						) : null}
						<Notice tone="info">{t.login.notice}</Notice>
					</div>
				</SectionCard>
			</div>
		</main>
	);
}
