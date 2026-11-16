import type { ComponentType, SVGProps } from "react";
import CalendarIcon from "~icons/solar/calendar-linear";
import CartIcon from "~icons/solar/cart-large-2-linear";
import GiftIcon from "~icons/solar/gift-linear";
import HomeIcon from "~icons/solar/home-2-linear";
import UsersIcon from "~icons/solar/users-group-rounded-linear";
import type { Me } from "@/features/auth";
import { t } from "@/strings";

export type NavItem = { to: string; label: string; Icon: ComponentType<SVGProps<SVGSVGElement>> };

const home: NavItem = { to: "/", label: t.nav.home, Icon: HomeIcon };

// The menu tree, per role, in one place. A page is added here when it exists.
export function navFor(role: Me["role"]): NavItem[] {
	if (role === "admin") return [home, { to: "/students", label: t.nav.students, Icon: UsersIcon }];
	return [
		home,
		{ to: "/courses", label: t.nav.courses, Icon: CalendarIcon },
		{ to: "/programs", label: t.nav.programs, Icon: GiftIcon },
		{ to: "/request", label: t.nav.request, Icon: CartIcon },
	];
}
