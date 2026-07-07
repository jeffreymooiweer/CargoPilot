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
  exportAppendix: async (payload: Record<string, unknown>) => {
    const res = await fetch(`${API_BASE}/export`, {
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
    a.download = `appendix_${Date.now()}.xlsx`;
    a.click();
    URL.revokeObjectURL(url);
  },
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
