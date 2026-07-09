/**
 * Audit page — run compliance checks, view results, apply fixes, iterate.
 */
"use client";

import { useEffect, useState } from "react";
import { auditApi, profilesApi, rulesApi, conflictsApi, type AuditReport, type AuditResultItem, type ProfileSummary, type Rule, type RuleConflict } from "@/lib/api";
import { Play, Wrench, RefreshCw, CheckCircle2, XCircle, SkipForward, AlertCircle, AlertTriangle, X } from "lucide-react";

type RunMode = "profile" | "all" | "custom";

export default function AuditPage() {
    const [profiles, setProfiles] = useState<ProfileSummary[]>([]);
    const [rules, setRules] = useState<Rule[]>([]);
    const [mode, setMode] = useState<RunMode>("all");
    const [selectedProfile, setSelectedProfile] = useState<number | null>(null);
    const [selectedRuleIds, setSelectedRuleIds] = useState<number[]>([]);
    const [report, setReport] = useState<AuditReport | null>(null);
    const [running, setRunning] = useState(false);
    const [fixing, setFixing] = useState(false);
    const [selectedFixes, setSelectedFixes] = useState<Set<string>>(new Set());
    const [fixLog, setFixLog] = useState<string[]>([]);
    // Conflict acknowledgement state
    const [pendingConflicts, setPendingConflicts] = useState<RuleConflict[] | null>(null);

    useEffect(() => {
        Promise.all([profilesApi.list(), rulesApi.list()]).then(([p, r]) => {
            setProfiles(p);
            setRules(r);
            if (p.length > 0) { setSelectedProfile(p[0].id); setMode("profile"); }
        });
    }, []);

    /** Resolve current rule IDs based on selected mode */
    function getCurrentRuleIds(): number[] {
        if (mode === "profile" && selectedProfile) {
            const profile = profiles.find(p => p.id === selectedProfile);
            // We don't have full rule list here; pass empty to let backend resolve
            return [];
        }
        if (mode === "custom") return selectedRuleIds;
        return rules.map(r => r.id);
    }

    /** Initiate audit — check for conflicts first, show modal if any */
    async function initiateAudit() {
        // Fetch conflicts for the current scope
        try {
            let conflicts: RuleConflict[];
            if (mode === "profile" && selectedProfile) {
                const profile = await profilesApi.get(selectedProfile);
                const ids = profile.rules.map(r => r.id);
                conflicts = ids.length > 0 ? await conflictsApi.checkIds(ids) : [];
            } else if (mode === "custom") {
                conflicts = selectedRuleIds.length > 0 ? await conflictsApi.checkIds(selectedRuleIds) : [];
            } else {
                conflicts = await conflictsApi.getAll();
            }

            if (conflicts.length > 0) {
                setPendingConflicts(conflicts);
            } else {
                await runAudit();
            }
        } catch {
            // If conflict check fails, proceed with audit anyway
            await runAudit();
        }
    }

    async function runAudit() {
        setPendingConflicts(null);
        setRunning(true);
        setReport(null);
        setSelectedFixes(new Set());
        setFixLog([]);
        try {
            const payload =
                mode === "profile" && selectedProfile
                    ? { profile_id: selectedProfile }
                    : mode === "custom"
                        ? { rule_ids: selectedRuleIds }
                        : {};
            setReport(await auditApi.run(payload));
        } catch (e) { alert("Audit failed: " + e); }
        setRunning(false);
    }

    async function applyFixes() {
        if (!report) return;
        setFixing(true);
        const ids = selectedFixes.size === 0 ? ["all"] : Array.from(selectedFixes);
        try {
            const result = await auditApi.fix(ids);
            setFixLog(result.details.map((d) => `${d.status.toUpperCase()} — ${d.item_name}: ${d.message}`));
            // Re-run audit after fixing
            const payload =
                mode === "profile" && selectedProfile
                    ? { profile_id: selectedProfile }
                    : mode === "custom"
                        ? { rule_ids: selectedRuleIds }
                        : {};
            setReport(await auditApi.run(payload));
            setSelectedFixes(new Set());
        } catch (e) { alert("Fix failed: " + e); }
        setFixing(false);
    }

    const failedItems = report?.results.filter((r) => r.status === "fail") ?? [];
    const fixableCount = failedItems.filter((r) => r.fix_available).length;

    return (
        <div style={{ padding: 32, maxWidth: 1000 }}>
            <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 6 }}>Audit</h1>
            <p style={{ color: "var(--text-muted)", marginBottom: 28 }}>
                Check your ProPresenter 7 presentations for compliance violations
            </p>

            {/* Conflict acknowledgement modal */}
            {pendingConflicts && (
                <AuditConflictModal
                    conflicts={pendingConflicts}
                    onAcknowledge={runAudit}
                    onCancel={() => setPendingConflicts(null)}
                />
            )}

            {/* Run configuration */}
            <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, padding: "20px 24px", marginBottom: 24 }}>
                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 14 }}>Audit scope</div>
                <div style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
                    {(["all", "profile", "custom"] as RunMode[]).map((m) => (
                        <button key={m} onClick={() => setMode(m)} style={mode === m ? activeTab : tab}>
                            {m === "all" ? "All rules" : m === "profile" ? "Profile" : "Custom selection"}
                        </button>
                    ))}
                </div>

                {mode === "profile" && (
                    <select value={selectedProfile ?? ""} onChange={(e) => setSelectedProfile(Number(e.target.value))} style={selectStyle}>
                        {profiles.length === 0 ? <option value="">No profiles — create one first</option> : profiles.map((p) => <option key={p.id} value={p.id}>{p.name} ({p.rule_count} rules)</option>)}
                    </select>
                )}

                {mode === "custom" && (
                    <div style={{ border: "1px solid var(--border)", borderRadius: 8, overflow: "hidden" }}>
                        {rules.map((r, i) => (
                            <label key={r.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "9px 14px", cursor: "pointer", background: i % 2 === 0 ? "var(--surface-2)" : "transparent", borderBottom: i < rules.length - 1 ? "1px solid var(--border)" : "none" }}>
                                <input type="checkbox" checked={selectedRuleIds.includes(r.id)} onChange={() => setSelectedRuleIds((prev) => prev.includes(r.id) ? prev.filter((x) => x !== r.id) : [...prev, r.id])} style={{ accentColor: "var(--accent)" }} />
                                <span style={{ fontSize: 13 }}>{r.name}</span>
                            </label>
                        ))}
                    </div>
                )}

                <div style={{ marginTop: 16 }}>
                    <button onClick={initiateAudit} disabled={running} style={primaryBtn}>
                        <Play size={14} />{running ? "Running audit…" : "Run Audit"}
                    </button>
                </div>
            </div>

            {/* Results */}
            {report && (
                <>
                    <SummaryBar report={report} />

                    {fixLog.length > 0 && (
                        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, padding: "14px 18px", marginBottom: 16 }}>
                            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8 }}>Fix Results</div>
                            {fixLog.map((l, i) => <div key={i} style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 3 }}>{l}</div>)}
                        </div>
                    )}

                    {failedItems.length > 0 && (
                        <div style={{ display: "flex", gap: 10, marginBottom: 16, alignItems: "center" }}>
                            <button
                                onClick={applyFixes}
                                disabled={fixing || fixableCount === 0}
                                style={fixing || fixableCount === 0 ? { ...primaryBtn, opacity: 0.5, cursor: "not-allowed" } : primaryBtn}
                            >
                                <Wrench size={14} />
                                {fixing ? "Fixing…" : selectedFixes.size > 0 ? `Fix ${selectedFixes.size} selected` : `Fix All (${fixableCount} fixable)`}
                            </button>
                            <button onClick={initiateAudit} disabled={running} style={secondaryBtn}>
                                <RefreshCw size={14} />Re-run Audit
                            </button>
                            {selectedFixes.size > 0 && (
                                <button onClick={() => setSelectedFixes(new Set())} style={ghostBtn}>Clear selection</button>
                            )}
                        </div>
                    )}

                    <ResultsTable
                        results={report.results}
                        selectedFixes={selectedFixes}
                        onToggleFix={(id) => setSelectedFixes((prev) => {
                            const next = new Set(prev);
                            next.has(id) ? next.delete(id) : next.add(id);
                            return next;
                        })}
                    />

                    {/* Conflict summary from this audit run */}
                    {report.conflicts.length > 0 && (
                        <div style={{ marginTop: 20, background: "rgba(245,158,11,0.07)", border: "1px solid rgba(245,158,11,0.25)", borderRadius: 10, padding: "14px 18px" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                                <AlertTriangle size={14} color="var(--warning)" />
                                <span style={{ fontWeight: 600, fontSize: 13, color: "var(--warning)" }}>
                                    {report.conflicts.length} conflict{report.conflicts.length !== 1 ? "s" : ""} in this rule set
                                </span>
                            </div>
                            <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 10 }}>
                                Superseded results are marked in the table above. Last rule in sequence wins for fixes.
                            </div>
                            {report.conflicts.map((c, i) => (
                                <div key={i} style={{ fontSize: 12, color: "var(--text)", marginBottom: 4, paddingLeft: 10, borderLeft: `2px solid ${c.conflict_type === "duplicate" ? "rgba(245,158,11,0.5)" : "rgba(239,68,68,0.5)"}` }}>
                                    <span style={{ background: c.conflict_type === "duplicate" ? "rgba(245,158,11,0.15)" : "rgba(239,68,68,0.15)", color: c.conflict_type === "duplicate" ? "var(--warning)" : "var(--error)", borderRadius: 3, padding: "1px 5px", marginRight: 6, fontSize: 10, fontWeight: 600 }}>
                                        {c.conflict_type}
                                    </span>
                                    <strong>{c.rule_a_name}</strong> — <strong>{c.rule_b_name}</strong>
                                    <span style={{ color: "var(--text-muted)" }}> ({c.field})</span>
                                </div>
                            ))}
                        </div>
                    )}
                </>
            )}
        </div>
    );
}

