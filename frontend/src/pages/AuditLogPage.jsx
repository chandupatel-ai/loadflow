import { useEffect, useState } from "react";
import api from "../api";
import { useAuth } from "../context/AuthContext";

export default function AuditLogPage() {
  const { user } = useAuth();
  const [rows, setRows] = useState([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.get("/dashboard/audit-log").then((r) => setRows(r.data)).catch((e) =>
      setErr(e?.response?.data?.detail || "Failed to load audit log")
    );
  }, []);

  if (!user.is_org_admin) {
    return <div className="content"><div className="error-box">Only org admins can view the audit log.</div></div>;
  }

  return (
    <div className="content">
      <h1>Audit log</h1>
      <p className="subtitle">Permission-denied attempts across the platform (most recent 200).</p>
      {err && <div className="error-box">{err}</div>}
      <div className="panel">
        {rows.length === 0 ? <div className="empty-state">No denied attempts logged.</div> : (
          <table>
            <thead><tr><th>Time</th><th>User</th><th>Endpoint</th><th>Required</th><th>Reason</th></tr></thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  <td className="mono" style={{ fontSize: 11 }}>{new Date(r.timestamp).toLocaleString()}</td>
                  <td className="mono">{r.user_id ?? "—"}</td>
                  <td className="mono" style={{ fontSize: 12 }}>{r.endpoint}</td>
                  <td className="mono" style={{ fontSize: 12 }}>{r.required_permission || "—"}</td>
                  <td>{r.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
