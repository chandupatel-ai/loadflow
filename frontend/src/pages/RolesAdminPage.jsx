import { useEffect, useState } from "react";
import api from "../api";
import { useAuth } from "../context/AuthContext";

export default function RolesAdminPage() {
  const { user } = useAuth();
  const [catalog, setCatalog] = useState([]);
  const [roles, setRoles] = useState([]);
  const [staff, setStaff] = useState([]);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  const [roleName, setRoleName] = useState("");
  const [rolePerms, setRolePerms] = useState([]);

  const [staffForm, setStaffForm] = useState({ email: "", password: "", full_name: "", role_id: "" });

  const refresh = async () => {
    const [c, r, s] = await Promise.all([
      api.get("/roles/permission-catalog"),
      api.get("/roles"),
      api.get("/roles/staff"),
    ]);
    setCatalog(c.data.permissions);
    setRoles(r.data);
    setStaff(s.data);
  };

  useEffect(() => { refresh(); }, []);

  if (!user.is_org_admin) {
    return (
      <div className="content">
        <div className="error-box">Only an org admin can manage roles and staff.</div>
      </div>
    );
  }

  const togglePerm = (p) => {
    setRolePerms((cur) => cur.includes(p) ? cur.filter((x) => x !== p) : [...cur, p]);
  };

  const createRole = async (e) => {
    e.preventDefault();
    setErr(""); setMsg("");
    try {
      await api.post("/roles", { name: roleName, permissions: rolePerms });
      setRoleName(""); setRolePerms([]);
      setMsg("Role created.");
      refresh();
    } catch (e2) { setErr(e2?.response?.data?.detail || "Failed to create role"); }
  };

  const inviteStaff = async (e) => {
    e.preventDefault();
    setErr(""); setMsg("");
    try {
      await api.post("/roles/staff", { ...staffForm, role_id: Number(staffForm.role_id) });
      setStaffForm({ email: "", password: "", full_name: "", role_id: "" });
      setMsg("Staff invited.");
      refresh();
    } catch (e2) { setErr(e2?.response?.data?.detail || "Failed to invite staff"); }
  };

  return (
    <div className="content">
      <h1>Roles & staff</h1>
      <p className="subtitle">
        Build custom roles as bundles of permissions from the catalog, then invite staff into
        those roles. Nothing here is hardcoded — the API checks permission strings, not role names.
      </p>
      {err && <div className="error-box">{err}</div>}
      {msg && <div className="info-box">{msg}</div>}

      <div className="panel">
        <h2>Create a role</h2>
        <form onSubmit={createRole}>
          <div className="form-group">
            <label>Role name</label>
            <input required value={roleName} onChange={(e) => setRoleName(e.target.value)}
                   placeholder='e.g. "Dispatcher", "Ops Lead"' />
          </div>
          <div className="form-group">
            <label>Permissions</label>
            <div className="checklist">
              {catalog.map((p) => (
                <div key={p} className={`check-chip ${rolePerms.includes(p) ? "selected" : ""}`}
                     onClick={() => togglePerm(p)}>
                  {p}
                </div>
              ))}
            </div>
          </div>
          <button className="btn btn-primary" disabled={!roleName || rolePerms.length === 0}>
            Create role
          </button>
        </form>
      </div>

      <div className="panel">
        <h2>Existing roles</h2>
        {roles.length === 0 ? <div className="empty-state">No custom roles yet.</div> : (
          <table>
            <thead><tr><th>Name</th><th>Permissions</th></tr></thead>
            <tbody>
              {roles.map((r) => (
                <tr key={r.id}>
                  <td>{r.name}</td>
                  <td className="mono" style={{ fontSize: 12 }}>{r.permissions.join(", ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="panel">
        <h2>Invite staff</h2>
        <form onSubmit={inviteStaff}>
          <div className="form-row">
            <div className="form-group">
              <label>Full name</label>
              <input value={staffForm.full_name} onChange={(e) => setStaffForm({ ...staffForm, full_name: e.target.value })} />
            </div>
            <div className="form-group">
              <label>Email</label>
              <input required type="email" value={staffForm.email}
                     onChange={(e) => setStaffForm({ ...staffForm, email: e.target.value })} />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Temporary password</label>
              <input required type="password" value={staffForm.password}
                     onChange={(e) => setStaffForm({ ...staffForm, password: e.target.value })} />
            </div>
            <div className="form-group">
              <label>Role</label>
              <select required value={staffForm.role_id}
                      onChange={(e) => setStaffForm({ ...staffForm, role_id: e.target.value })}>
                <option value="">Select role…</option>
                {roles.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
              </select>
            </div>
          </div>
          <button className="btn btn-primary" disabled={roles.length === 0}>Invite staff</button>
        </form>
      </div>

      <div className="panel">
        <h2>Org members</h2>
        <table>
          <thead><tr><th>Name</th><th>Email</th><th>Admin</th><th>Role</th></tr></thead>
          <tbody>
            {staff.map((s) => (
              <tr key={s.id}>
                <td>{s.full_name || "—"}</td>
                <td>{s.email}</td>
                <td>{s.is_org_admin ? "✓" : ""}</td>
                <td className="mono">{s.role_id ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
