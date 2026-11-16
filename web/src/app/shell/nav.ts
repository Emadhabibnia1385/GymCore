import type { ComponentType, SVGProps } from "react";
import CalendarIcon from "~icons/solar/calendar-linear";
import CheckIcon from "~icons/solar/check-circle-linear";
import DumbbellIcon from "~icons/solar/dumbbell-large-minimalistic-linear";
import WalletIcon from "~icons/solar/wallet-linear";
import CartIcon from "~icons/solar/cart-large-2-linear";
import GiftIcon from "~icons/solar/gift-linear";
import HomeIcon from "~icons/solar/home-2-linear";
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
			{ to: "/attendance", label: t.nav.attendance, Icon: CheckIcon },
			{ to: "/students", label: t.nav.students, Icon: UsersIcon },
			{ to: "/finance", label: t.nav.finance, Icon: WalletIcon },
			{ to: "/classes", label: t.nav.classes, Icon: DumbbellIcon },
		];
	}
	return [
		home,
		{ to: "/courses", label: t.nav.courses, Icon: CalendarIcon },
		{ to: "/programs", label: t.nav.programs, Icon: GiftIcon },
		{ to: "/request", label: t.nav.request, Icon: CartIcon },
	];
}
