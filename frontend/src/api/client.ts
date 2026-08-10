import i18n from "i18next";

const API_BASE = "/api";

async function downloadBlob(path: string, filename: string): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, { credentials: "include" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(describeDetail(err.detail));
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
    // The import routes answer with a translatable message, so this cannot
    // assume a string any more — that assumption is what produced "Upload
    // failed" where the server had said exactly what was wrong.
    throw new Error(describeDetail(err.detail));
  }
  return res.json();
}

/** FastAPI reads a repeated parameter as a list: ?profiles=ADR&profiles=IMDG. */
function profileQuery(profiles: string[]): string {
  return profiles.map((p) => `&profiles=${encodeURIComponent(p)}`).join("");
}

/** A message the backend sends with a code, so the interface can translate it.
 *
 * The server does not translate. It cannot: an error is raised deep in a
 * service that has no idea who is asking, and the language belongs to the
 * screen. So it sends a code, the parameters that go in the sentence, and an
 * English text to fall back on. */
export interface ApiMessage {
  code: string;
  message: string;
  params?: Record<string, unknown>;
}

/** The translation for a message code, or the server's English fallback.
 *
 * The fallback is what makes this safe to deploy: a backend newer than the
 * frontend in front of it can send a code these language files do not know yet,
 * and the user still reads a sentence instead of a dotted key. */
export function translateMessage(message: ApiMessage): string {
  const fallback = message.message || message.code;
  const key = `errors.${message.code}`;
  // `t` can return the key itself, or nothing at all when i18next has not
  // finished initialising — on the very first paint, or in a unit test that
  // never loads a bundle. Neither is a translation, and neither is worth
  // showing when the server already sent a readable sentence.
  const translated = i18n.t(key, { ...(message.params ?? {}), defaultValue: fallback });
  return typeof translated === "string" && translated && translated !== key ? translated : fallback;
}

function isApiMessage(value: unknown): value is ApiMessage {
  return !!value && typeof value === "object" && typeof (value as ApiMessage).code === "string";
}

/** Make a FastAPI error readable, and in the user's language where possible.
 *
 * Three shapes arrive here, and all three used to end up as "[object Object]"
 * or as a Dutch sentence:
 *
 * - `{code, message}` — an error this application raised on purpose;
 * - a list of `{type, loc, msg, ctx}` — FastAPI's own 422, where `type` carries
 *   our code for the validators that set one;
 * - a plain string — FastAPI's built-ins, which stay English.
 *
 * The field path is kept ("products → 1 → adr_total_quantity: …") with the head
 * ("body") removed, because it adds nothing.
 */
