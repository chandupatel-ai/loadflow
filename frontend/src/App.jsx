import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Layout from "./components/Layout";
import AuthPage from "./pages/AuthPage";
import DashboardPage from "./pages/DashboardPage";
import LoadBoardPage from "./pages/LoadBoardPage";
import LoadDetailPage from "./pages/LoadDetailPage";
import RolesAdminPage from "./pages/RolesAdminPage";
import CompliancePage from "./pages/CompliancePage";
import AuditLogPage from "./pages/AuditLogPage";

function Gate({ children }) {
  const { user, loading } = useAuth();
  if (loading) {
    return <div className="center-screen" style={{ color: "var(--text-dim)" }}>Loading…</div>;
  }
  if (!user) return <AuthPage />;
  return children;
}

function AppRoutes() {
  return (
    <Gate>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/loads" element={<LoadBoardPage />} />
          <Route path="/loads/:id" element={<LoadDetailPage />} />
          <Route path="/roles" element={<RolesAdminPage />} />
          <Route path="/compliance" element={<CompliancePage />} />
          <Route path="/audit-log" element={<AuditLogPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </Gate>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
