import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import { useAuth } from "../context/AuthContext";

const STATUSES = [
  "Posted", "Carrier Assigned", "Rate Confirmed", "Dispatched",
  "In Transit", "Delivered", "POD Verified", "Invoiced/Closed",
];

export default function LoadBoardPage() {
  const { user } = useAuth();
  const nav = useNavigate();
  const [loads, setLoads] = useState([]);
  const [q, setQ] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ pickup_location: "", delivery_location: "", commodity: "", equipment_type: "", weight_lbs: "" });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const fetchLoads = async () => {
    const params = {};
    if (q) params.q = q;
    if (statusFilter) params.status = statusFilter;
    const res = await api.get("/loads", { params });
    setLoads(res.data);
  };

  useEffect(() => { fetchLoads(); }, [q, statusFilter]);

  const createLoad = async (e) => {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      await api.post("/loads", {
        ...form,
        weight_lbs: Number(form.weight_lbs) || 0,
      });
      setShowCreate(false);
      setForm({ pickup_location: "", delivery_location: "", commodity: "", equipment_type: "", weight_lbs: "" });
      fetchLoads();
    } catch (e2) {
      setErr(e2?.response?.data?.detail || "Failed to create load. You may be missing the load.create permission.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="content">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1>Load board</h1>
          <p className="subtitle">
            {user.account_type === "broker" && "All loads posted by your brokerage."}
            {user.account_type === "carrier" && "Loads assigned to your carrier org."}
            {user.account_type === "shipper" && "Your shipments and their status."}
          </p>
        </div>
        {user.account_type === "broker" && (
          <button className="btn btn-primary" onClick={() => setShowCreate((s) => !s)}>
            {showCreate ? "Cancel" : "+ Post load"}
          </button>
        )}
      </div>

      {showCreate && (
        <div className="panel">
          <h2>New load</h2>
          {err && <div className="error-box">{err}</div>}
          <form onSubmit={createLoad}>
            <div className="form-row">
              <div className="form-group">
                <label>Pickup location</label>
                <input required value={form.pickup_location}
                       onChange={(e) => setForm({ ...form, pickup_location: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Delivery location</label>
                <input required value={form.delivery_location}
                       onChange={(e) => setForm({ ...form, delivery_location: e.target.value })} />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Commodity</label>
                <input value={form.commodity}
                       onChange={(e) => setForm({ ...form, commodity: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Equipment type</label>
                <input value={form.equipment_type} placeholder="dry_van, reefer, flatbed…"
                       onChange={(e) => setForm({ ...form, equipment_type: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Weight (lbs)</label>
                <input type="number" value={form.weight_lbs}
                       onChange={(e) => setForm({ ...form, weight_lbs: e.target.value })} />
              </div>
            </div>
            <button className="btn btn-primary" disabled={busy}>{busy ? "Posting…" : "Post load"}</button>
          </form>
        </div>
      )}

      <div className="panel">
        <div className="form-row" style={{ marginBottom: 4 }}>
          <div className="form-group">
            <label>Search</label>
            <input placeholder="pickup, delivery, commodity…" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          <div className="form-group">
            <label>Status</label>
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="">All statuses</option>
              {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
        </div>
      </div>

      <div className="panel">
        {loads.length === 0 ? (
          <div className="empty-state">No loads match. {user.account_type === "broker" && "Post one to get started."}</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>ID</th><th>Route</th><th>Commodity</th><th>Status</th><th>Compliance</th>
              </tr>
            </thead>
            <tbody>
              {loads.map((l) => (
                <tr key={l.id} className="clickable" onClick={() => nav(`/loads/${l.id}`)}>
                  <td className="mono">#{l.id}</td>
                  <td>{l.pickup_location} → {l.delivery_location}</td>
                  <td>{l.commodity || "—"}</td>
                  <td><span className="status-pill">{l.status}</span></td>
                  <td>
                    {l.compliance_flag
                      ? <span className="status-pill flagged">flagged</span>
                      : <span style={{ color: "var(--text-dim)" }}>ok</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