export function describeDetail(detail: unknown): string {
  if (typeof detail === "string" && detail) return detail;
  if (isApiMessage(detail)) return translateMessage(detail);
  if (Array.isArray(detail)) {
    const lines = detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (!item || typeof item !== "object") return "";
        const entry = item as { loc?: unknown[]; msg?: string; type?: string; ctx?: Record<string, unknown> };
        const where = (entry.loc ?? [])
          .filter((part) => part !== "body")
          .map((part) => String(part))
          .join(" → ");
        const fallback = entry.msg?.replace(/^Value error,\s*/, "") ?? "";
        const message = entry.type
          ? translateMessage({ code: entry.type, message: fallback, params: entry.ctx })
          : fallback;
        return where ? `${where}: ${message}` : message;
      })
      .filter(Boolean);
    if (lines.length) return lines.join("\n");
  }
  return translateMessage({ code: "request_failed", message: "Request failed" });
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
    throw new Error(describeDetail(err.detail));
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
  unitCatalogue: () => request<UnitCatalogue>("/units"),
  convertUnit: (payload: {
    quantity?: number | null;
    unit?: string | null;
    density_kg_m3?: number | null;
    category?: string | null;
    mass_per_item_kg?: number | null;
    volume_per_item_m3?: number | null;
  }) => request<UnitConversion>("/units/convert", { method: "POST", body: JSON.stringify(payload) }),
  // Language and profiles travel along because the proper shipping name depends
  // on them: ADR 5.4.1.4.1 permits a German name, IMDG 5.4.1.4.1 and IATA DGR
  // 8.1.2.1 do not. The suggestion the user clicks is the text that ends up on
  // the document.
  dgLookup: (un: string, language = "nl", profiles: string[] = []) =>
    request<DgLookupResult>(
      `/dg/lookup?un=${encodeURIComponent(un)}&language=${language}${profileQuery(profiles)}`,
    ),
  dgSearch: (q: string, limit = 12, language = "nl", profiles: string[] = []) =>
    request<{ results: DgUnEntry[] }>(
      `/dg/search?q=${encodeURIComponent(q)}&limit=${limit}&language=${language}` +
        profileQuery(profiles),
    ),
  dgPackagings: (q = "", limit = 150) =>
    request<{ results: DgPackaging[] }>(`/dg/packagings?q=${encodeURIComponent(q)}&limit=${limit}`),
  mySettings: () => request<UserPreferences>("/settings/me"),
  saveMySettings: (payload: UserPreferences) =>
    request<UserPreferences>("/settings/me", { method: "PUT", body: JSON.stringify(payload) }),
  publicSettings: () => request<PublicSettings>("/settings/public"),
  settingsOptions: () => request<SettingsOptions>("/settings/options"),
  instanceSettings: () => request<InstanceSettings>("/settings/instance"),
  saveInstanceSettings: (payload: InstanceSettings) =>
    request<InstanceSettings>("/settings/instance", { method: "PUT", body: JSON.stringify(payload) }),
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
  remapWizardImport: (rows: string[][], mapping: ImportMapping, hasHeader: boolean) =>
    request<WizardFileParseResult>("/import/wizard-remap", {
      method: "POST",
      body: JSON.stringify({ rows, mapping, has_header: hasHeader }),
    }),
  catalogSearch: (q: string, limit = 25, language = "nl") =>
    request<{ results: CatalogSearchHit[] }>(
      `/catalog/search?q=${encodeURIComponent(q)}&limit=${limit}&language=${language}`,
    ),
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

export type ThemeChoice = "light" | "dark" | "system";

/** One user's own settings. Kept on the server, so they follow the account to a
 *  second device instead of staying behind in one browser's localStorage. */
export interface UserPreferences {
  language: string;
  theme: ThemeChoice;
  default_modality: string;
  default_unit: string;
  prefill_documents: boolean;
  consignor_name: string;
  consignor_address: string;
  consignor_contact: string;
  carrier_name: string;
  loading_point: string;
  emergency_contact: string;
  signature_image: string;
}

/** What the whole installation is set to. Administrators only. */
export interface InstanceSettings {
  default_language: string;
  default_theme: ThemeChoice;
  address_lookup_enabled: boolean;
  address_api_url: string;
  address_timeout_seconds: number;
  catalog_auto_sync: boolean;
  un_cards_enabled: boolean;
  session_timeout_minutes: number;
  organisation_name: string;
  organisation_address: string;
}

/** The part of the instance settings every signed-in user may read. */
export interface PublicSettings {
  default_language: string;
  default_theme: ThemeChoice;
  address_lookup_enabled: boolean;
  un_cards_enabled: boolean;
  organisation_name: string;
  organisation_address: string;
}

/** The lists the settings screen offers, from the backend that owns them. */
export interface SettingsOptions {
  languages: string[];
  modalities: string[];
  units: { code: string; symbol: string }[];
}

