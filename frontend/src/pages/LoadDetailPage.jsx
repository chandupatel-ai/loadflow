import { useEffect, useState, useCallback } from "react";
import { useParams } from "react-router-dom";
import api from "../api";
import { useAuth } from "../context/AuthContext";

const STATES = [
  "Posted", "Carrier Assigned", "Rate Confirmed", "Dispatched",
  "In Transit", "Delivered", "POD Verified", "Invoiced/Closed",
];

export default function LoadDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const [load, setLoad] = useState(null);
  const [history, setHistory] = useState([]);
  const [rates, setRates] = useState([]);
  const [pods, setPods] = useState([]);
  const [carriers, setCarriers] = useState([]);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  const [carrierChoice, setCarrierChoice] = useState("");
  const [rateForm, setRateForm] = useState({ base_rate: "", accessorials: "" });
  const [podUrl, setPodUrl] = useState("");

  const load_ = useCallback(async () => {
    setErr("");
    try {
      const [l, h, r, p] = await Promise.all([
        api.get(`/loads/${id}`),
        api.get(`/loads/${id}/history`),
        api.get(`/loads/${id}/rate-confirmations`),
        api.get(`/loads/${id}/pods`),
      ]);
      setLoad(l.data);
      setHistory(h.data);
      setRates(r.data);
      setPods(p.data);
    } catch (e) {
      setErr(e?.response?.data?.detail || "Failed to load");
    }
    if (user.account_type === "broker") {
      try {
        const c = await api.get("/dashboard/carriers");
        setCarriers(c.data);
      } catch { /* not permitted, fine */ }
    }
  }, [id, user.account_type]);

  useEffect(() => { load_(); }, [load_]);

  const act = async (fn) => {
    setErr(""); setMsg("");
    try {
      await fn();
      setMsg("Done.");
      await load_();
    } catch (e) {
      setErr(e?.response?.data?.detail || "Action failed");
    }
  };

  if (err && !load) return <div className="content"><div className="error-box">{err}</div></div>;
  if (!load) return <div className="content">Loading…</div>;

  const currentIdx = STATES.indexOf(load.status);
  const nextState = STATES[currentIdx + 1];

  return (
    <div className="content">
      <h1>Load #{load.id}</h1>
      <p className="subtitle">{load.pickup_location} → {load.delivery_location}</p>

      {err && <div className="error-box">{err}</div>}
      {msg && <div className="info-box">{msg}</div>}

      {load.compliance_flag && (
        <div className="error-box">
          ⚠ This load is compliance-flagged — the assigned carrier has an insurance/authority
          issue. Progression past "Carrier Assigned" is blocked until resolved (or overridden
          by a role with the compliance-override permission).
        </div>
      )}

      <div className="grid-2">
        <div className="panel">
          <h2>Details</h2>
          <table>
            <tbody>
              <tr><td>Status</td><td><span className="status-pill">{load.status}</span></td></tr>
              <tr><td>Commodity</td><td>{load.commodity || "—"}</td></tr>
              <tr><td>Equipment</td><td>{load.equipment_type || "—"}</td></tr>
              <tr><td>Weight</td><td>{load.weight_lbs} lbs</td></tr>
              <tr><td>Carrier org</td><td>{load.carrier_org_id ? `#${load.carrier_org_id}` : "unassigned"}</td></tr>
            </tbody>
          </table>
        </div>

        <div className="panel">
          <h2>Status history</h2>
          {history.length === 0 ? <div className="empty-state">No history.</div> : (
            <div className="timeline">
              {history.map((h, i) => (
                <div className="timeline-item" key={i}>
                  <div>{h.from_status || "—"} → <strong>{h.to_status}</strong></div>
                  <div className="ts">{new Date(h.timestamp).toLocaleString()}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {user.account_type === "broker" && !load.carrier_org_id && (
        <div className="panel">
          <h2>Assign carrier</h2>
          <div className="form-row">
            <div className="form-group" style={{ flex: 2 }}>
              <select value={carrierChoice} onChange={(e) => setCarrierChoice(e.target.value)}>
                <option value="">Select a carrier…</option>
                {carriers.map((c) => (
                  <option key={c.org_id} value={c.org_id}>
                    {c.name} {c.is_compliant ? "✓ compliant" : "⚠ non-compliant"}
                  </option>
                ))}
              </select>
            </div>
            <button
              className="btn btn-primary"
              disabled={!carrierChoice}
              onClick={() => act(() => api.post(`/loads/${id}/assign-carrier`, { carrier_org_id: Number(carrierChoice) }))}
            >
              Assign
            </button>
          </div>
        </div>
      )}

      <div className="panel">
        <h2>Rate confirmations</h2>
        {rates.length === 0 ? <div className="empty-state">No rate confirmed yet.</div> : (
          <table>
            <thead><tr><th>Version</th><th>Base rate</th><th>Accessorials</th><th>Current</th></tr></thead>
            <tbody>
              {rates.map((r) => (
                <tr key={r.id}>
                  <td className="mono">v{r.version}</td>
                  <td>${r.base_rate.toFixed(2)}</td>
                  <td>${r.accessorials.toFixed(2)}</td>
                  <td>{r.is_current ? "✓" : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {user.account_type === "broker" && (
          <div className="form-row" style={{ marginTop: 12 }}>
            <div className="form-group">
              <label>Base rate ($)</label>
              <input type="number" value={rateForm.base_rate}
                     onChange={(e) => setRateForm({ ...rateForm, base_rate: e.target.value })} />
            </div>
            <div className="form-group">
              <label>Accessorials ($)</label>
              <input type="number" value={rateForm.accessorials}
                     onChange={(e) => setRateForm({ ...rateForm, accessorials: e.target.value })} />
            </div>
            <div className="form-group" style={{ justifyContent: "flex-end" }}>
              <button
                className="btn btn-primary"
                disabled={!rateForm.base_rate}
                onClick={() => act(() => api.post(`/loads/${id}/rate-confirmations`, {
                  base_rate: Number(rateForm.base_rate), accessorials: Number(rateForm.accessorials) || 0,
                }))}
              >
                Confirm rate
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="panel">
        <h2>Proof of delivery</h2>
        {pods.length === 0 ? <div className="empty-state">No POD uploaded yet.</div> : (
          <ul>{pods.map((p) => <li key={p.id}><a href={p.file_url} target="_blank" rel="noreferrer">{p.file_url}</a></li>)}</ul>
        )}
        <div className="form-row" style={{ marginTop: 8 }}>
          <div className="form-group" style={{ flex: 2 }}>
            <input placeholder="https://…/pod.pdf" value={podUrl} onChange={(e) => setPodUrl(e.target.value)} />
          </div>
          <button className="btn" disabled={!podUrl}
                  onClick={() => act(() => api.post(`/loads/${id}/pods`, { file_url: podUrl }).then(() => setPodUrl("")))}>
            Upload
          </button>
        </div>
      </div>

      {nextState && (
        <div className="panel">
          <h2>Advance status</h2>
          <p style={{ color: "var(--text-dim)", fontSize: 13 }}>
            Current: <strong>{load.status}</strong> → Next: <strong>{nextState}</strong>
          </p>
          <button className="btn btn-primary"
                  onClick={() => act(() => api.post(`/loads/${id}/status`, { to_status: nextState }))}>
            Move to "{nextState}"
          </button>
        </div>
      )}
    </div>
  );
}
