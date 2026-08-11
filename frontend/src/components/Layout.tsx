import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router";
import { useTranslation } from "react-i18next";
import { api, User } from "../api/client";

interface Props {
  user: User;
  onLogout: () => void;
}

/** Where the side menu is in the way rather than useful.
 *
 *  The wizard's lines table is a table you *type* in: description, quantity,
 *  unit, cargo form and two masses, all of them input fields. On a laptop the
 *  fixed 200px rail took enough width off it that the fields became too narrow
 *  to enter anything in. Everywhere else the rail costs nothing, because those
 *  screens are reading width. */
const WIZARD_PATH = /^\/wizard\//;

export default function Layout({ user, onLogout }: Props) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const [railOpen, setRailOpen] = useState(true);
  const [version, setVersion] = useState<string | null>(null);

  const inWizard = WIZARD_PATH.test(location.pathname);
  // The rail follows the route once, on the way in and on the way out. Doing it
  // on every render would fight the user: they fold it back open to reach the
  // settings link, and the next keystroke folds it shut again.
  const followedRoute = useRef<boolean | null>(null);
  useEffect(() => {
    if (followedRoute.current === inWizard) return;
    followedRoute.current = inWizard;
    setRailOpen(!inWizard);
  }, [inWizard]);

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
    `block px-4 py-3 rounded-lg text-sm font-medium min-h-[44px] whitespace-nowrap ${
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

  // A collapsed rail is still in the DOM, so its links stay in the tab order
  // unless they are taken out of it. A menu you cannot see but can tab into is
  // worse than one that is simply gone.
  const navLinks = (reachable = true) => {
    const tabIndex = reachable ? undefined : -1;
    return (
      <>
        <NavLink to="/" className={linkClass} end onClick={closeMenu} tabIndex={tabIndex}>{t("nav.new")}</NavLink>
        {user.role === "admin" && <NavLink to="/materieel" className={linkClass} onClick={closeMenu} tabIndex={tabIndex}>{t("nav.materieel")}</NavLink>}
        {user.role === "admin" && <NavLink to="/users" className={linkClass} onClick={closeMenu} tabIndex={tabIndex}>{t("nav.users")}</NavLink>}
        <NavLink to="/settings" className={linkClass} onClick={closeMenu} tabIndex={tabIndex}>{t("nav.settings")}</NavLink>
        <NavLink to="/legal" className={linkClass} onClick={closeMenu} tabIndex={tabIndex}>{t("nav.legal")}</NavLink>
      </>
    );
  };

  // Folding the rail away is only half of it. The shell is capped at 80rem, so
  // on a wide monitor the 200px freed up went into the margin and the lines
  // table — which wants 1,620px — was no better off. With the rail away the cap
  // lifts, and the same measurement that produced the table's floor decides
  // this one: 1,800px minus the padding leaves the table its full width.
  const shellWidth = `mx-auto transition-[max-width] duration-300 ease-out motion-reduce:transition-none ${
    railOpen ? "max-w-7xl" : "max-w-[1800px]"
  }`;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <header className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 sticky top-0 z-40">
        <div className={`${shellWidth} px-3 sm:px-4 py-3 flex items-center justify-between gap-3`}>
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
          <button
            type="button"
            className="hidden md:flex p-2 -ml-2 rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200 min-h-[44px] min-w-[44px] items-center justify-center"
            onClick={() => setRailOpen((open) => !open)}
            aria-expanded={railOpen}
            aria-controls="main-nav"
            aria-label={railOpen ? t("nav.collapseMenu") : t("nav.expandMenu")}
            title={railOpen ? t("nav.collapseMenu") : t("nav.expandMenu")}
          >
            <svg
              className={`w-5 h-5 transition-transform duration-300 ease-out motion-reduce:transition-none ${
                railOpen ? "" : "rotate-180"
              }`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
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

      {/* The column itself animates, so the main panel widens into the space
          rather than jumping into it. `grid-template-columns` is animatable
          between two lengths, which keeps this to one transition instead of a
          margin and a width fighting each other. */}
      <div
        className={`${shellWidth} px-3 sm:px-4 py-4 sm:py-6 md:grid md:transition-[grid-template-columns,column-gap,max-width] md:duration-300 md:ease-out motion-reduce:md:transition-none ${
          railOpen ? "md:grid-cols-[200px_1fr] md:gap-x-6" : "md:grid-cols-[0px_1fr] md:gap-x-0"
        }`}
      >
        <nav
          id="main-nav"
          className={`hidden md:flex flex-col gap-1 min-h-[calc(100vh-7rem)] overflow-hidden transition-[opacity,transform] duration-300 ease-out motion-reduce:transition-none ${
            railOpen ? "opacity-100 translate-x-0" : "pointer-events-none -translate-x-4 opacity-0"
          }`}
          aria-hidden={!railOpen}
        >
          {navLinks(railOpen)}
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
            <nav className="flex-1 overflow-y-auto p-3 space-y-1">{navLinks()}</nav>
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