export interface LineItem {
  line_id: number;
  raw: string;
  description: string;
  output_description: string;
  quantity: number | null;
  unit: string | null;
  material: string | null;
  /** Category of the recognised commodity, "liquid" or "bulk_material" for
   *  instance. Determines which units and forms the dropdowns suggest first. */
  material_category?: string | null;
  /** The form computed with: solid, stacked, loose bulk. */
  cargo_form?: string | null;
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
  /** Net per inner packaging, with unit — for the LQ/EQ check (3.4/3.5). */
  net_per_inner_packaging?: string;
  net_mass_liters_per_package?: string;
  gross_mass_per_package?: string;
  /** Class 1 only: total net explosive mass in kg (ADR 1.1.3.6.3). */
  net_explosive_mass?: string;
  /** Set by /dg/prepare for substances that may not be carried. */
  transport_forbidden?: boolean;
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
  /** A warning when a UN number has more than one packing group. */
  packing_group_note?: string;
  air_note?: string;
  air_forbidden?: boolean;
  segregation_groups?: string[];
  segregation_groups_text?: string;
  marine_pollutant_text?: string;
  imdg_stowage_codes?: string[];
  imdg_stowage_text?: string;
  imdg_segregation_codes?: string[];
  imdg_segregation_text?: string;
  /** The description of every code from IMDG 7.1.5, 7.1.6 and 7.2.8. */
  imdg_stowage_definitions?: { code: string; text: string }[];
  imdg_segregation_definitions?: { code: string; text: string }[];
  imdg_stowage_category?: string;
  /** What IMDG Amendment 42-24 changes about this substance. */
  imdg_amendment_changes?: string[];
  imdg_document_requirement?: { section: string; text: string; fields: string[] };
  /** From the Dangerous Goods List itself, chapter 3.2 of the IMDG Code. */
  imdg_special_provisions?: string[];
  imdg_packing_instructions?: string;
  imdg_packing_provisions?: string;
  imdg_tank_instructions?: string;
  imdg_tank_provisions?: string;
  imdg_subsidiary_hazards?: string;
  imdg_properties?: string;
  /** The list marks this entry as amended by 42-24. */
  imdg_amended_in_42_24?: boolean;
  imdg_dgl_source?: string;
  imdg_amendment?: string;
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
  /** One entry per unusable row, translated by the interface. */
  errors: ApiMessage[];
}

export interface ImportColumn {
  index: number;
  header: string;
  samples: string[];
}

export interface ImportMapping {
  description: number | null;
  quantity: number | null;
  unit: number | null;
}

export interface ImportAnalysis {
  columns: ImportColumn[];
  mapping: ImportMapping;
  /** "header": the heading row was recognised. "position": guessed from the order. */
  source: "header" | "position" | "user" | "none";
  has_header: boolean;
}

export interface WizardFileParseResult {
  text: string;
  has_header: boolean;
  analysis: ImportAnalysis;
  rows: string[][];
}

/** Dutch and English are always there; a third language can be missing in a
 *  registry that comes from elsewhere. Use `localised()` to get text out of it —
 *  that falls back instead of showing nothing. */
export type LocalizedText = { nl: string; en: string; de?: string };

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
  /** "avc" fills in an official form, just as "pdf_template" does. */
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
  /** Column (2) of Table A in the Dutch ADR edition; empty where it has none. */
  name_nl: string;
  /** The name in the language permitted for the chosen profiles. */
  proper_shipping_name: string;
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
  /** Lines with a transport prohibition are not in the count. */
  forbidden_products?: string[];
  category0_products: string[];
  incomplete_products: string[];
  quantity_units_note: string;
  exempt_provisions: string[];
  still_required: string[];
  /** Which tables were computed with, for example "ADR 1.1.3.6". */
  basis?: string;
  /** What the chosen mode says about this basis itself. For RID, that
   *  1.1.3.6.3/1.1.3.6.4 prescribe the same categories, factors and value 1000;
   *  for ADN, that it has no points at all and is assessed separately. */
  basis_note?: string | null;
}

export interface AdnExemptionRow {
  product: string;
  class?: string;
  selector?: string;
  limit: number | null;
  quantity: number | null;
}

/** ADN 1.1.3.6.1: exemption on gross mass, with a limit of its own per class.
 *  No points count — ADN does not have one. */
export interface AdnExemptionResult {
  rows: AdnExemptionRow[];
  total_gross_mass_kg: number;
  threshold: number;
  status: "exempt_possible" | "above_threshold" | "not_exempt" | "incomplete";
  over_class_limit: { class: string; selector: string; limit: number; carried: number }[];
  incomplete_products: string[];
  basis: string;
  conditions: string[];
  note: string;
}

export interface ComplianceWarning {
  rule: string;
  severity: "error" | "warning" | "info";
  message: string;
  products: string;
}

export type LqEqStatus =
  | "within_limits"
  | "not_within"
  | "not_permitted"
  | "incomplete"
  | "no_data";

export interface LqEqRow {
  product: string;
  position: string | number | null;
  lq: { value: string | null; status: LqEqStatus; message: string };
  eq: { code: string | null; status: LqEqStatus; message: string };
}