function SummaryBar({ report }: { report: AuditReport }) {
    const pct = report.total_items_checked > 0
        ? Math.round((report.pass_count / report.total_items_checked) * 100)
        : 0;

    return (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 20 }}>
            {[
                { label: "Total checked", value: report.total_items_checked, color: "var(--text)" },
                { label: "Passed", value: report.pass_count, color: "var(--success)" },
                { label: "Failed", value: report.fail_count, color: "var(--error)" },
                { label: "Compliance", value: `${pct}%`, color: pct === 100 ? "var(--success)" : pct >= 75 ? "var(--warning)" : "var(--error)" },
            ].map(({ label, value, color }) => (
                <div key={label} style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, padding: "16px 20px" }}>
                    <div style={{ fontSize: 22, fontWeight: 700, color }}>{value}</div>
                    <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>{label}</div>
                </div>
            ))}
        </div>
    );
}

function ResultsTable({ results, selectedFixes, onToggleFix }: {
    results: AuditResultItem[];
    selectedFixes: Set<string>;
    onToggleFix: (id: string) => void;
}) {
    const [filter, setFilter] = useState<"all" | "pass" | "fail">("all");
    const filtered = filter === "all" ? results : results.filter((r) => r.status === filter);

    return (
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, overflow: "hidden" }}>
            {/* Filter tabs */}
            <div style={{ display: "flex", gap: 0, borderBottom: "1px solid var(--border)", padding: "0 16px" }}>
                {(["all", "pass", "fail"] as const).map((f) => (
                    <button key={f} onClick={() => setFilter(f)} style={{ background: "none", border: "none", cursor: "pointer", padding: "12px 14px", fontSize: 13, color: filter === f ? "var(--accent)" : "var(--text-muted)", borderBottom: filter === f ? "2px solid var(--accent)" : "2px solid transparent", fontWeight: filter === f ? 600 : 400 }}>
                        {f === "all" ? `All (${results.length})` : f === "pass" ? `Pass (${results.filter((r) => r.status === "pass").length})` : `Fail (${results.filter((r) => r.status === "fail").length})`}
                    </button>
                ))}
            </div>

            {filtered.length === 0 ? (
                <div style={{ padding: "32px", textAlign: "center", color: "var(--text-muted)", fontSize: 14 }}>No items to show</div>
            ) : (
                filtered.map((result, i) => (
                    <ResultRow key={`${result.item_id}-${result.rule_id}`} result={result} isLast={i === filtered.length - 1} selected={selectedFixes.has(result.item_id)} onToggle={() => result.fix_available && onToggleFix(result.item_id)} />
                ))
            )}
        </div>
    );
}

