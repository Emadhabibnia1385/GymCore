import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, redirect, useNavigate } from "@tanstack/react-router";
import { Button, Notice, SectionCard } from "@nyxon/nasim";
import { useState } from "react";
import {
	loginConfigQuery,
	BotLoginButton,
	loginDev,
	meQuery,
	PasswordLoginForm,
	RegisterForm,
	type Me,
} from "@/features/auth";
import { BrandMark } from "@/features/brand";
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
	const [mode, setMode] = useState<"in" | "up">("in");

	async function signedIn(me: Me) {
		queryClient.setQueryData(meQuery.queryKey, me);
		await navigate({ to: "/" });
	}
	const dev = useMutation({ mutationFn: (who: "coach" | "student") => loginDev(who === "student"), onSuccess: signedIn });
	const canSignUp = config.data?.registration_open ?? false;

	return (
		<main className="grid min-h-dvh place-items-center px-page py-8">
			<div className="flex w-full max-w-md flex-col gap-4">
				<h1 className="flex justify-center"><BrandMark size="hero" /></h1>
				<SectionCard title={mode === "up" && canSignUp ? t.login.signUp : t.login.title} description={t.login.hint}>
					<div className="flex flex-col gap-5">
						{mode === "up" && canSignUp ? (
							<RegisterForm onDone={signedIn} />
						) : (
							<PasswordLoginForm onDone={signedIn} />
						)}

						<div className="flex flex-col gap-3 border-t border-separator pt-4">
							<p className="text-center text-sm text-muted">{t.login.or}</p>
							{dev.isError ? (
								<Notice tone="danger" title={t.login.failed} role="alert">
									{dev.error.message}
								</Notice>
							) : null}
							{config.data?.dev_login ? (
								<div className="flex flex-col gap-2">
									<Button variant="secondary" isPending={dev.isPending} onPress={() => dev.mutate("coach")}>
										{t.login.dev}
									</Button>
									<Button variant="secondary" isPending={dev.isPending} onPress={() => dev.mutate("student")}>
										{t.login.devStudent}
									</Button>
								</div>
							) : (
								<BotLoginButton
									onDone={(me) => void signedIn(me)}
									// Sign-in and sign-up each offer only the other one, right beside the Telegram button.
									aside={canSignUp ? <Button size="lg" variant="secondary" onPress={() => setMode(mode === "up" ? "in" : "up")}>{mode === "up" ? t.login.signIn : t.login.signUp}</Button> : undefined}
								/>
							)}
						</div>
					</div>
				</SectionCard>
			</div>
		</main>
	);
}