/** ADR/IMDG 3.4 and 3.5: the entered quantities tested against columns 7a/7b. */
export interface LqEqResult {
  rows: LqEqRow[];
  status: "checked" | "incomplete" | "not_checked";
  warnings: ComplianceWarning[];
  basis: string;
  basis_note?: string | null;
  note: string;
}

/** ADR 8.6.3: the tunnel restriction code derived for the whole load.
 *
 *  `status` says what happened, and the difference matters more than the code:
 *  `exempt` means 8.6.3.3 leaves the goods out of the determination entirely,
 *  `lq_marking_only` that the goods are exempt but the unit's 3.4.13 mark
 *  brings a category E restriction with it anyway. */
export interface AdrTunnelResult {
  rows: { product: string; code: string | null }[];
  /** Null where nothing was determined. */
  code: string | null;
  restricted_categories: string[];
  /** Total net explosive mass, only for the codes that split on it. */
  explosive_mass_kg: number | null;
  status: "derived" | "unrestricted" | "exempt" | "lq_marking_only" | "incomplete" | "unknown_code" | "not_checked";
  message: string;
  basis: string;
  note: string;
}

export interface QValueResult {
  position: string | number;
  components: { product: string; net_quantity: number; max_per_package: number; ratio: number }[];
  /** Null when there was nothing to compute or the input was incomplete. */
  q_value: number | null;
  exceeded: boolean | null;
  status?: "ok" | "exceeded" | "incomplete" | "not_checked";
  note: string;
}

/** Whether the Q check of 5.0.2.11 was actually performed. Belongs with the
 *  result, so the export sees it too and not only this panel. */
export interface QCheckStatus {
  status: "checked" | "incomplete" | "exceeded" | "not_checked";
  message: string;
}

export interface DgComplianceResult {
  sources: Record<string, string>;
  profiles: string[];
  adr_points?: AdrPointsResult;
  /** With the ADN profile only: its own exemption of 1.1.3.6.1. */
  adn_exemption?: AdnExemptionResult;
  adr_mixed_loading?: ComplianceWarning[];
  /** The same caveat as `basis_note`, for the mixed loading of 7.5.2. */
  adr_mixed_loading_basis_note?: string;
  /** Rule sets that have run out without anything taking their place. */
  rule_set_warnings?: ComplianceWarning[];
  /** What this result was computed with. */
  regulatory_manifest?: {
    manifest_id: string;
    editions: Record<string, string>;
    expired: string[];
  };
  imdg_segregation?: ComplianceWarning[];
  imdg_note?: string;
  imdg_segregation_groups?: {
    note: string;
    class8_exception: string;
    groups: { code: string; label: string }[];
  };
  iata_segregation?: ComplianceWarning[];
  /** LQ/EQ check of 3.4/3.5 — present with the ADR, RID, ADN and IMDG profiles. */
  lq_eq?: LqEqResult;
  /** Tunnel restriction code for the whole load — road only. */
  adr_tunnel?: AdrTunnelResult;
  q_values?: QValueResult[];
  q_check_status?: QCheckStatus;
  cargo_aircraft_only_products?: string[];
}


/** The unit catalogue. Units, and which of them are obvious for which category,
 *  are maintained in one place — in the backend — so the interface does not
 *  overwrite the list with another. */
export interface UnitCatalogue {
  units: { code: string; symbol: string; dimension: "mass" | "volume" | "length" | "count" }[];
  /** The form a commodity travels in, with the part of a cubic metre that is material. */
  forms: { code: string; fill_factor: number }[];
  /** Per category the applicable forms, the default first. Empty means the form
   *  does not come into play: for gravel the stored density is already a bulk
   *  density and a second factor would count the air twice. */
  forms_by_category: Record<string, string[]>;
  suggested_by_category: Record<string, string[]>;
  default_suggested: string[];
  density_basis_by_category: Record<string, string>;
}

export interface UnitConversion {
  mass_kg: number | null;
  volume_m3: number | null;
  density_basis: string;
  /** Filled when one of the two could not be determined, for example "per_item"
   *  with a count and no weight per item. Not an error but an outcome. */
  missing: string | null;
}

