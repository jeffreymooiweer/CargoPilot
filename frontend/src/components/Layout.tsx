import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api, User } from "../api/client";
import { toggleTheme } from "../theme";

interface Props {
  user: User;
  onLogout: () => void;
}

export default function Layout({ user, onLogout }: Props) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const [dark, setDark] = useState(document.documentElement.classList.contains("dark"));

  const handleLogout = async () => {
    await api.logout();
    onLogout();
    navigate("/login");
  };

  const handleThemeToggle = () => {
    setDark(toggleTheme() === "dark");
  };

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center justify-center md:justify-start gap-2 px-3 py-2.5 md:py-2 rounded-lg text-sm font-medium min-h-[44px] md:min-h-0 ${
      isActive
        ? "bg-brand-100 text-brand-700 dark:bg-brand-900/50 dark:text-brand-200"
        : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
    }`;

  const navItems = (
    <>
      <NavLink to="/" className={linkClass} end>{t("nav.dashboard")}</NavLink>
      <NavLink to="/wizard" className={linkClass}>{t("nav.new")}</NavLink>
      {user.role === "admin" && <NavLink to="/materieel" className={linkClass}>{t("nav.materieel")}</NavLink>}
      {user.role === "admin" && <NavLink to="/users" className={linkClass}>{t("nav.users")}</NavLink>}
    </>
  );

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <header className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-3 sm:px-4 py-3 sm:py-4 flex flex-wrap items-center justify-between gap-2">
          <div className="min-w-0">
            <h1 className="text-lg sm:text-xl font-semibold text-slate-900 dark:text-slate-100 truncate">{t("app.name")}</h1>
            <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 truncate hidden xs:block">{t("app.tagline")}</p>
          </div>
          <div className="flex items-center gap-1.5 sm:gap-2 flex-shrink-0">
            <button
              type="button"
              onClick={handleThemeToggle}
              className="text-sm border border-slate-200 dark:border-slate-700 rounded-lg px-2 py-1.5 min-h-[36px] text-slate-600 dark:text-slate-300"
              aria-label={t("theme.toggle")}
            >
              {dark ? "☀" : "☾"}
            </button>
            <select
              className="text-sm border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 rounded-lg px-2 py-1.5 min-h-[36px] text-slate-700 dark:text-slate-200"
              value={i18n.language}
              onChange={(e) => i18n.changeLanguage(e.target.value)}
            >
              <option value="nl">NL</option>
              <option value="en">EN</option>
            </select>
            <span className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 hidden sm:inline max-w-[80px] truncate">{user.username}</span>
            <button onClick={handleLogout} className="text-xs sm:text-sm text-slate-600 dark:text-slate-300 px-2 py-1.5 min-h-[36px]">
              {t("nav.logout")}
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-3 sm:px-4 py-4 sm:py-6 md:grid md:grid-cols-[200px_1fr] md:gap-6">
        <nav className="hidden md:flex flex-col gap-1">{navItems}</nav>
        <main className="min-w-0"><Outlet /></main>
      </div>

      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-30 bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 px-2 py-1 safe-area-pb">
        <div className="flex justify-around gap-1 max-w-lg mx-auto">{navItems}</div>
      </nav>
    </div>
  );
}
