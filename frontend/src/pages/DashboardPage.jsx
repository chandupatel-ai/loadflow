import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";
import { useAuth } from "../context/AuthContext";

export default function DashboardPage() {
  const { user } = useAuth();
  const [summary, setSummary] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.get("/dashboard/summary").then((r) => setSummary(r.data)).catch((e) =>
      setErr(e?.response?.data?.detail || "Failed to load dashboard")
    );
  }, []);

  const roleLabel = {
    broker: "Broker load board",
    carrier: "Carrier assigned loads",
    shipper: "Your shipments",
  }[user.account_type];

  return (
    <div className="content">
      <h1>Dashboard</h1>
      <p className="subtitle">{roleLabel} — welcome back, {user.full_name || user.email}.</p>

      {err && <div className="error-box">{err}</div>}

      {summary && (
        <>
          <div className="grid-3" style={{ marginBottom: 20 }}>
            <div className="stat">
              <div className="num">{summary.total_loads}</div>
              <div className="label">Total loads</div>
            </div>
            <div className="stat">
              <div className="num" style={{ color: summary.compliance_alerts.length ? "var(--red)" : "var(--green)" }}>
                {summary.compliance_alerts.length}
              </div>
              <div className="label">Compliance alerts</div>
            </div>
            <div className="stat">
              <div className="num">{Object.keys(summary.by_status).length}</div>
              <div className="label">Active statuses</div>
            </div>
          </div>

          <div className="panel">
            <h2>Loads by status</h2>
            {Object.keys(summary.by_status).length === 0 ? (
              <div className="empty-state">No loads yet.</div>
            ) : (
              <table>
                <tbody>
                  {Object.entries(summary.by_status).map(([status, count]) => (
                    <tr key={status}>
                      <td><span className="status-pill">{status}</span></td>
                      <td style={{ textAlign: "right" }} className="mono">{count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {summary.compliance_alerts.length > 0 && (
            <div className="panel" style={{ borderColor: "var(--red)" }}>
              <h2 style={{ color: "var(--red)" }}>⚠ Compliance-flagged loads</h2>
              <p style={{ color: "var(--text-dim)", fontSize: 13 }}>
                These loads are blocked from progressing past "Carrier Assigned" until the
                carrier's insurance/authority issue is resolved.
              </p>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}>
                {summary.compliance_alerts.map((id) => (
                  <Link key={id} to={`/loads/${id}`} className="btn btn-sm btn-danger">
                    Load #{id}
                  </Link>
                ))}
              </div>
            </div>
          )}

          <Link to="/loads" className="btn btn-primary">Go to load board →</Link>
        </>
      )}
    </div>
  );
}