function ResultRow({ result, isLast, selected, onToggle }: { result: AuditResultItem; isLast: boolean; selected: boolean; onToggle: () => void }) {
    const StatusIcon = result.status === "pass" ? CheckCircle2 : result.status === "fail" ? XCircle : SkipForward;
    const color = result.status === "pass" ? "var(--success)" : result.status === "fail" ? "var(--error)" : "var(--text-muted)";

    return (
        <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 16px", borderBottom: isLast ? "none" : "1px solid var(--border)", background: selected ? "rgba(99,102,241,0.06)" : "transparent" }}>
            {result.status === "fail" && result.fix_available && (
                <input type="checkbox" checked={selected} onChange={onToggle} style={{ accentColor: "var(--accent)", flexShrink: 0 }} />
            )}
            {!(result.status === "fail" && result.fix_available) && <div style={{ width: 16, flexShrink: 0 }} />}
            <StatusIcon size={15} color={color} style={{ flexShrink: 0 }} />
            <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 500, fontSize: 13, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{result.item_name}</div>
                <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>{result.details}</div>
            </div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", flexShrink: 0, textAlign: "right" }}>
                <div>{result.rule_name}</div>
                <div style={{ marginTop: 1 }}>{result.item_type}</div>
            </div>
            {result.status === "fail" && !result.fix_available && (
                <span style={{ fontSize: 10, background: "rgba(239,68,68,0.1)", color: "var(--error)", borderRadius: 4, padding: "2px 6px", flexShrink: 0 }}>manual fix</span>
            )}
        </div>
    );
}

