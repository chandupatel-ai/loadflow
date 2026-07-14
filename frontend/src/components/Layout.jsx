import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className="app-shell">
      <div className="topbar">
        <div className="brand"><span className="dot">●</span> LoadFlow</div>
        <div className="topbar-right">
          <span className={`badge badge-${user.account_type}`}>{user.account_type}</span>
          <span>{user.full_name || user.email}</span>
          {user.is_org_admin && <span style={{ color: "var(--amber)" }}>admin</span>}
          <button className="btn btn-sm" onClick={logout}>Log out</button>
        </div>
      </div>
      <div className="main">
        <div className="sidebar">
          <NavLink to="/" end className={({ isActive }) => `side-link ${isActive ? "active" : ""}`}>Dashboard</NavLink>
          <NavLink to="/loads" className={({ isActive }) => `side-link ${isActive ? "active" : ""}`}>Load board</NavLink>
          {user.account_type === "carrier" && (
            <NavLink to="/compliance" className={({ isActive }) => `side-link ${isActive ? "active" : ""}`}>Compliance</NavLink>
          )}
          {user.is_org_admin && (
            <NavLink to="/roles" className={({ isActive }) => `side-link ${isActive ? "active" : ""}`}>Roles & staff</NavLink>
          )}
          {user.is_org_admin && (
            <NavLink to="/audit-log" className={({ isActive }) => `side-link ${isActive ? "active" : ""}`}>Audit log</NavLink>
          )}
        </div>
        <Outlet />
      </div>
    </div>
  );
}
