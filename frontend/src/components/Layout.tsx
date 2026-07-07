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
    `px-3 py-2 rounded-lg text-sm font-medium ${
      isActive
        ? "bg-brand-100 text-brand-700 dark:bg-brand-900/50 dark:text-brand-200"
        : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
    }`;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <header className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">{t("app.name")}</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">{t("app.tagline")}</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleThemeToggle}
              className="text-sm border border-slate-200 dark:border-slate-700 rounded-lg px-2 py-1 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
              aria-label={t("theme.toggle")}
            >
              {dark ? t("theme.light") : t("theme.dark")}
            </button>
            <select
              className="text-sm border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 rounded-lg px-2 py-1 text-slate-700 dark:text-slate-200"
              value={i18n.language}
              onChange={(e) => i18n.changeLanguage(e.target.value)}
            >
              <option value="nl">NL</option>
              <option value="en">EN</option>
            </select>
            <span className="text-sm text-slate-500 dark:text-slate-400">{user.username}</span>
            <button onClick={handleLogout} className="text-sm text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white">
              {t("nav.logout")}
            </button>
          </div>
        </div>
      </header>
      <div className="max-w-7xl mx-auto px-4 py-6 grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6">
        <nav className="flex md:flex-col gap-1">
          <NavLink to="/" className={linkClass} end>{t("nav.dashboard")}</NavLink>
          <NavLink to="/wizard" className={linkClass}>{t("nav.new")}</NavLink>
          {user.role === "admin" && <NavLink to="/users" className={linkClass}>{t("nav.users")}</NavLink>}
        </nav>
        <main>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
