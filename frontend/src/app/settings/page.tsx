/**
 * Settings page — configure ProPresenter and Ollama connection.
 */
"use client";

import { useEffect, useState } from "react";
import { settingsApi, type AppConfig, type ConnectionStatus } from "@/lib/api";
import { CheckCircle2, XCircle, RefreshCw, Save } from "lucide-react";

export default function SettingsPage() {
    const [config, setConfig] = useState<AppConfig | null>(null);
    const [form, setForm] = useState<AppConfig | null>(null);
    const [status, setStatus] = useState<ConnectionStatus | null>(null);
    const [saving, setSaving] = useState(false);
    const [checking, setChecking] = useState(false);
    const [saved, setSaved] = useState(false);

    useEffect(() => {
        settingsApi.get().then((c) => { setConfig(c); setForm(c); });
        checkStatus();
    }, []);

    async function checkStatus() {
        setChecking(true);
        try { setStatus(await settingsApi.status()); } catch { }
        setChecking(false);
    }

    async function handleSave() {
        if (!form) return;
        setSaving(true);
        try {
            const updated = await settingsApi.update(form);
            setConfig(updated);
            setForm(updated);
            setSaved(true);
            setTimeout(() => setSaved(false), 2000);
            await checkStatus();
        } catch (e) {
            alert("Save failed: " + e);
        }
        setSaving(false);
    }

    if (!form) return <div style={{ padding: 32, color: "var(--text-muted)" }}>Loading…</div>;

    return (
        <div style={{ padding: 32, maxWidth: 640 }}>
            <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 6 }}>Settings</h1>
            <p style={{ color: "var(--text-muted)", marginBottom: 32 }}>
                Configure connection details. Changes persist immediately.
            </p>

            {/* ProPresenter section */}
            <Section title="ProPresenter 7">
                <Field label="Host URL" hint="Default: http://localhost">
                    <input
                        value={form.propresenter_url}
                        onChange={(e) => setForm({ ...form, propresenter_url: e.target.value })}
                        placeholder="http://localhost"
                        style={inputStyle}
                    />
                </Field>
                <Field label="Port" hint="Default: 50001 (per PP7 API docs)">
                    <input
                        type="number"
                        value={form.propresenter_port}
                        onChange={(e) => setForm({ ...form, propresenter_port: Number(e.target.value) })}
                        placeholder="50001"
                        style={{ ...inputStyle, width: 140 }}
                    />
                </Field>
                <ConnectionBadge
                    connected={status?.propresenter_connected}
                    label={status?.propresenter_version ?? "Unknown"}
                />
            </Section>

            {/* Ollama section */}
            <Section title="Ollama AI">
                <Field label="Ollama URL" hint="Apple Silicon: http://host.docker.internal:11434">
                    <input
                        value={form.ollama_url}
                        onChange={(e) => setForm({ ...form, ollama_url: e.target.value })}
                        placeholder="http://host.docker.internal:11434"
                        style={inputStyle}
                    />
                </Field>
                <Field
                    label="Model"
                    hint={
                        status?.ollama_connected && status.ollama_models.length > 0
                            ? `Available: ${status.ollama_models.join(", ")}`
                            : "Run: ollama pull llama3.2:3b"
                    }
                >
                    <input
                        value={form.ollama_model}
                        onChange={(e) => setForm({ ...form, ollama_model: e.target.value })}
                        placeholder="llama3.2:3b"
                        style={inputStyle}
                    />
                </Field>
                <ConnectionBadge
                    connected={status?.ollama_connected}
                    label={status?.ollama_connected ? `${status!.ollama_models.length} model(s)` : "Not connected"}
                />
            </Section>

            {/* Actions */}
            <div style={{ display: "flex", gap: 12, marginTop: 24 }}>
                <button onClick={handleSave} disabled={saving} style={primaryBtn}>
                    <Save size={14} />
                    {saving ? "Saving…" : saved ? "Saved!" : "Save Settings"}
                </button>
                <button onClick={checkStatus} disabled={checking} style={secondaryBtn}>
                    <RefreshCw size={14} style={{ animation: checking ? "spin 1s linear infinite" : "none" }} />
                    Check Connection
                </button>
            </div>
        </div>
    );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
    return (
        <div
            style={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: 12,
                padding: "20px 24px",
                marginBottom: 20,
            }}
        >
            <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 18, marginTop: 0 }}>{title}</h2>
            {children}
        </div>
    );
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
    return (
        <div style={{ marginBottom: 16 }}>
            <label style={{ display: "block", fontSize: 13, fontWeight: 500, marginBottom: 6 }}>
                {label}
            </label>
            {children}
            {hint && <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>{hint}</p>}
        </div>
    );
}

function ConnectionBadge({ connected, label }: { connected?: boolean; label: string }) {
    return (
        <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, marginTop: 4 }}>
            {connected ? (
                <CheckCircle2 size={13} color="var(--success)" />
            ) : (
                <XCircle size={13} color="var(--error)" />
            )}
            <span style={{ color: connected ? "var(--success)" : "var(--error)" }}>
                {connected ? `Connected — ${label}` : "Not connected"}
            </span>
        </div>
    );
}

const inputStyle: React.CSSProperties = {
    background: "var(--surface-2)",
    border: "1px solid var(--border)",
    borderRadius: 8,
    padding: "8px 12px",
    color: "var(--text)",
    fontSize: 14,
    width: "100%",
    outline: "none",
};

const primaryBtn: React.CSSProperties = {
    display: "flex",
    alignItems: "center",
    gap: 6,
    background: "var(--accent)",
    color: "#fff",
    border: "none",
    borderRadius: 8,
    padding: "9px 18px",
    cursor: "pointer",
    fontWeight: 600,
    fontSize: 14,
};

const secondaryBtn: React.CSSProperties = {
    display: "flex",
    alignItems: "center",
    gap: 6,
    background: "var(--surface-2)",
    color: "var(--text)",
    border: "1px solid var(--border)",
    borderRadius: 8,
    padding: "9px 18px",
    cursor: "pointer",
    fontSize: 14,
};
