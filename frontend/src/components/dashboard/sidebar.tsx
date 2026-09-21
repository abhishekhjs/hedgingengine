"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import {
  ChartLine,
  Buildings,
  GitBranch,
  Cube,
  Shield,
} from "@phosphor-icons/react";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Market Risk", icon: ChartLine },
  { href: "/dashboard/exposure", label: "Exposure", icon: Buildings },
  { href: "/dashboard/transmission", label: "Transmission", icon: GitBranch },
  { href: "/dashboard/montecarlo", label: "Monte Carlo", icon: Cube },
  { href: "/dashboard/optimization", label: "Optimization", icon: Shield },
] as const;

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed inset-y-0 left-0 z-30 flex w-60 flex-col bg-[var(--sidebar)] border-r border-[var(--sidebar-border)]">
      {/* Brand */}
      <div className="flex h-16 items-center gap-3 px-5 border-b border-[var(--sidebar-border)]">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-stripi-primary">
          <Shield size={18} weight="bold" className="text-white" />
        </div>
        <div>
          <p className="text-sm font-medium text-white tracking-tight">
            IFSA
          </p>
          <p className="text-[11px] text-white/50 tracking-wide">
            Risk Engine
          </p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const isActive =
            href === "/dashboard"
              ? pathname === "/dashboard"
              : pathname.startsWith(href);

          return (
            <Link
              key={href}
              href={href}
              className={`
                flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors
                ${
                  isActive
                    ? "bg-[var(--sidebar-accent)] text-white font-medium"
                    : "text-white/60 hover:text-white hover:bg-white/[0.06]"
                }
              `}
            >
              <Icon
                size={18}
                weight={isActive ? "fill" : "regular"}
                className="shrink-0"
              />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-[var(--sidebar-border)]">
        <p className="text-[11px] text-white/30 font-tabular">
          Market Risk Engine v1.0
        </p>
      </div>
    </aside>
  );
}
