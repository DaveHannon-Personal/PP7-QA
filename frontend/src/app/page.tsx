/**
 * Dashboard — connection status summary and quick-start links.
 */
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { settingsApi, type ConnectionStatus } from "@/lib/api";
import { CheckCircle2, XCircle, ArrowRight, MessageSquare, ListChecks, ClipboardCheck } from "lucide-react";

export default function DashboardPage() {
    const [status, setStatus] = useState<ConnectionStatus | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        settingsApi.status().then(setStatus).finally(() => setLoading(false));
    }, []);

    return (
        <div style={{ padding: 32, maxWidth: 900 }}>
            <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 6 }}>PP7-QA Dashboard</h1>
            <p style={{ color: "var(--text-muted)", marginBottom: 32 }}>
                AI-powered compliance auditing for ProPresenter 7
            </p>

            {/* Connection status cards */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 40 }}>
                <StatusCard
                    label="ProPresenter 7"
                    connected={status?.propresenter_connected ?? false}
                    detail={status?.propresenter_version ?? (loading ? "Checking…" : "Not connected")}
                    settingsHref="/settings"
                />
                <StatusCard
                    label="Ollama AI"
                    connected={status?.ollama_connected ?? false}
                    detail={
                        status?.ollama_connected
                            ? `${status.ollama_models.length} model(s) available`
                            : loading ? "Checking…" : "Not connected"
                    }
                    settingsHref="/settings"
                />
            </div>

            {/* Quick actions */}
            <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Get started</h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
                <QuickLink
                    href="/chat"
                    icon={<MessageSquare size={20} />}
                    title="Ask AI to create a rule"
                    desc="Describe a compliance requirement in plain English"
                />
                <QuickLink
                    href="/rules"
                    icon={<ListChecks size={20} />}
                    title="Manage rules"
                    desc="Create, edit, and organise your QA rules"
                />
                <QuickLink
                    href="/audit"
                    icon={<ClipboardCheck size={20} />}
                    title="Run an audit"
                    desc="Check your presentations for compliance violations"
                />
            </div>
        </div>
    );
}

function StatusCard({
    label,
    connected,
    detail,
    settingsHref,
}: {
    label: string;
    connected: boolean;
    detail: string;
    settingsHref: string;
}) {
    return (
        <div
            style={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: 12,
                padding: "20px 24px",
            }}
        >
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
                {connected ? (
                    <CheckCircle2 size={18} color="var(--success)" />
                ) : (
                    <XCircle size={18} color="var(--error)" />
                )}
                <span style={{ fontWeight: 600 }}>{label}</span>
            </div>
            <p style={{ fontSize: 13, color: "var(--text-muted)", margin: "0 0 12px" }}>{detail}</p>
            {!connected && (
                <Link
                    href={settingsHref}
                    style={{ fontSize: 12, color: "var(--accent)", textDecoration: "none" }}
                >
                    Configure in Settings →
                </Link>
            )}
        </div>
    );
}

function QuickLink({
    href,
    icon,
    title,
    desc,
}: {
    href: string;
    icon: React.ReactNode;
    title: string;
    desc: string;
}) {
    return (
        <Link
            href={href}
            style={{
                display: "block",
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: 12,
                padding: "20px 24px",
                textDecoration: "none",
                transition: "border-color 0.15s",
            }}
        >
            <div style={{ color: "var(--accent)", marginBottom: 10 }}>{icon}</div>
            <div style={{ fontWeight: 600, marginBottom: 4 }}>{title}</div>
            <div style={{ fontSize: 13, color: "var(--text-muted)" }}>{desc}</div>
        </Link>
    );
}
