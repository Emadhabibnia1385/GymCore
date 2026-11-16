import type { ComponentType, SVGProps } from "react";
import CalendarIcon from "~icons/solar/calendar-linear";
import CalendarMarkIcon from "~icons/solar/calendar-mark-linear";
import PhoneIcon from "~icons/solar/phone-calling-linear";
import SettingsIcon from "~icons/solar/settings-linear";
import CheckIcon from "~icons/solar/check-circle-linear";
import WalletIcon from "~icons/solar/wallet-linear";
import CartIcon from "~icons/solar/cart-large-2-linear";
import GiftIcon from "~icons/solar/gift-linear";
import HomeIcon from "~icons/solar/home-2-linear";
import ChartIcon from "~icons/solar/chart-2-linear";
import UsersIcon from "~icons/solar/users-group-rounded-linear";
import type { Me } from "@/features/auth";
import { t } from "@/strings";

export type NavItem = { to: string; label: string; Icon: ComponentType<SVGProps<SVGSVGElement>> };

// A phone's bottom bar holds four; the full menu is in the drawer.
export const PHONE_TABS = 4;

const home: NavItem = { to: "/", label: t.nav.home, Icon: HomeIcon };

// The menu tree, per role, in one place. A page is added here when it exists.
export function navFor(role: Me["role"]): NavItem[] {
	if (role === "admin") {
		return [
			home,
			// The daily four come first — they are the phone's bottom bar. Class types and messages
			// live inside settings, which keeps the menu short.
			{ to: "/attendance", label: t.nav.attendance, Icon: CheckIcon },
			{ to: "/students", label: t.nav.students, Icon: UsersIcon },
			{ to: "/timetable", label: t.nav.timetable, Icon: CalendarMarkIcon },
			{ to: "/finance", label: t.nav.finance, Icon: WalletIcon },
			{ to: "/reports", label: t.nav.reports, Icon: ChartIcon },
			{ to: "/followups", label: t.nav.followups, Icon: PhoneIcon },
			{ to: "/plans", label: t.nav.plans, Icon: GiftIcon },
			{ to: "/settings", label: t.nav.settings, Icon: SettingsIcon },
		];
	}
	return [
		home,
		{ to: "/courses", label: t.nav.courses, Icon: CalendarIcon },
		{ to: "/programs", label: t.nav.programs, Icon: GiftIcon },
		{ to: "/request", label: t.nav.request, Icon: CartIcon },
	];
}
