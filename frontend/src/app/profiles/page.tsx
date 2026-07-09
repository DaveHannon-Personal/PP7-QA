/**
 * Profiles page — manage named rule collections.
 */
"use client";

import { useEffect, useState } from "react";
import { profilesApi, rulesApi, type ProfileSummary, type Rule } from "@/lib/api";
import { Plus, Trash2, FolderOpen, X, Check, Pencil } from "lucide-react";

export default function ProfilesPage() {
    const [profiles, setProfiles] = useState<ProfileSummary[]>([]);
    const [rules, setRules] = useState<Rule[]>([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [editId, setEditId] = useState<number | null>(null);
    const [form, setForm] = useState({ name: "", description: "", rule_ids: [] as number[] });
    const [saving, setSaving] = useState(false);

    async function load() {
        setLoading(true);
        const [p, r] = await Promise.all([profilesApi.list(), rulesApi.list()]);
        setProfiles(p);
        setRules(r);
        setLoading(false);
    }

    useEffect(() => { load(); }, []);

    function openCreate() {
        setEditId(null);
        setForm({ name: "", description: "", rule_ids: [] });
        setShowForm(true);
    }

    async function openEdit(id: number) {
        const p = await profilesApi.get(id);
        setEditId(id);
        setForm({ name: p.name, description: p.description ?? "", rule_ids: p.rules.map((r) => r.id) });
        setShowForm(true);
    }

    async function handleSave() {
        setSaving(true);
        try {
            if (editId) {
                await profilesApi.update(editId, form);
            } else {
                await profilesApi.create(form);
            }
            await load();
            setShowForm(false);
        } catch (e) { alert("Save failed: " + e); }
        setSaving(false);
    }

    async function handleDelete(id: number) {
        if (!confirm("Delete this profile?")) return;
        await profilesApi.delete(id);
        await load();
    }

    function toggleRule(id: number) {
        setForm((f) => ({
            ...f,
            rule_ids: f.rule_ids.includes(id) ? f.rule_ids.filter((r) => r !== id) : [...f.rule_ids, id],
        }));
    }

    return (
        <div style={{ padding: 32, maxWidth: 900 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
                <div>
                    <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 4 }}>Profiles</h1>
                    <p style={{ color: "var(--text-muted)", margin: 0 }}>
                        Named collections of rules — run an entire profile as one audit
                    </p>
                </div>
                <button onClick={openCreate} style={primaryBtn}><Plus size={15} /> New Profile</button>
            </div>

            {loading ? (
                <div style={{ color: "var(--text-muted)" }}>Loading…</div>
            ) : profiles.length === 0 ? (
                <div style={{ textAlign: "center", padding: "48px 0", color: "var(--text-muted)" }}>
                    <FolderOpen size={40} style={{ marginBottom: 12 }} />
                    <p>No profiles yet. Create a profile to group rules together.</p>
                    <button onClick={openCreate} style={primaryBtn}><Plus size={14} /> Create First Profile</button>
                </div>
            ) : (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 14 }}>
                    {profiles.map((p) => (
                        <div key={p.id} style={card}>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                                <div style={{ fontWeight: 600, fontSize: 15 }}>{p.name}</div>
                                <div style={{ display: "flex", gap: 4 }}>
                                    <IconBtn onClick={() => openEdit(p.id)} title="Edit"><Pencil size={13} /></IconBtn>
                                    <IconBtn onClick={() => handleDelete(p.id)} title="Delete" danger><Trash2 size={13} /></IconBtn>
                                </div>
                            </div>
                            {p.description && <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>{p.description}</div>}
                            <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 10 }}>
                                {p.rule_count} rule{p.rule_count !== 1 ? "s" : ""}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {showForm && (
                <div style={overlayStyle}>
                    <div style={modalStyle}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
                            <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>{editId ? "Edit Profile" : "New Profile"}</h2>
                            <button onClick={() => setShowForm(false)} style={iconBtnStyle}><X size={18} /></button>
                        </div>

                        <label style={labelStyle}>Name *</label>
                        <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} style={inputStyle} placeholder="e.g. Sunday Service QA" />

                        <label style={{ ...labelStyle, marginTop: 12 }}>Description</label>
                        <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} style={inputStyle} placeholder="Optional" />

                        <div style={{ marginTop: 16 }}>
                            <label style={labelStyle}>Rules to include ({form.rule_ids.length} selected)</label>
                            {rules.length === 0 ? (
                                <p style={{ fontSize: 13, color: "var(--text-muted)" }}>No rules yet — create some on the Rules page first.</p>
                            ) : (
                                <div style={{ border: "1px solid var(--border)", borderRadius: 8, overflow: "hidden", marginTop: 6 }}>
                                    {rules.map((r, i) => (
                                        <label key={r.id} style={{
                                            display: "flex", alignItems: "center", gap: 10, padding: "10px 14px", cursor: "pointer",
                                            background: i % 2 === 0 ? "var(--surface-2)" : "transparent",
                                            borderBottom: i < rules.length - 1 ? "1px solid var(--border)" : "none",
                                        }}>
                                            <input type="checkbox" checked={form.rule_ids.includes(r.id)} onChange={() => toggleRule(r.id)} style={{ accentColor: "var(--accent)" }} />
                                            <span style={{ fontSize: 13 }}>{r.name}</span>
                                            <span style={{ marginLeft: "auto", fontSize: 11, color: "var(--text-muted)" }}>{r.target}</span>
                                        </label>
                                    ))}
                                </div>
                            )}
                        </div>

                        <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 20 }}>
                            <button onClick={() => setShowForm(false)} style={secondaryBtn}>Cancel</button>
                            <button onClick={handleSave} disabled={saving || !form.name} style={primaryBtn}>
                                <Check size={14} />{saving ? "Saving…" : "Save Profile"}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

function IconBtn({ onClick, title, danger, children }: { onClick: () => void; title?: string; danger?: boolean; children: React.ReactNode }) {
    return (
        <button title={title} onClick={onClick} style={{ background: "none", border: "none", cursor: "pointer", color: danger ? "var(--error)" : "var(--text-muted)", padding: 4, borderRadius: 4 }}>
            {children}
        </button>
    );
}

const card: React.CSSProperties = { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, padding: "16px 20px" };
const overlayStyle: React.CSSProperties = { position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100, padding: 20 };
const modalStyle: React.CSSProperties = { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 14, padding: 28, width: "100%", maxWidth: 520, maxHeight: "85vh", overflowY: "auto" };
const iconBtnStyle: React.CSSProperties = { background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)", padding: 4 };
const inputStyle: React.CSSProperties = { background: "var(--surface-2)", border: "1px solid var(--border)", borderRadius: 8, padding: "8px 12px", color: "var(--text)", fontSize: 13, width: "100%", outline: "none", marginTop: 4 };
const labelStyle: React.CSSProperties = { display: "block", fontSize: 12, fontWeight: 500, color: "var(--text-muted)" };
const primaryBtn: React.CSSProperties = { display: "flex", alignItems: "center", gap: 6, background: "var(--accent)", color: "#fff", border: "none", borderRadius: 8, padding: "9px 16px", cursor: "pointer", fontWeight: 600, fontSize: 13 };
const secondaryBtn: React.CSSProperties = { display: "flex", alignItems: "center", gap: 6, background: "var(--surface-2)", color: "var(--text)", border: "1px solid var(--border)", borderRadius: 8, padding: "9px 16px", cursor: "pointer", fontSize: 13 };
