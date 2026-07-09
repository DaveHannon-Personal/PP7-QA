/**
 * Rules management page — list, create (form), edit, delete QA rules.
 */
"use client";

import { useEffect, useState } from "react";
import { rulesApi, conflictsApi, type Rule, type RuleCreate, type Condition, type FixAction, type RuleConflict } from "@/lib/api";
import { Plus, Pencil, Trash2, AlertCircle, AlertTriangle, Info, X, Check } from "lucide-react";

const TARGETS = ["presentation", "slide", "look", "theme", "prop", "macro", "message"];
const OPERATORS = ["equals", "not_equals", "contains", "not_contains", "exists", "not_exists", "matches_regex"];
const FIX_TYPES = ["noop", "set_field", "trigger_look", "assign_theme"];
const SEVERITIES = ["error", "warning", "info"];

const emptyCondition = (): Condition => ({ field: "", operator: "equals", value: "" });
const emptyFix = (): FixAction => ({ type: "noop" });

function emptyForm(): RuleCreate {
    return {
        name: "",
        description: "",
        target: "presentation",
        severity: "error",
        condition: emptyCondition(),
        fix_action: emptyFix(),
    };
}

export default function RulesPage() {
    const [rules, setRules] = useState<Rule[]>([]);
    const [conflicts, setConflicts] = useState<RuleConflict[]>([]);
    const [conflictsAcknowledged, setConflictsAcknowledged] = useState(false);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [editRule, setEditRule] = useState<Rule | null>(null);
    const [form, setForm] = useState<RuleCreate>(emptyForm());
    const [saving, setSaving] = useState(false);

    async function load() {
        setLoading(true);
        try {
            const [r, c] = await Promise.all([rulesApi.list(), conflictsApi.getAll()]);
            setRules(r);
            setConflicts(c);
            // Reset acknowledgement whenever conflicts change
            setConflictsAcknowledged(false);
        } catch { }
        setLoading(false);
    }

    useEffect(() => { load(); }, []);

    function openCreate() {
        setEditRule(null);
        setForm(emptyForm());
        setShowForm(true);
    }

    function openEdit(rule: Rule) {
        setEditRule(rule);
        setForm({
            name: rule.name,
            description: rule.description ?? "",
            target: rule.target,
            severity: rule.severity,
            condition: rule.condition as Condition,
            fix_action: rule.fix_action as FixAction,
        });
        setShowForm(true);
    }

    async function handleSave() {
        setSaving(true);
        try {
            if (editRule) {
                await rulesApi.update(editRule.id, form);
            } else {
                await rulesApi.create(form);
            }
            await load();
            setShowForm(false);
        } catch (e) {
            alert("Save failed: " + e);
        }
        setSaving(false);
    }

    async function handleDelete(id: number) {
        if (!confirm("Delete this rule?")) return;
        await rulesApi.delete(id);
        await load();
    }

    return (
        <div style={{ padding: 32, maxWidth: 900 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
                <div>
                    <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 4 }}>QA Rules</h1>
                    <p style={{ color: "var(--text-muted)", margin: 0 }}>
                        {rules.length} rule{rules.length !== 1 ? "s" : ""} — define compliance checks for ProPresenter 7
                    </p>
                </div>
                <button onClick={openCreate} style={primaryBtn}>
                    <Plus size={15} /> New Rule
                </button>
            </div>

            {/* Conflict warning banner */}
            {!loading && conflicts.length > 0 && !conflictsAcknowledged && (
                <ConflictBanner
                    conflicts={conflicts}
                    onAcknowledge={() => setConflictsAcknowledged(true)}
                />
            )}
            {!loading && conflicts.length > 0 && conflictsAcknowledged && (
                <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "var(--warning)", marginBottom: 16, padding: "8px 14px", background: "rgba(245,158,11,0.08)", borderRadius: 8, border: "1px solid rgba(245,158,11,0.2)" }}>
                    <AlertTriangle size={13} />
                    {conflicts.length} conflict{conflicts.length !== 1 ? "s" : ""} acknowledged — last rule in sequence wins.
                    <button onClick={() => setConflictsAcknowledged(false)} style={{ marginLeft: "auto", background: "none", border: "none", cursor: "pointer", color: "var(--warning)", fontSize: 11, padding: 0 }}>Review</button>
                </div>
            )}

            {loading ? (
                <div style={{ color: "var(--text-muted)" }}>Loading…</div>
            ) : rules.length === 0 ? (
                <EmptyState onAdd={openCreate} />
            ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    {rules.map((rule) => (
                        <RuleCard key={rule.id} rule={rule} onEdit={() => openEdit(rule)} onDelete={() => handleDelete(rule.id)} conflictIds={new Set(conflicts.flatMap(c => [c.rule_a_id, c.rule_b_id]))} />
                    ))}
                </div>
            )}

            {showForm && (
                <RuleFormModal
                    form={form}
                    setForm={setForm}
                    onSave={handleSave}
                    onClose={() => setShowForm(false)}
                    saving={saving}
                    isEdit={!!editRule}
                />
            )}
        </div>
    );
}

