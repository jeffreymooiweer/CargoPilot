import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, User } from "../api/client";

const inputClass =
  "border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 w-full";
const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";
const buttonPrimary =
  "rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50";
const buttonSecondary =
  "rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800";
const buttonDanger =
  "rounded-lg border border-red-200 px-3 py-1.5 text-sm text-red-700 hover:bg-red-50 disabled:opacity-50 dark:border-red-900/60 dark:text-red-300 dark:hover:bg-red-950/40";

/** Whether the backend's safety rules would refuse this change: you cannot
 *  demote, deactivate or delete yourself, nor the last active
 *  administrator. The server enforces it; disabling the control here just
 *  saves the round trip and explains itself in the tooltip. */
function guarded(target: User, self: User | null, users: User[]): string | null {
  const isSelf = self != null && target.id === self.id;
  const activeAdmins = users.filter((u) => u.role === "admin" && u.active !== false).length;
  const lastAdmin = target.role === "admin" && target.active !== false && activeAdmins <= 1;
  if (isSelf) return "self";
  if (lastAdmin) return "lastAdmin";
  return null;
}

export default function UsersPage({ user: self }: { user: User | null }) {
  const { t } = useTranslation();
  const [users, setUsers] = useState<User[]>([]);
  const [form, setForm] = useState({ username: "", email: "", password: "", role: "user" });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [resetFor, setResetFor] = useState<number | null>(null);
  const [resetPassword, setResetPassword] = useState("");

  const load = () =>
    api
      .listUsers()
      .then(setUsers)
      .catch((e) => setError(String(e)));
  useEffect(() => {
    void load();
  }, []);

  const run = async (action: () => Promise<unknown>, done = "") => {
    setBusy(true);
    setMessage("");
    setError("");
    try {
      await action();
      await load();
      if (done) setMessage(done);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const create = (e: React.FormEvent) => {
    e.preventDefault();
    void run(async () => {
      await api.createUser(form);
      setForm({ username: "", email: "", password: "", role: "user" });
    }, t("users.created"));
  };

  const patch = (id: number, payload: Record<string, unknown>, done = "") =>
    run(() => api.updateUser(id, payload), done);

  const remove = (target: User) => {
    if (!confirm(t("users.deleteConfirm", { name: target.username }))) return;
    void run(() => api.deleteUser(target.id), t("users.deleted"));
  };

  const guardText = (kind: string | null) =>
    kind === "self" ? t("users.guardSelf") : kind === "lastAdmin" ? t("users.guardLastAdmin") : undefined;

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">{t("users.title")}</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{t("users.intro")}</p>
      </div>

      <form onSubmit={create} className={`${panelClass} p-5 space-y-4`}>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          {t("users.newUser")}
        </h3>
        <div className="grid gap-3 md:grid-cols-2">
          <div>
            <label className="text-sm font-medium text-slate-800 dark:text-slate-200" htmlFor="new-username">
              {t("users.username")}
            </label>
            <input
              id="new-username"
              className={`${inputClass} mt-1`}
              value={form.username}
              minLength={3}
              required
              onChange={(e) => setForm({ ...form, username: e.target.value })}
            />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-800 dark:text-slate-200" htmlFor="new-email">
              {t("users.email")}
            </label>
            <input
              id="new-email"
              type="email"
              className={`${inputClass} mt-1`}
              value={form.email}
              required
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-800 dark:text-slate-200" htmlFor="new-password">
              {t("users.password")}
            </label>
            <input
              id="new-password"
              type="password"
              className={`${inputClass} mt-1`}
              value={form.password}
              minLength={8}
              required
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
            <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{t("users.passwordHint")}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-slate-800 dark:text-slate-200" htmlFor="new-role">
              {t("users.role")}
            </label>
            <select
              id="new-role"
              className={`${inputClass} mt-1`}
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value })}
            >
              <option value="user">{t("users.roleUser")}</option>
              <option value="admin">{t("users.roleAdmin")}</option>
            </select>
          </div>
        </div>
        <button className={buttonPrimary} disabled={busy}>
          {t("users.create")}
        </button>
      </form>

      <div className="space-y-3">
        {users.map((u) => {
          const guard = guarded(u, self, users);
          const inactive = u.active === false;
          return (
            <div key={u.id} className={`${panelClass} p-4 space-y-3 ${inactive ? "opacity-70" : ""}`}>
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium text-slate-900 dark:text-slate-100">{u.username}</span>
                {self && u.id === self.id && (
                  <span className="rounded-full bg-brand-100 px-2 py-0.5 text-[11px] font-medium text-brand-700 dark:bg-brand-900/50 dark:text-brand-200">
                    {t("users.you")}
                  </span>
                )}
                {inactive && (
                  <span className="rounded-full bg-slate-200 px-2 py-0.5 text-[11px] font-medium text-slate-600 dark:bg-slate-700 dark:text-slate-300">
                    {t("users.inactive")}
                  </span>
                )}
                <span className="text-sm text-slate-500 dark:text-slate-400">{u.email}</span>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <label className="text-xs text-slate-500 dark:text-slate-400">
                  {t("users.role")}
                  <select
                    className={`${inputClass} mt-1 !w-auto py-1.5 text-sm`}
                    value={u.role}
                    disabled={busy || guard !== null}
                    title={guardText(guard)}
                    onChange={(e) => void patch(u.id, { role: e.target.value }, t("users.saved"))}
                  >
                    <option value="user">{t("users.roleUser")}</option>
                    <option value="admin">{t("users.roleAdmin")}</option>
                  </select>
                </label>

                <div className="ml-auto flex flex-wrap gap-2">
                  <button
                    type="button"
                    className={buttonSecondary}
                    disabled={busy || guard !== null}
                    title={guardText(guard)}
                    onClick={() => void patch(u.id, { active: inactive }, t("users.saved"))}
                  >
                    {inactive ? t("users.activate") : t("users.deactivate")}
                  </button>
                  <button
                    type="button"
                    className={buttonSecondary}
                    disabled={busy}
                    onClick={() => {
                      setResetFor(resetFor === u.id ? null : u.id);
                      setResetPassword("");
                    }}
                  >
                    {t("users.resetPassword")}
                  </button>
                  <button
                    type="button"
                    className={buttonDanger}
                    disabled={busy || guard !== null}
                    title={guardText(guard)}
                    onClick={() => remove(u)}
                  >
                    {t("users.delete")}
                  </button>
                </div>
              </div>

              {resetFor === u.id && (
                <form
                  className="flex flex-wrap items-end gap-2"
                  onSubmit={(e) => {
                    e.preventDefault();
                    void patch(u.id, { password: resetPassword }, t("users.passwordReset"));
                    setResetFor(null);
                    setResetPassword("");
                  }}
                >
                  <div className="min-w-[220px] flex-1">
                    <label className="text-xs text-slate-500 dark:text-slate-400" htmlFor={`reset-${u.id}`}>
                      {t("users.newPasswordFor", { name: u.username })}
                    </label>
                    <input
                      id={`reset-${u.id}`}
                      type="password"
                      className={`${inputClass} mt-1`}
                      value={resetPassword}
                      minLength={8}
                      required
                      onChange={(e) => setResetPassword(e.target.value)}
                    />
                  </div>
                  <button className={buttonPrimary} disabled={busy}>
                    {t("users.resetPasswordDo")}
                  </button>
                </form>
              )}
            </div>
          );
        })}
      </div>

      {message && <p className="text-sm text-emerald-700 dark:text-emerald-400">{message}</p>}
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
    </div>
  );
}