const primaryBtn: React.CSSProperties = { display: "flex", alignItems: "center", gap: 6, background: "var(--accent)", color: "#fff", border: "none", borderRadius: 8, padding: "9px 16px", cursor: "pointer", fontWeight: 600, fontSize: 13 };
const secondaryBtn: React.CSSProperties = { display: "flex", alignItems: "center", gap: 6, background: "var(--surface-2)", color: "var(--text)", border: "1px solid var(--border)", borderRadius: 8, padding: "9px 16px", cursor: "pointer", fontSize: 13 };
const ghostBtn: React.CSSProperties = { background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: 12, padding: "4px 8px" };
const tab: React.CSSProperties = { background: "var(--surface-2)", border: "1px solid var(--border)", borderRadius: 8, padding: "7px 14px", cursor: "pointer", fontSize: 13, color: "var(--text-muted)" };
const activeTab: React.CSSProperties = { ...tab, background: "rgba(99,102,241,0.15)", borderColor: "var(--accent)", color: "var(--accent)", fontWeight: 600 };
const selectStyle: React.CSSProperties = { background: "var(--surface-2)", border: "1px solid var(--border)", borderRadius: 8, padding: "8px 12px", color: "var(--text)", fontSize: 13, width: "100%", outline: "none" };

function AuditConflictModal({ conflicts, onAcknowledge, onCancel }: {
    conflicts: RuleConflict[];
    onAcknowledge: () => void;
    onCancel: () => void;
}) {
    const dupes = conflicts.filter(c => c.conflict_type === "duplicate");
    const contradictions = conflicts.filter(c => c.conflict_type === "contradiction");

    return (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 200, padding: 20 }}>
            <div style={{ background: "var(--surface)", border: "1px solid rgba(245,158,11,0.4)", borderRadius: 14, padding: 28, width: "100%", maxWidth: 520, maxHeight: "85vh", overflowY: "auto" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <AlertTriangle size={20} color="var(--warning)" />
                        <span style={{ fontWeight: 700, fontSize: 17 }}>Rule Conflicts Detected</span>
                    </div>
                    <button onClick={onCancel} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)", padding: 2 }}><X size={18} /></button>
                </div>

                <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 16, lineHeight: 1.6 }}>
                    The selected rules contain <strong style={{ color: "var(--text)" }}>{conflicts.length} conflict{conflicts.length !== 1 ? "s" : ""}</strong>.
                    You can acknowledge and continue — rules will run sequentially and{" "}
                    <strong style={{ color: "var(--warning)" }}>the last rule in the sequence wins</strong> when two rules
                    target the same field on the same item.
                </p>

                {dupes.length > 0 && (
                    <div style={{ marginBottom: 14 }}>
                        <div style={{ fontSize: 12, fontWeight: 600, color: "var(--warning)", marginBottom: 8 }}>
                            Duplicates — {dupes.length} redundant check{dupes.length !== 1 ? "s" : ""}
                        </div>
                        {dupes.map((c, i) => (
                            <div key={i} style={{ fontSize: 12, background: "var(--surface-2)", borderRadius: 6, padding: "8px 12px", marginBottom: 6 }}>
                                <div><strong>{c.rule_a_name}</strong> and <strong>{c.rule_b_name}</strong></div>
                                <div style={{ color: "var(--text-muted)", marginTop: 3 }}>{c.description}</div>
                            </div>
                        ))}
                    </div>
                )}

                {contradictions.length > 0 && (
                    <div style={{ marginBottom: 16 }}>
                        <div style={{ fontSize: 12, fontWeight: 600, color: "var(--error)", marginBottom: 8 }}>
                            Contradictions — {contradictions.length} mutually exclusive check{contradictions.length !== 1 ? "s" : ""}
                        </div>
                        {contradictions.map((c, i) => (
                            <div key={i} style={{ fontSize: 12, background: "var(--surface-2)", borderRadius: 6, padding: "8px 12px", marginBottom: 6 }}>
                                <div><strong>{c.rule_a_name}</strong> vs <strong>{c.rule_b_name}</strong></div>
                                <div style={{ color: "var(--text-muted)", marginTop: 3 }}>{c.description}</div>
                            </div>
                        ))}
                    </div>
                )}

                <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
                    <button onClick={onCancel} style={secondaryBtn}>Cancel</button>
                    <button
                        onClick={onAcknowledge}
                        style={{ display: "flex", alignItems: "center", gap: 6, background: "var(--warning)", color: "#000", border: "none", borderRadius: 8, padding: "9px 16px", cursor: "pointer", fontWeight: 700, fontSize: 13 }}
                    >
                        <Play size={13} /> Acknowledge &amp; Run Audit
                    </button>
                </div>
            </div>
        </div>
    );
}