function RuleCard({ rule, onEdit, onDelete, conflictIds }: { rule: Rule; onEdit: () => void; onDelete: () => void; conflictIds: Set<number> }) {
    const SeverityIcon = rule.severity === "error" ? AlertCircle : rule.severity === "warning" ? AlertTriangle : Info;
    const severityColor = rule.severity === "error" ? "var(--error)" : rule.severity === "warning" ? "var(--warning)" : "var(--info)";
    const hasConflict = conflictIds.has(rule.id);

    return (
        <div style={{ background: "var(--surface)", border: `1px solid ${hasConflict ? "rgba(245,158,11,0.4)" : "var(--border)"}`, borderRadius: 10, padding: "14px 18px", display: "flex", alignItems: "center", gap: 14 }}>
            <SeverityIcon size={16} color={severityColor} style={{ flexShrink: 0 }} />
            <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 600, fontSize: 14, display: "flex", alignItems: "center", gap: 8 }}>
                    {rule.name}
                    {hasConflict && (
                        <span title="This rule has a duplicate or contradiction with another rule" style={{ fontSize: 10, background: "rgba(245,158,11,0.15)", color: "var(--warning)", borderRadius: 4, padding: "2px 6px", fontWeight: 500 }}>
                            ⚠ conflict
                        </span>
                    )}
                </div>
                {rule.description && <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>{rule.description}</div>}
                <div style={{ display: "flex", gap: 8, marginTop: 6, flexWrap: "wrap" }}>
                    <Badge label={rule.target} />
                    <Badge label={`${rule.condition.operator} "${rule.condition.value ?? "—"}"`} dimmed />
                    {rule.fix_action?.type !== "noop" && <Badge label={`fix: ${rule.fix_action.type}`} accent />}
                </div>
            </div>
            <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
                <IconBtn onClick={onEdit} title="Edit"><Pencil size={14} /></IconBtn>
                <IconBtn onClick={onDelete} title="Delete" danger><Trash2 size={14} /></IconBtn>
            </div>
        </div>
    );
}

