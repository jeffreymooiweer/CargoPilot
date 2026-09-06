import { ReactElement, useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router";
import { useTranslation } from "react-i18next";
import { api, User } from "../api/client";
import { useBranding } from "../branding";
import { usePreferences } from "../settings/preferences";
import UpdateToast from "./UpdateToast";
import TwoFactorNudge, { clearTwoFactorNudge } from "./TwoFactorNudge";
import WhatsNewModal from "./WhatsNewModal";
import {
  CollapseIcon,
  GroupageIcon,
  HistoryIcon,
  LibraryIcon,
  MenuIcon,
  MoreIcon,
  PlusIcon,
  RoadIcon,
  SettingsIcon,
  ShipmentsIcon,
  TripsIcon,
  UserIcon,
} from "./icons";

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
  // The open application has nobody to sign out, no library to link to and
  // no release notes to show — and it says what it is where the account
  // name would otherwise stand, so a visitor can see it without asking.
  const { mode, publicSettings } = usePreferences();
  const open = mode === "open";
  // The shipments page exists only where the installation keeps them.
  const history = !open && !!publicSettings?.history_enabled;
  const { branding } = useBranding();

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
    // So the next sign-in is reminded again, rather than inheriting this
    // session's "already asked".
    clearTwoFactorNudge();
    onLogout();
    navigate("/login");
  };

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium min-h-[44px] whitespace-nowrap ${
      isActive
        ? "bg-brand-100 text-brand-700 dark:bg-brand-900/50 dark:text-brand-200"
        : "text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
    }`;

  /** The same link, drawn as an icon alone. A folded rail used to be no rail:
   *  the whole menu went away and coming back to it meant unfolding first. The
   *  icons stay, so the destinations stay one press away at 56px instead of
   *  200px. */
  const railLinkClass = ({ isActive }: { isActive: boolean }) =>
    `flex h-11 w-11 items-center justify-center rounded-lg ${
      isActive
        ? "bg-brand-100 text-brand-700 dark:bg-brand-900/50 dark:text-brand-200"
        : "text-slate-500 hover:bg-slate-100 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200"
    }`;

  const versionLabel = version ? (version.startsWith("v") ? version : `v${version}`) : null;

  const versionBadge = versionLabel ? (
    <p className="px-4 py-2 text-[10px] tracking-wide text-slate-400 dark:text-slate-500 select-none" aria-label={`${t("settings.version")} ${versionLabel}`}>
      {open ? `${t("nav.openMode")} · ${versionLabel}` : versionLabel}
    </p>
  ) : null;

  // What stands where the account name would: which application this is.
  // The health line says the same thing to a script; this says it to a
  // person, in every language the screen speaks.
  const whoami = open ? (
    <span title={t("nav.openModeHint")}>{t("nav.openMode")}</span>
  ) : (
    <span>{user.username}</span>
  );

  /** One destination: where it goes, what it is called, whether this
   *  installation and this account have it, and the glyph the folded rail
   *  shows in place of the words. */
  interface RailLink {
    to: string;
    label: string;
    when: boolean;
    icon: (props: { className?: string }) => ReactElement;
  }

  const linkGroups = (): { key: string; links: RailLink[] }[] => {
    const admin = !open && user.role === "admin";
    // Four groups rather than ten links in a row: the work, the libraries it
    // draws on, what an administrator keeps, and this account. Every address
    // is the one it always was — this is a heading above a list, not a move.
    return [
      {
        key: "work",
        links: [
          { to: "/", label: t("nav.new"), when: true, icon: PlusIcon },
          { to: "/shipments", label: t("nav.shipments"), when: history, icon: ShipmentsIcon },
          { to: "/groupage", label: t("nav.groupage"), when: true, icon: GroupageIcon },
          { to: "/trips", label: t("nav.trips"), when: history, icon: TripsIcon },
        ],
      },
      {
        key: "libraries",
        links: [
          { to: "/articles", label: t("nav.articles"), when: history, icon: LibraryIcon },
          { to: "/materieel", label: t("nav.materieel"), when: admin, icon: RoadIcon },
        ],
      },
      {
        key: "administration",
        links: [
          { to: "/users", label: t("nav.users"), when: admin, icon: UserIcon },
          { to: "/audit", label: t("nav.audit"), when: admin, icon: HistoryIcon },
        ],
      },
      {
        key: "account",
        links: [
          { to: "/settings", label: t("nav.settings"), when: true, icon: SettingsIcon },
          // The set has no glyph for a page of licences and credits, and
          // inventing one that half-says "law" would be worse than the three
          // dots, which say "the rest" and leave the label to do the work.
          { to: "/legal", label: t("nav.legal"), when: true, icon: MoreIcon },
        ],
      },
    ];
  };

  const navLinks = () => {
    return (
      <>
        {linkGroups().map((group) => {
          const shown = group.links.filter((link) => link.when);
          if (shown.length === 0) return null;
          return (
            <div key={group.key} className="space-y-0.5">
              <p className="px-3 pt-3 text-[11px] font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">
                {t(`nav.group.${group.key}`)}
              </p>
              {shown.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === "/"}
                  className={linkClass}
                  onClick={closeMenu}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  <span className="truncate">{label}</span>
                </NavLink>
              ))}
            </div>
          );
        })}
      </>
    );
  };

  /** The folded rail: the same destinations, as icons. The label is still
   *  there for anyone who cannot see the glyph — as the accessible name and as
   *  the tooltip — because an icon on its own is a guess. */
  const railIcons = () => (
    <>
      {linkGroups().map((group) => {
        const shown = group.links.filter((link) => link.when);
        if (shown.length === 0) return null;
        return (
          <div key={group.key} className="flex flex-col items-center gap-1 py-1.5">
            {shown.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                className={railLinkClass}
                title={label}
                aria-label={label}
              >
                <Icon className="h-5 w-5" />
              </NavLink>
            ))}
          </div>
        );
      })}
    </>
  );

  // Folding the rail away is only half of it. The shell is capped at 80rem, so
  // on a wide monitor the 200px freed up went into the margin and the lines
  // table — which wants 1,620px — was no better off. With the rail folded the
  // cap lifts, and the same measurement that produced the table's floor decides
  // this one: 1,800px minus the padding leaves the table its full width. The
  // folded rail is 56px of icons rather than nothing, so the cap is 56px wider
  // than it was and the table keeps exactly the width it was measured to need.
  const shellWidth = `mx-auto transition-[max-width] duration-300 ease-out motion-reduce:transition-none ${
    railOpen ? "max-w-7xl" : "max-w-[1856px]"
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
            <MenuIcon className="w-6 h-6" />
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
            <CollapseIcon
              className={`w-5 h-5 transition-transform duration-300 ease-out motion-reduce:transition-none ${
                railOpen ? "" : "rotate-180"
              }`}
            />
          </button>
          <div className="min-w-0 flex-1 md:flex-none flex items-center gap-2 sm:gap-3">
            {/* The default glyph is black and is inverted for the dark theme.
                An uploaded logo is a picture in its own colours and must not
                be — inverting a company's logo is not a theme, it is damage. */}
            <img
              src={branding.logo ?? "/shipping.png"}
              alt=""
              aria-hidden="true"
              className={`h-8 w-8 sm:h-9 sm:w-9 shrink-0 object-contain ${branding.logo ? "" : "dark:brightness-0 dark:invert"}`}
            />
            <div className="min-w-0">
              <h1 className="text-lg sm:text-xl font-semibold text-slate-900 dark:text-slate-100 truncate">
                {branding.name || t("app.name")}
              </h1>
              <p className="text-xs text-slate-500 dark:text-slate-400 truncate hidden sm:block">{t("app.tagline")}</p>
            </div>
          </div>
          <div className="hidden md:flex items-center gap-3 text-sm text-slate-500 dark:text-slate-400">
            {whoami}
            {!open && (
              <button type="button" onClick={handleLogout} className="text-slate-600 dark:text-slate-300 hover:underline">
                {t("nav.logout")}
              </button>
            )}
          </div>
        </div>
      </header>

      {/* The column itself animates, so the main panel widens into the space
          rather than jumping into it. `grid-template-columns` is animatable
          between two lengths, which keeps this to one transition instead of a
          margin and a width fighting each other. */}
      <div
        className={`${shellWidth} px-3 sm:px-4 py-4 sm:py-6 md:grid md:transition-[grid-template-columns,column-gap,max-width] md:duration-300 md:ease-out motion-reduce:md:transition-none ${
          railOpen ? "md:grid-cols-[200px_1fr] md:gap-x-6" : "md:grid-cols-[56px_1fr] md:gap-x-2"
        }`}
      >
        <nav
          id="main-nav"
          className="hidden md:flex flex-col gap-1 min-h-[calc(100vh-7rem)] overflow-hidden"
        >
          {/* One or the other, never both. Keeping the folded rail in the DOM
              alongside the open one would put every destination on the screen
              twice — once for the eye and once more for a screen reader and
              the tab key. */}
          {railOpen ? navLinks() : railIcons()}
          <div className="flex-1" aria-hidden />
          {railOpen && versionBadge}
        </nav>
        <main className="min-w-0"><Outlet /></main>
      </div>

      {/* Only signed-in chrome mounts these, which is exactly who release
          notes are for; the login page stays free of them. The toast asks the
          server only for administrators — the one role that can pull an image.
          The open application has none of the three: no account to remember
          what was seen, no administrator to update, no second factor. */}
      {!open && <WhatsNewModal />}
      {!open && <UpdateToast user={user} />}
      {!open && <TwoFactorNudge user={user} />}

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
              <p className="px-4 py-1 text-xs text-slate-500 dark:text-slate-400">
                {open ? t("nav.openModeHint") : user.username}
              </p>
              {!open && (
                <button
                  type="button"
                  onClick={handleLogout}
                  className="w-full text-left px-4 py-3 rounded-lg text-sm text-red-600 dark:text-red-400 min-h-[44px]"
                >
                  {t("nav.logout")}
                </button>
              )}
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}
