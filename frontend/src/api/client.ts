const API_BASE = "/api";

async function downloadBlob(path: string, filename: string): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, { credentials: "include" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Download failed");
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

async function uploadFile<T>(path: string, file: File): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    credentials: "include",
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof err.detail === "string" ? err.detail : "Upload failed");
  }
  return res.json();
}

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
  health: () => request<{ status: string; app: string; version: string }>("/health"),
  setupStatus: () => request<{ has_admin: boolean }>("/setup-status"),
  parse: (payload: Record<string, unknown>) =>
    request<CalcResult>("/parse", { method: "POST", body: JSON.stringify(payload) }),
  calculate: (payload: Record<string, unknown>) =>
    request<CalcResult>("/calculate", { method: "POST", body: JSON.stringify(payload) }),
  dgInstructions: () => request<DgInstructions>("/dg/instructions"),
  dgLookup: (un: string) => request<DgLookupResult>(`/dg/lookup?un=${encodeURIComponent(un)}`),
  dgSearch: (q: string, limit = 12) =>
    request<{ results: DgUnEntry[] }>(`/dg/search?q=${encodeURIComponent(q)}&limit=${limit}`),
  dgPackagings: (q = "", limit = 150) =>
    request<{ results: DgPackaging[] }>(`/dg/packagings?q=${encodeURIComponent(q)}&limit=${limit}`),
  listUsers: () => request<User[]>("/users"),
  createUser: (payload: Record<string, unknown>) =>
    request<User>("/users", { method: "POST", body: JSON.stringify(payload) }),
  listEquipment: () => request<EquipmentItem[]>("/equipment"),
  createEquipment: (payload: Partial<EquipmentItem>) =>
    request<EquipmentItem>("/equipment", { method: "POST", body: JSON.stringify(payload) }),
  updateEquipment: (id: number, payload: Partial<EquipmentItem>) =>
    request<EquipmentItem>(`/equipment/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteEquipment: (id: number) => request<{ ok: boolean }>(`/equipment/${id}`, { method: "DELETE" }),
  downloadEquipmentTemplate: () => downloadBlob("/equipment/import-template", "materieel_import_template.xlsx"),
  importEquipmentFile: (file: File) => uploadFile<EquipmentImportResult>("/equipment/import", file),
  downloadWizardTemplate: () => downloadBlob("/import/wizard-template", "wizard_import_template.xlsx"),
  parseWizardImportFile: (file: File) => uploadFile<WizardFileParseResult>("/import/wizard-file", file),
  catalogSearch: (q: string, limit = 25) =>
    request<{ results: CatalogSearchHit[] }>(`/catalog/search?q=${encodeURIComponent(q)}&limit=${limit}`),
  geoLocations: (q: string, types?: GeoLocationType[], limit = 8) =>
    request<{ results: GeoLocation[] }>(
      `/geo/locations?q=${encodeURIComponent(q)}&limit=${limit}${types?.length ? `&type=${types.join(",")}` : ""}`,
    ),
  geoAddress: (q: string, lang = "en", limit = 6) =>
    request<{ results: GeoAddress[]; available: boolean }>(
      `/geo/address?q=${encodeURIComponent(q)}&lang=${lang}&limit=${limit}`,
    ),
  documentsRegistry: () => request<DocumentRegistry>("/documents/registry"),
  dgPrepare: (entries: DgEntry[], lines: LineItem[], profiles: string[], language: string) =>
    request<DgPrepareResult>("/dg/prepare", {
      method: "POST",
      body: JSON.stringify({ entries, lines, profiles, language }),
    }),
  dgCompliance: (entries: DgEntry[], profiles: string[], language: string) =>
    request<DgComplianceResult>("/dg/compliance", {
      method: "POST",
      body: JSON.stringify({ entries, profiles, language }),
    }),
  validateDocument: (payload: DocumentExportPayload) =>
    request<DocumentValidationResult>("/documents/validate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  exportDocument: async (payload: DocumentExportPayload) => {
    const res = await fetch(`${API_BASE}/documents/export`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      const detail = err.detail;
      if (detail && typeof detail === "object" && Array.isArray(detail.errors)) {
        throw new Error(detail.errors.join("\n"));
      }
      throw new Error(typeof detail === "string" ? detail : "Export failed");
    }
    const blob = await res.blob();
    const disposition = res.headers.get("content-disposition") || "";
    const match = disposition.match(/filename="?([^";]+)"?/i);
    const contentType = res.headers.get("content-type") || "";
    const ext = contentType.includes("pdf") ? "pdf" : "xlsx";
    const filename = match ? match[1] : `${payload.document_key}_${Date.now()}.${ext}`;
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  },
  unCardsAvailability: (payload: UnCardsPayload) =>
    request<UnCardsAvailability>("/documents/un-cards/availability", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  downloadUnCards: async (payload: UnCardsPayload) => {
    const res = await fetch(`${API_BASE}/documents/un-cards`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(typeof err.detail === "string" ? err.detail : "Download failed");
    }
    const blob = await res.blob();
    const disposition = res.headers.get("content-disposition") || "";
    const match = disposition.match(/filename="?([^";]+)"?/i);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = match ? match[1] : `un_cards_${Date.now()}.zip`;
    a.click();
    URL.revokeObjectURL(url);
  },
};

export interface UnCardsPayload {
  dangerous_goods?: unknown[] | null;
  output_language?: string;
}

export interface UnCardsAvailability {
  enabled: boolean;
  requested: string[];
  available: string[];
  missing: string[];
  count: number;
  library_size: number;
}

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
  input_language?: string;
  dangerous_goods?: boolean;
  detected_un_numbers?: string[];
}

export interface CalcResult {
  success: boolean;
  column_map: Record<string, number | null>;
  lines: LineItem[];
  totals: Record<string, number>;
  errors: unknown[];
}

export interface DgProduct {
  un_number?: string;
  proper_shipping_name?: string;
  technical_name?: string;
  class?: string;
  subsidiary_risks?: string;
  packing_group?: string;
  packing_instruction?: string;
  flashpoint?: string;
  type_of_package?: string;
  quantity_packages?: string;
  quantity_items_per_package?: string;
  net_mass_liters_per_package?: string;
  gross_mass_per_package?: string;
  eq_lq_points?: string;
  dimensions?: string;
  additional_information?: string;
  caliber?: string;
  marine_pollutant?: string;
  cargo_aircraft_only?: string;
  overpack?: string;
  emergency_contact?: string;
  ems_code?: string;
  transport_category?: string;
  adr_total_quantity?: string;
  q_net_quantity?: string;
  q_max_net_quantity?: string;
  classification_code?: string;
  tunnel_code?: string;
  labels?: string;
  hazard_number?: string;
  iata_packing_instruction?: string;
  limited_quantity?: string;
  excepted_quantity?: string;
}

export interface DgEntry {
  line_id: number;
  vehicle: string;
  registration?: string;
  products: DgProduct[];
}

export interface DgPrepareHint {
  line_id?: number;
  product_index?: number;
  un_number?: string;
  ems_source?: string;
  ems_class_default?: string;
  ems_description?: string;
  ems_variants?: { label: string; code: string; description: string }[];
  ems_packing_group_options?: Record<string, string>;
  excepted_quantity_text?: string;
  limited_quantity_text?: string;
  air_note?: string;
  air_forbidden?: boolean;
  segregation_groups?: string[];
  segregation_groups_text?: string;
  transport_forbidden?: boolean;
  transport_forbidden_note?: string;
  label_reference_note?: string;
}

export interface DgPrepareResult {
  entries: DgEntry[];
  document_lines: Record<string, string[]>;
  hints: DgPrepareHint[];
  requirements: string[];
  adr_category_totals?: {
    statement: string;
    categories: { transport_category: string; total: string }[];
  };
}

export interface DgLookupResult {
  un_number: string;
  proper_shipping_name: string;
  class: string;
  subsidiary_risks?: string;
  classification_code?: string;
  packing_group?: string;
  packing_instruction?: string;
  transport_category?: string | number | null;
  tunnel_restriction_code?: string | null;
  limited_quantity?: string | null;
  source?: string;
}

export interface DgInstructions {
  dg_intro: { nl: string; en: string };
  dg_fields: Record<string, { label: { nl: string; en: string }; help: { nl: string; en: string } }>;
}

export interface CatalogSearchHit {
  id: string;
  source: "equipment" | "profile" | "reference" | "template" | "material";
  label: string;
  sublabel: string | null;
  value: string;
  score: number;
}

export type GeoLocationType = "airport" | "port" | "station";

export interface GeoLocation {
  type: GeoLocationType;
  name: string;
  code: string;
  icao?: string;
  country: string;
  city?: string;
  subdivision?: string;
}

export interface GeoAddress {
  label: string;
  name: string;
  street: string;
  housenumber: string;
  postcode: string;
  city: string;
  state: string;
  country: string;
  countrycode: string;
}

export interface EquipmentItem {
  id?: number;
  sap_code?: string | null;
  specifications: string;
  length_cm?: number | null;
  width_cm?: number | null;
  height_cm?: number | null;
  weight_kg: number;
  aliases?: string[];
  language_labels?: Record<string, string>;
  source?: string | null;
  notes?: string | null;
  active?: boolean;
}

export interface EquipmentImportResult {
  created: number;
  updated: number;
  skipped: number;
  errors: string[];
}

export interface WizardFileParseResult {
  text: string;
  has_header: boolean;
}

export type LocalizedText = { nl: string; en: string };

export type FieldStatus =
  | "AUTO_DERIVED"
  | "USER_REQUIRED"
  | "USER_OPTIONAL"
  | "CONDITIONAL"
  | "CARRIER_PROVIDED"
  | "OPERATIONAL"
  | "SIGNATURE_REQUIRED"
  | "FIXED_TEMPLATE_TEXT";

export interface DocumentFieldOption {
  value: string;
  label: LocalizedText;
}

export interface DocumentField {
  key: string;
  label: LocalizedText;
  status: FieldStatus;
  type: "text" | "textarea" | "number" | "date" | "select" | "checkbox";
  options?: DocumentFieldOption[];
  condition?: string;
  auto_from?: string;
  help?: LocalizedText;
}

export interface DocumentSection {
  key?: string;
  ref?: string;
  label?: LocalizedText;
  fields?: DocumentField[];
}

export interface DocumentDefinition {
  key: string;
  label: LocalizedText;
  short_label: LocalizedText;
  category: string;
  issue_status: LocalizedText;
  /** "avc" vult, net als "pdf_template", een officieel formulier in. */
  exporter: "generic" | "pdf_template" | "avc";
  output_format?: "xlsx" | "pdf";
  dg_profile: string | null;
  dg_only?: boolean;
  default_selected?: boolean;
  sections: DocumentSection[];
  signature_note?: LocalizedText;
}

export interface ModalityDefinition {
  key: string;
  label: LocalizedText;
  description: LocalizedText;
  documents: string[];
}

export interface DocumentRegistry {
  registry_version: string;
  field_statuses: Record<FieldStatus, LocalizedText>;
  modalities: ModalityDefinition[];
  shared_sections: DocumentSection[];
  documents: DocumentDefinition[];
  modality_defaults?: Record<string, string>;
}

export interface DgUnEntry {
  un: string;
  name_en: string;
  name_de: string;
  class: string;
  classification_code: string;
  packing_group: string;
  labels: string;
  special_provisions: string;
  limited_quantity: string;
  excepted_quantity: string;
  packing_instructions: string;
  transport_category: string;
  tunnel_code: string;
  hazard_number: string;
}

export interface DgPackaging {
  code: string;
  category: string;
  label: { nl: string; en: string };
  contents: string;
}

export interface DocumentExportPayload extends Record<string, unknown> {
  document_key: string;
  values: Record<string, string>;
  lines: LineItem[];
  dangerous_goods?: DgEntry[];
  output_language: string;
  signature_image?: string;
}

export interface DocumentValidationResult {
  document_key: string;
  errors: string[];
  warnings: string[];
}

export interface AdrPointsRow {
  product: string;
  transport_category: string | null;
  quantity: number | null;
  factor?: number | null;
  points: number | null;
}

export interface AdrPointsResult {
  rows: AdrPointsRow[];
  total_points: number;
  threshold: number;
  status: "exempt_possible" | "above_threshold" | "not_exempt" | "incomplete";
  category0_products: string[];
  incomplete_products: string[];
  quantity_units_note: string;
  exempt_provisions: string[];
  still_required: string[];
}

export interface ComplianceWarning {
  rule: string;
  severity: "error" | "warning";
  message: string;
  products: string;
}

export interface QValueResult {
  position: string | number;
  components: { product: string; net_quantity: number; max_per_package: number; ratio: number }[];
  q_value: number;
  exceeded: boolean;
  note: string;
}

export interface DgComplianceResult {
  sources: Record<string, string>;
  profiles: string[];
  adr_points?: AdrPointsResult;
  adr_mixed_loading?: ComplianceWarning[];
  imdg_segregation?: ComplianceWarning[];
  imdg_note?: string;
  imdg_segregation_groups?: {
    note: string;
    class8_exception: string;
    groups: { code: string; label: string }[];
  };
  iata_segregation?: ComplianceWarning[];
  q_values?: QValueResult[];
  cargo_aircraft_only_products?: string[];
}
