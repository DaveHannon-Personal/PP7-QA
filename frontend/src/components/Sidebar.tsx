/**
 * Sidebar navigation component.
 */
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    LayoutDashboard,
    MessageSquare,
    ListChecks,
    FolderOpen,
    ClipboardCheck,
    Settings,
} from "lucide-react";
import clsx from "clsx";

const navItems = [
    { href: "/", label: "Dashboard", icon: LayoutDashboard },
    { href: "/chat", label: "AI Chat", icon: MessageSquare },
    { href: "/rules", label: "Rules", icon: ListChecks },
    { href: "/profiles", label: "Profiles", icon: FolderOpen },
    { href: "/audit", label: "Audit", icon: ClipboardCheck },
    { href: "/settings", label: "Settings", icon: Settings },
];

export default function Sidebar() {
    const pathname = usePathname();

    return (
        <aside
            style={{
                width: 220,
                minHeight: "100vh",
                background: "var(--surface)",
                borderRight: "1px solid var(--border)",
                display: "flex",
                flexDirection: "column",
                flexShrink: 0,
            }}
        >
            {/* Logo */}
            <div
                style={{
                    padding: "20px 16px 12px",
                    borderBottom: "1px solid var(--border)",
                }}
            >
                <div style={{ fontWeight: 700, fontSize: 16, color: "var(--accent)" }}>
                    PP7-QA
                </div>
                <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>
                    ProPresenter 7 Audit
                </div>
            </div>

            {/* Nav */}
            <nav style={{ flex: 1, padding: "12px 8px" }}>
                {navItems.map(({ href, label, icon: Icon }) => {
                    const active = pathname === href;
                    return (
                        <Link
                            key={href}
                            href={href}
                            style={{
                                display: "flex",
                                alignItems: "center",
                                gap: 10,
                                padding: "9px 12px",
                                borderRadius: 8,
                                marginBottom: 2,
                                color: active ? "var(--accent)" : "var(--text-muted)",
                                background: active ? "rgba(99,102,241,0.12)" : "transparent",
                                fontWeight: active ? 600 : 400,
                                fontSize: 14,
                                textDecoration: "none",
                                transition: "all 0.15s",
                            }}
                        >
                            <Icon size={16} />
                            {label}
                        </Link>
                    );
                })}
            </nav>

            {/* Footer */}
            <div
                style={{
                    padding: "12px 16px",
                    borderTop: "1px solid var(--border)",
                    fontSize: 11,
                    color: "var(--text-muted)",
                }}
            >
                v1.0.0 · Phase 1
            </div>
        </aside>
    );
}
