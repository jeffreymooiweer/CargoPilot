import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api, User } from "../api/client";

interface Props {
  user: User;
  onLogout: () => void;
}

export default function Layout({ user, onLogout }: Props) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [version, setVersion] = useState<string | null>(null);

  useEffect(() => {
    api.health().then((h) => setVersion(h.version)).catch(() => {});
  }, []);

  useEffect(() => {
    document.body.style.overflow = menuOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [menuOpen]);

  const closeMenu = () => setMenuOpen(false);

  const handleLogout = async () => {
    closeMenu();
    await api.logout();
    onLogout();
    navigate("/login");
  };

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `block px-4 py-3 rounded-lg text-sm font-medium min-h-[44px] ${
      isActive
        ? "bg-brand-100 text-brand-700 dark:bg-brand-900/50 dark:text-brand-200"
        : "text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
    }`;

  const versionLabel = version ? (version.startsWith("v") ? version : `v${version}`) : null;

  const versionBadge = versionLabel ? (
    <p className="px-4 py-2 text-[10px] tracking-wide text-slate-400 dark:text-slate-500 select-none" aria-label={`${t("settings.version")} ${versionLabel}`}>
      {versionLabel}
    </p>
  ) : null;

  const navLinks = (
    <>
      <NavLink to="/" className={linkClass} end onClick={closeMenu}>{t("nav.dashboard")}</NavLink>
      <NavLink to="/wizard" className={linkClass} onClick={closeMenu}>{t("nav.new")}</NavLink>
      {user.role === "admin" && <NavLink to="/materieel" className={linkClass} onClick={closeMenu}>{t("nav.materieel")}</NavLink>}
      {user.role === "admin" && <NavLink to="/users" className={linkClass} onClick={closeMenu}>{t("nav.users")}</NavLink>}
      <NavLink to="/settings" className={linkClass} onClick={closeMenu}>{t("nav.settings")}</NavLink>
    </>
  );

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <header className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-3 sm:px-4 py-3 flex items-center justify-between gap-3">
          <button
            type="button"
            className="md:hidden p-2 -ml-2 rounded-lg text-slate-700 dark:text-slate-200 min-h-[44px] min-w-[44px] flex items-center justify-center"
            onClick={() => setMenuOpen(true)}
            aria-label={t("nav.openMenu")}
          >
            <span className="sr-only">{t("nav.openMenu")}</span>
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
              <path strokeLinecap="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <div className="min-w-0 flex-1 md:flex-none flex items-center gap-2 sm:gap-3">
            <img
              src="/shipping.png"
              alt=""
              aria-hidden="true"
              className="h-8 w-8 sm:h-9 sm:w-9 shrink-0 dark:brightness-0 dark:invert"
            />
            <div className="min-w-0">
              <h1 className="text-lg sm:text-xl font-semibold text-slate-900 dark:text-slate-100 truncate">{t("app.name")}</h1>
              <p className="text-xs text-slate-500 dark:text-slate-400 truncate hidden sm:block">{t("app.tagline")}</p>
            </div>
          </div>
          <div className="hidden md:flex items-center gap-3 text-sm text-slate-500 dark:text-slate-400">
            <span>{user.username}</span>
            <button type="button" onClick={handleLogout} className="text-slate-600 dark:text-slate-300 hover:underline">
              {t("nav.logout")}
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-3 sm:px-4 py-4 sm:py-6 md:grid md:grid-cols-[200px_1fr] md:gap-6">
        <nav className="hidden md:flex flex-col gap-1 min-h-[calc(100vh-7rem)]">
          {navLinks}
          <div className="flex-1" aria-hidden />
          {versionBadge}
        </nav>
        <main className="min-w-0"><Outlet /></main>
      </div>

      {menuOpen && (
        <div className="md:hidden fixed inset-0 z-50">
          <button type="button" className="absolute inset-0 bg-black/50" onClick={closeMenu} aria-label={t("nav.closeMenu")} />
          <aside className="absolute left-0 top-0 bottom-0 w-[min(100%,280px)] bg-white dark:bg-slate-900 shadow-xl flex flex-col">
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-800">
              <span className="font-semibold text-slate-900 dark:text-slate-100">{t("nav.menu")}</span>
              <button type="button" onClick={closeMenu} className="p-2 rounded-lg min-h-[44px] min-w-[44px]" aria-label={t("nav.closeMenu")}>
                ×
              </button>
            </div>
            <nav className="flex-1 overflow-y-auto p-3 space-y-1">{navLinks}</nav>
            <div className="p-3 border-t border-slate-200 dark:border-slate-800">
              {versionBadge}
              <p className="px-4 py-1 text-xs text-slate-500 dark:text-slate-400">{user.username}</p>
              <button
                type="button"
                onClick={handleLogout}
                className="w-full text-left px-4 py-3 rounded-lg text-sm text-red-600 dark:text-red-400 min-h-[44px]"
              >
                {t("nav.logout")}
              </button>
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}
