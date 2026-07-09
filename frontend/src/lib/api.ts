/**
 * Shared API client utility.
 * All requests go through /api (proxied to FastAPI by next.config.ts).
 */

const API = process.env.NEXT_PUBLIC_API_URL || "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const res = await fetch(`${API}${path}`, {
        headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
        ...init,
    });
    if (!res.ok) {
        const text = await res.text();
        throw new Error(`API error ${res.status}: ${text}`);
    }
    return res.json() as Promise<T>;
}

// ── Settings ─────────────────────────────────────────────────────────────────

export interface AppConfig {
    propresenter_url: string;
    propresenter_port: number;
    ollama_url: string;
    ollama_model: string;
}

export interface ConnectionStatus {
    propresenter_connected: boolean;
    propresenter_version: string | null;
    ollama_connected: boolean;
    ollama_models: string[];
}

export const settingsApi = {
    get: () => request<AppConfig>("/api/settings"),
    update: (data: Partial<AppConfig>) =>
        request<AppConfig>("/api/settings", { method: "PUT", body: JSON.stringify(data) }),
    status: () => request<ConnectionStatus>("/api/settings/status"),
};

// ── Rules ────────────────────────────────────────────────────────────────────

export interface Condition {
    field: string;
    operator: string;
    value: string | number | boolean | null;
}

export interface FixAction {
    type: string;
    field?: string;
    value?: string | number | boolean | null;
}

export interface Rule {
    id: number;
    name: string;
    description: string | null;
    target: string;
    severity: string;
    condition: Condition;
    fix_action: FixAction;
    created_at: string;
    updated_at: string;
}

export interface RuleCreate {
    name: string;
    description?: string;
    target: string;
    severity?: string;
    condition: Condition;
    fix_action?: FixAction;
}

export const rulesApi = {
    list: () => request<Rule[]>("/api/rules"),
    get: (id: number) => request<Rule>(`/api/rules/${id}`),
    create: (data: RuleCreate) =>
        request<Rule>("/api/rules", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: Partial<RuleCreate>) =>
        request<Rule>(`/api/rules/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (id: number) =>
        fetch(`${API}/api/rules/${id}`, { method: "DELETE" }),
};

// ── Rule Conflicts ────────────────────────────────────────────────────────────

export interface RuleConflict {
    conflict_type: "duplicate" | "contradiction";
    rule_a_id: number;
    rule_a_name: string;
    rule_b_id: number;
    rule_b_name: string;
    target: string;
    field: string;
    description: string;
}

export const conflictsApi = {
    /** All conflicts across every rule in the library */
    getAll: () => request<RuleConflict[]>("/api/rules/conflicts"),
    /** Conflicts for a specific ordered list of rule IDs (e.g. a profile) */
    checkIds: (rule_ids: number[]) =>
        request<RuleConflict[]>("/api/rules/conflicts/check", {
            method: "POST",
            body: JSON.stringify(rule_ids),
        }),
};

// ── Profiles ─────────────────────────────────────────────────────────────────

export interface ProfileSummary {
    id: number;
    name: string;
    description: string | null;
    rule_count: number;
    created_at: string;
}

export interface Profile {
    id: number;
    name: string;
    description: string | null;
    rules: Rule[];
    created_at: string;
    updated_at: string;
}

export const profilesApi = {
    list: () => request<ProfileSummary[]>("/api/profiles"),
    get: (id: number) => request<Profile>(`/api/profiles/${id}`),
    create: (data: { name: string; description?: string; rule_ids?: number[] }) =>
        request<Profile>("/api/profiles", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: { name?: string; description?: string; rule_ids?: number[] }) =>
        request<Profile>(`/api/profiles/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (id: number) => fetch(`${API}/api/profiles/${id}`, { method: "DELETE" }),
};

// ── Audit ────────────────────────────────────────────────────────────────────

export interface AuditResultItem {
    item_id: string;
    item_name: string;
    item_type: string;
    rule_id: number;
    rule_name: string;
    status: "pass" | "fail" | "skipped";
    details: string;
    fix_available: boolean;
}

export interface AuditReport {
    profile_id: number | null;
    profile_name: string | null;
    total_items_checked: number;
    pass_count: number;
    fail_count: number;
    skip_count: number;
    results: AuditResultItem[];
    conflicts: RuleConflict[];
}

export interface FixResponse {
    fixed_count: number;
    failed_count: number;
    details: Array<{ item_id: string; item_name: string; status: string; message: string }>;
}

export const auditApi = {
    run: (data: { profile_id?: number; rule_ids?: number[] }) =>
        request<AuditReport>("/api/audit/run", { method: "POST", body: JSON.stringify(data) }),
    fix: (result_ids: string[]) =>
        request<FixResponse>("/api/audit/fix", {
            method: "POST",
            body: JSON.stringify({ result_ids }),
        }),
    runAndFix: (data: { profile_id?: number; rule_ids?: number[] }) =>
        request<AuditReport>("/api/audit/run-and-fix", { method: "POST", body: JSON.stringify(data) }),
};
