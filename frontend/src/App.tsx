import { useEffect, useState } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router";
import { api, InstallationMode, User, VISITOR } from "./api/client";
import Layout from "./components/Layout";
import CardsPage from "./pages/CardsPage";
import GroupagePage from "./pages/GroupagePage";
import LoginPage from "./pages/LoginPage";
import ResetPasswordPage from "./pages/ResetPasswordPage";
import ModalitySelectPage from "./pages/ModalitySelectPage";
import WizardPage from "./pages/WizardPage";
import UsersPage from "./pages/UsersPage";
import MaterieelPage from "./pages/MaterieelPage";
import SettingsPage from "./pages/SettingsPage";
import ShipmentsPage from "./pages/ShipmentsPage";
import LegalPage from "./pages/LegalPage";
import { BrandingProvider } from "./branding";
import { PreferencesProvider } from "./settings/preferences";
import { ToastProvider } from "./toast/ToastProvider";

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [mode, setMode] = useState<InstallationMode>("organisation");
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    // Which application is this? The health line says, and it needs no
    // cookie — the one question that can be asked before knowing whether
    // there is anybody to ask on behalf of. The open application has no
    // `/auth/me` to call, so its caller is the visitor, straight away. An
    // unreachable server is treated as the organisation application: the
    // sign-in page is the one that can show the error.
    let cancelled = false;
    void (async () => {
      const health = await api.health().catch(() => null);
      if (cancelled) return;
      if (health?.mode === "open") {
        setMode("open");
        setUser(VISITOR);
        setLoading(false);
        return;
      }
      try {
        setUser((await api.me()).user);
      } catch {
        setUser(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-slate-500 dark:text-slate-400">Loading...</div>;
  }

  if (!user) {
    return (
      <BrandingProvider>
      <ToastProvider>
      <Routes>
        <Route path="/login" element={<LoginPage onLogin={() => api.me().then((r) => { setUser(r.user); navigate("/"); })} />} />
        {/* A reset link is opened by somebody who cannot sign in; sending
            them to /login would swallow the token in the address. */}
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        {/* The QR code on a transport document is scanned by somebody who has
            no account here. Sending them to /login would make the code
            useless, which is the whole point of it being public. */}
        <Route path="/cards" element={<CardsPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
      </ToastProvider>
      </BrandingProvider>
    );
  }

  const open = mode === "open";

  return (
    <BrandingProvider>
    <PreferencesProvider mode={mode}>
      <ToastProvider>
      <Routes>
        <Route element={<Layout user={user} onLogout={() => setUser(null)} />}>
          <Route path="/" element={<ModalitySelectPage />} />
          <Route path="/wizard" element={<Navigate to="/" replace />} />
          <Route path="/wizard/:modality" element={<WizardPage />} />
          <Route path="/groupage" element={<GroupagePage />} />
          {/* The library and the users page presume an account. In the open
              application their addresses are not on the server either, so
              a page that called them would only draw an error. */}
          {/* The history exists only where the switch is on; the page says
              so itself when it is not, and the open application never
              keeps anything. */}
          {!open && <Route path="/shipments" element={<ShipmentsPage />} />}
          {!open && <Route path="/shipments/:id" element={<ShipmentsPage />} />}
          {!open && <Route path="/materieel" element={<MaterieelPage />} />}
          {!open && <Route path="/users" element={<UsersPage user={user} />} />}
          <Route path="/settings" element={<SettingsPage user={user} />} />
          <Route path="/legal" element={<LegalPage />} />
        </Route>
        {!open && <Route path="/reset-password" element={<ResetPasswordPage />} />}
        <Route path="/cards" element={<CardsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      </ToastProvider>
    </PreferencesProvider>
    </BrandingProvider>
  );
}
