import { useQueryClient } from "@tanstack/react-query";
import { Outlet, useNavigate, useRouterState } from "@tanstack/react-router";
import { AccountMenu, AppShell, OfflineBanner, ThemeToggle } from "@nyxon/nasim";
import DownloadIcon from "~icons/solar/download-minimalistic-linear";
import UserIcon from "~icons/solar/user-circle-linear";
import LogoutIcon from "~icons/solar/logout-2-linear";
import { logout, type Me } from "@/features/auth";
import { BrandMark } from "@/features/brand";
import { useInstall } from "@/features/pwa";
import { t } from "@/strings";
import { navFor } from "./nav";
import { PhoneTabBar } from "./PhoneTabBar";

export function AppFrame({ me }: { me: Me }) {
	const pathname = useRouterState({ select: (state) => state.location.pathname });
	const navigate = useNavigate();
	const queryClient = useQueryClient();
	const install = useInstall();

	async function signOut() {
		await logout();
		queryClient.clear();
		await navigate({ to: "/login" });
	}

	const items = [
		{ id: "account", label: t.account.menu, href: "/account", icon: <UserIcon /> },
		...(install ? [{ id: "install", label: t.role.install, icon: <DownloadIcon /> }] : []),
		{ id: "logout", label: t.role.logout, icon: <LogoutIcon />, tone: "danger" as const },
	];

	return (
		<>
			<AppShell
				brand={<BrandMark />}
				navLabel={t.nav.label}
				nav={navFor(me.role).map(({ to, label, Icon }) => ({
					href: to,
					label,
					icon: <Icon className="size-5" />,
					isCurrent: to === "/" ? pathname === "/" : pathname.startsWith(to),
				}))}
				topbar={<ThemeToggle lightLabel={t.theme.light} darkLabel={t.theme.dark} />}
				sidebarFooter={
					<AccountMenu
						name={me.name}
						description={me.role === "admin" ? t.role.coach : t.role.student}
						items={items}
						onAction={(id) => (id === "logout" ? void signOut() : void install?.())}
					/>
				}
				banner={<OfflineBanner />}
				contentWidth="full"
			>
				<div className="pb-(--nasim-bottom-bar,0px) lg:pb-0">
					<Outlet />
				</div>
			</AppShell>
			<PhoneTabBar role={me.role} />
		</>
	);
}
