const API_BASE = "/api";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  if (res.headers.get("content-type")?.includes("application/json")) {
    return res.json();
  }
  return res as unknown as T;
}

export const api = {
  login: (username: string, password: string) =>
    request<{ user: User }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  logout: () => request("/auth/logout", { method: "POST" }),
  me: () => request<{ user: User; admin_ready: boolean }>("/auth/me"),
  setupStatus: () => request<{ has_admin: boolean }>("/setup-status"),
  parse: (payload: Record<string, unknown>) =>
    request<CalcResult>("/parse", { method: "POST", body: JSON.stringify(payload) }),
  calculate: (payload: Record<string, unknown>) =>
    request<CalcResult>("/calculate", { method: "POST", body: JSON.stringify(payload) }),
  createJob: (payload: Record<string, unknown>) =>
    request<{ job: Job; result: CalcResult }>("/jobs", { method: "POST", body: JSON.stringify(payload) }),
  listJobs: () => request<Job[]>("/jobs"),
  getJob: (id: number) => request<JobDetail>(`/jobs/${id}`),
  updateJob: (id: number, payload: Record<string, unknown>) =>
    request<JobDetail>(`/jobs/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  exportJob: async (id: number, payload: Record<string, unknown>) => {
    const res = await fetch(`${API_BASE}/jobs/${id}/export`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Export failed");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `appendix_job${id}.xlsx`;
    a.click();
    URL.revokeObjectURL(url);
  },
  listMaterials: () => request<Material[]>("/materials"),
  listProfiles: () => request<Profile[]>("/profiles"),
  catalogSyncStatus: () => request<CatalogSyncStatus>("/catalog/sync-status"),
  catalogSync: () => request<CatalogSyncStatus>("/catalog/sync", { method: "POST" }),
  listUsers: () => request<User[]>("/users"),
  createUser: (payload: Record<string, unknown>) =>
    request<User>("/users", { method: "POST", body: JSON.stringify(payload) }),
};

export interface User {
  id: number;
  username: string;
  email: string;
  role: string;
  active: boolean;
}

export interface LineItem {
  line_id: number;
  raw: string;
  description: string;
  output_description: string;
  quantity: number | null;
  unit: string | null;
  material: string | null;
  product_type: string | null;
  weight_each_kg: number | null;
  weight_total_kg: number | null;
  material_volume_m3: number | null;
  transport_volume_m3: number | null;
  length_cm: number | null;
  width_cm: number | null;
  height_cm: number | null;
  status: string;
  messages: string[];
  include: boolean;
}

export interface CalcResult {
  success: boolean;
  column_map: Record<string, number | null>;
  lines: LineItem[];
  totals: Record<string, number>;
  errors: unknown[];
}

export interface Job {
  id: number;
  title: string;
  status: string;
  totals?: Record<string, number>;
  created_at?: string;
}

export interface JobDetail extends Job {
  input_raw?: string;
  calculated?: CalcResult;
  metadata?: Record<string, unknown>;
}

export interface Material {
  id: number;
  canonical_name: string;
  category: string;
  density_kg_m3: number;
  language_labels?: Record<string, string>;
  source?: string | null;
}

export interface Profile {
  id: number;
  profile_type: string;
  size_label: string;
  kg_per_meter: number;
  standard?: string | null;
  source?: string | null;
}

export interface CatalogSyncStatus {
  last_run_at: string | null;
  success: boolean | null;
  profiles_added: number;
  profiles_updated: number;
  materials_added: number;
  materials_updated: number;
  profile_count: number;
  material_count: number;
  sources: string[];
  errors: string[];
  used_offline_fallback: boolean;
}
