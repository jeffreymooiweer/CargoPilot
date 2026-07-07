import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api, User } from "../api/client";

interface Props {
  user: User;
  onLogout: () => void;
}

export default function Layout({ user, onLogout }: Props) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await api.logout();
    onLogout();
    navigate("/login");
  };

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `px-3 py-2 rounded-lg text-sm font-medium ${isActive ? "bg-brand-100 text-brand-700" : "text-slate-600 hover:bg-slate-100"}`;

  return (
    <div className="min-h-screen">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-slate-900">{t("app.name")}</h1>
            <p className="text-sm text-slate-500">{t("app.tagline")}</p>
          </div>
          <div className="flex items-center gap-2">
            <select
              className="text-sm border rounded-lg px-2 py-1"
              value={i18n.language}
              onChange={(e) => i18n.changeLanguage(e.target.value)}
            >
              <option value="nl">NL</option>
              <option value="en">EN</option>
            </select>
            <span className="text-sm text-slate-500">{user.username}</span>
            <button onClick={handleLogout} className="text-sm text-slate-600 hover:text-slate-900">
              {t("nav.logout")}
            </button>
          </div>
        </div>
      </header>
      <div className="max-w-7xl mx-auto px-4 py-6 grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6">
        <nav className="flex md:flex-col gap-1">
          <NavLink to="/" className={linkClass} end>{t("nav.dashboard")}</NavLink>
          <NavLink to="/wizard" className={linkClass}>{t("nav.new")}</NavLink>
          <NavLink to="/history" className={linkClass}>{t("nav.history")}</NavLink>
          <NavLink to="/materials" className={linkClass}>{t("nav.materials")}</NavLink>
          <NavLink to="/profiles" className={linkClass}>{t("nav.profiles")}</NavLink>
          {user.role === "admin" && <NavLink to="/users" className={linkClass}>{t("nav.users")}</NavLink>}
        </nav>
        <main>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