function ConflictBanner({ conflicts, onAcknowledge }: { conflicts: RuleConflict[]; onAcknowledge: () => void }) {
    const dupes = conflicts.filter(c => c.conflict_type === "duplicate");
    const contradictions = conflicts.filter(c => c.conflict_type === "contradiction");

    return (
        <div style={{ background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.35)", borderRadius: 12, padding: "16px 20px", marginBottom: 20 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                <AlertTriangle size={16} color="var(--warning)" />
                <span style={{ fontWeight: 600, fontSize: 14, color: "var(--warning)" }}>
                    {conflicts.length} Rule Conflict{conflicts.length !== 1 ? "s" : ""} Detected
                </span>
            </div>
            <div style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 14, lineHeight: 1.5 }}>
                Rules run sequentially. When two rules target the same field on the same item,{" "}
                <strong style={{ color: "var(--text)" }}>the last rule in the sequence wins</strong> for auto-fix actions.
                Both results will still appear in audit reports.
            </div>
            {dupes.length > 0 && (
                <div style={{ marginBottom: 10 }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)", marginBottom: 6 }}>Duplicates ({dupes.length})</div>
                    {dupes.map((c, i) => (
                        <div key={i} style={{ fontSize: 12, color: "var(--text)", marginBottom: 4, paddingLeft: 10, borderLeft: "2px solid rgba(245,158,11,0.4)" }}>
                            <strong>"{c.rule_a_name}"</strong> and <strong>"{c.rule_b_name}"</strong>
                            <span style={{ color: "var(--text-muted)" }}> — {c.description}</span>
                        </div>
                    ))}
                </div>
            )}
            {contradictions.length > 0 && (
                <div style={{ marginBottom: 14 }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)", marginBottom: 6 }}>Contradictions ({contradictions.length})</div>
                    {contradictions.map((c, i) => (
                        <div key={i} style={{ fontSize: 12, color: "var(--text)", marginBottom: 4, paddingLeft: 10, borderLeft: "2px solid rgba(239,68,68,0.4)" }}>
                            <strong>"{c.rule_a_name}"</strong> vs <strong>"{c.rule_b_name}"</strong>
                            <span style={{ color: "var(--text-muted)" }}> — {c.description}</span>
                        </div>
                    ))}
                </div>
            )}
            <button
                onClick={onAcknowledge}
                style={{ background: "var(--warning)", color: "#000", border: "none", borderRadius: 8, padding: "8px 16px", cursor: "pointer", fontWeight: 600, fontSize: 13 }}
            >
                Acknowledge &amp; Continue
            </button>
        </div>
    );
}

