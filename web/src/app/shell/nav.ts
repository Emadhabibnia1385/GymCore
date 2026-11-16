import type { ComponentType, SVGProps } from "react";
import HomeIcon from "~icons/solar/home-2-linear";
import { t } from "@/strings";

export type NavItem = { to: string; label: string; Icon: ComponentType<SVGProps<SVGSVGElement>> };

// The menu tree, in one place. A page is added here when it exists.
export const NAV: NavItem[] = [{ to: "/", label: t.nav.home, Icon: HomeIcon }];
