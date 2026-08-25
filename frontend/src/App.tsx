import { useEffect, useState } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router";
import { api, User } from "./api/client";
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
import LegalPage from "./pages/LegalPage";
import { PreferencesProvider } from "./settings/preferences";
import { ToastProvider } from "./toast/ToastProvider";

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    api.me()
      .then((res) => setUser(res.user))
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-slate-500 dark:text-slate-400">Loading...</div>;
  }

  if (!user) {
    return (
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
    );
  }

  return (
    <PreferencesProvider>
      <ToastProvider>
      <Routes>
        <Route element={<Layout user={user} onLogout={() => setUser(null)} />}>
          <Route path="/" element={<ModalitySelectPage />} />
          <Route path="/wizard" element={<Navigate to="/" replace />} />
          <Route path="/wizard/:modality" element={<WizardPage />} />
          <Route path="/groupage" element={<GroupagePage />} />
          <Route path="/materieel" element={<MaterieelPage />} />
          <Route path="/settings" element={<SettingsPage user={user} />} />
          <Route path="/legal" element={<LegalPage />} />
          <Route path="/users" element={<UsersPage user={user} />} />
        </Route>
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/cards" element={<CardsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      </ToastProvider>
    </PreferencesProvider>
  );
}