function RuleFormModal({ form, setForm, onSave, onClose, saving, isEdit }: {
    form: RuleCreate;
    setForm: (f: RuleCreate) => void;
    onSave: () => void;
    onClose: () => void;
    saving: boolean;
    isEdit: boolean;
}) {
    function setCondition(patch: Partial<Condition>) {
        setForm({ ...form, condition: { ...form.condition!, ...patch } });
    }
    function setFix(patch: Partial<FixAction>) {
        setForm({ ...form, fix_action: { ...form.fix_action!, ...patch } });
    }

    return (
        <div style={overlay}>
            <div style={modal}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
                    <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>{isEdit ? "Edit Rule" : "New Rule"}</h2>
                    <button onClick={onClose} style={iconBtn}><X size={18} /></button>
                </div>

                <FormField label="Name *">
                    <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} style={input} placeholder="e.g. All presentations must use Main Look" />
                </FormField>
                <FormField label="Description">
                    <input value={form.description ?? ""} onChange={(e) => setForm({ ...form, description: e.target.value })} style={input} placeholder="Optional" />
                </FormField>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                    <FormField label="Target">
                        <Select value={form.target} onChange={(v) => setForm({ ...form, target: v })} options={TARGETS} />
                    </FormField>
                    <FormField label="Severity">
                        <Select value={form.severity!} onChange={(v) => setForm({ ...form, severity: v })} options={SEVERITIES} />
                    </FormField>
                </div>

                <div style={{ borderTop: "1px solid var(--border)", marginTop: 4, paddingTop: 16, marginBottom: 4 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Condition</div>
                    <FormField label="Field (dot notation)">
                        <input value={form.condition?.field ?? ""} onChange={(e) => setCondition({ field: e.target.value })} style={input} placeholder="e.g. presentation.name or theme.name.string" />
                    </FormField>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                        <FormField label="Operator">
                            <Select value={form.condition?.operator ?? "equals"} onChange={(v) => setCondition({ operator: v })} options={OPERATORS} />
                        </FormField>
                        <FormField label="Value">
                            <input value={form.condition?.value != null ? String(form.condition.value) : ""} onChange={(e) => setCondition({ value: e.target.value })} style={input} placeholder='e.g. "Main Theme" or leave blank for exists/not_exists' />
                        </FormField>
                    </div>
                </div>

                <div style={{ borderTop: "1px solid var(--border)", marginTop: 4, paddingTop: 16, marginBottom: 16 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Auto-Fix Action</div>
                    <FormField label="Fix Type">
                        <Select value={form.fix_action?.type ?? "noop"} onChange={(v) => setFix({ type: v })} options={FIX_TYPES} />
                    </FormField>
                    {form.fix_action?.type === "set_field" && (
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                            <FormField label="Field to Set">
                                <input value={form.fix_action.field ?? ""} onChange={(e) => setFix({ field: e.target.value })} style={input} placeholder="dot.notation.field" />
                            </FormField>
                            <FormField label="New Value">
                                <input value={form.fix_action.value != null ? String(form.fix_action.value) : ""} onChange={(e) => setFix({ value: e.target.value })} style={input} placeholder="value" />
                            </FormField>
                        </div>
                    )}
                    {form.fix_action?.type === "trigger_look" && (
                        <FormField label="Look ID (leave blank to use item ID)">
                            <input value={form.fix_action.value != null ? String(form.fix_action.value) : ""} onChange={(e) => setFix({ value: e.target.value })} style={input} placeholder="look UUID" />
                        </FormField>
                    )}
                </div>

                <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
                    <button onClick={onClose} style={secondaryBtn}>Cancel</button>
                    <button onClick={onSave} disabled={saving || !form.name} style={primaryBtn}>
                        <Check size={14} />{saving ? "Saving…" : "Save Rule"}
                    </button>
                </div>
            </div>
        </div>
    );
}

function EmptyState({ onAdd }: { onAdd: () => void }) {
    return (
        <div style={{ textAlign: "center", padding: "48px 0", color: "var(--text-muted)" }}>
            <ListChecksIcon />
            <p style={{ marginBottom: 16 }}>No rules yet. Create your first QA rule or use the AI Chat to generate one.</p>
            <button onClick={onAdd} style={primaryBtn}><Plus size={14} /> Create First Rule</button>
        </div>
    );
}
function ListChecksIcon() {
    return <div style={{ fontSize: 48, marginBottom: 12 }}>✓</div>;
}

function Badge({ label, dimmed, accent }: { label: string; dimmed?: boolean; accent?: boolean }) {
    return (
        <span style={{
            background: accent ? "rgba(99,102,241,0.15)" : "var(--surface-2)",
            color: accent ? "var(--accent)" : dimmed ? "var(--text-muted)" : "var(--text)",
            borderRadius: 5,
            padding: "2px 7px",
            fontSize: 11,
            fontWeight: 500,
        }}>{label}</span>
    );
}

function IconBtn({ onClick, title, danger, children }: { onClick: () => void; title?: string; danger?: boolean; children: React.ReactNode }) {
    return (
        <button title={title} onClick={onClick} style={{ background: "none", border: "none", cursor: "pointer", color: danger ? "var(--error)" : "var(--text-muted)", padding: 4, borderRadius: 4 }}>
            {children}
        </button>
    );
}

function FormField({ label, children }: { label: string; children: React.ReactNode }) {
    return (
        <div style={{ marginBottom: 12 }}>
            <label style={{ display: "block", fontSize: 12, fontWeight: 500, marginBottom: 5, color: "var(--text-muted)" }}>{label}</label>
            {children}
        </div>
    );
}

function Select({ value, onChange, options }: { value: string; onChange: (v: string) => void; options: string[] }) {
    return (
        <select value={value} onChange={(e) => onChange(e.target.value)} style={input}>
            {options.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
    );
}

const input: React.CSSProperties = { background: "var(--surface-2)", border: "1px solid var(--border)", borderRadius: 8, padding: "8px 12px", color: "var(--text)", fontSize: 13, width: "100%", outline: "none" };
const overlay: React.CSSProperties = { position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100, padding: 20 };
const modal: React.CSSProperties = { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 14, padding: 28, width: "100%", maxWidth: 560, maxHeight: "90vh", overflowY: "auto" };
const iconBtn: React.CSSProperties = { background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)", padding: 4 };
const primaryBtn: React.CSSProperties = { display: "flex", alignItems: "center", gap: 6, background: "var(--accent)", color: "#fff", border: "none", borderRadius: 8, padding: "9px 16px", cursor: "pointer", fontWeight: 600, fontSize: 13 };
const secondaryBtn: React.CSSProperties = { display: "flex", alignItems: "center", gap: 6, background: "var(--surface-2)", color: "var(--text)", border: "1px solid var(--border)", borderRadius: 8, padding: "9px 16px", cursor: "pointer", fontSize: 13 };
