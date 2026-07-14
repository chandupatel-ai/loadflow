import { useEffect, useState } from "react";
import api from "../api";
import { useAuth } from "../context/AuthContext";

export default function CompliancePage() {
  const { user } = useAuth();
  const [form, setForm] = useState({
    insurance_expiry: "", mc_dot_authority_status: "active",
    approved_equipment_types: "", approved_commodity_types: "",
  });
  const [current, setCurrent] = useState(null);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  const load = async () => {
    try {
      const r = await api.get("/compliance/me");
      setCurrent(r.data);
      setForm({
        insurance_expiry: r.data.insurance_expiry ? r.data.insurance_expiry.slice(0, 10) : "",
        mc_dot_authority_status: r.data.mc_dot_authority_status,
        approved_equipment_types: r.data.approved_equipment_types.join(", "),
        approved_commodity_types: r.data.approved_commodity_types.join(", "),
      });
    } catch { /* none yet */ }
  };

  useEffect(() => { load(); }, []);

  if (user.account_type !== "carrier") {
    return <div className="content"><div className="error-box">Only carrier accounts have a compliance record.</div></div>;
  }

  const save = async (e) => {
    e.preventDefault();
    setErr(""); setMsg("");
    try {
      await api.put("/compliance/me", {
        insurance_expiry: form.insurance_expiry ? `${form.insurance_expiry}T00:00:00` : null,
        mc_dot_authority_status: form.mc_dot_authority_status,
        approved_equipment_types: form.approved_equipment_types.split(",").map((s) => s.trim()).filter(Boolean),
        approved_commodity_types: form.approved_commodity_types.split(",").map((s) => s.trim()).filter(Boolean),
      });
      setMsg("Compliance record saved.");
      load();
    } catch (e2) { setErr(e2?.response?.data?.detail || "Failed to save"); }
  };

  return (
    <div className="content">
      <h1>Carrier compliance</h1>
      <p className="subtitle">
        This record gates whether your carrier org can be assigned loads without blocking their
        progression. Keep insurance expiry and authority status current.
      </p>

      {current && (
        <div className={current.is_compliant ? "info-box" : "error-box"}>
          {current.is_compliant ? "✓ Currently compliant" : "⚠ Currently NON-compliant — new load assignments will be flagged"}
        </div>
      )}
      {err && <div className="error-box">{err}</div>}
      {msg && <div className="info-box">{msg}</div>}

      <div className="panel">
        <form onSubmit={save}>
          <div className="form-row">
            <div className="form-group">
              <label>Insurance expiry</label>
              <input type="date" value={form.insurance_expiry}
                     onChange={(e) => setForm({ ...form, insurance_expiry: e.target.value })} />
            </div>
            <div className="form-group">
              <label>MC/DOT authority status</label>
              <select value={form.mc_dot_authority_status}
                      onChange={(e) => setForm({ ...form, mc_dot_authority_status: e.target.value })}>
                <option value="active">Active</option>
                <option value="expired">Expired</option>
                <option value="suspended">Suspended</option>
              </select>
            </div>
          </div>
          <div className="form-group">
            <label>Approved equipment types (comma-separated)</label>
            <input value={form.approved_equipment_types} placeholder="dry_van, reefer, flatbed"
                   onChange={(e) => setForm({ ...form, approved_equipment_types: e.target.value })} />
          </div>
          <div className="form-group">
            <label>Approved commodity types (comma-separated)</label>
            <input value={form.approved_commodity_types} placeholder="general, hazmat, perishable"
                   onChange={(e) => setForm({ ...form, approved_commodity_types: e.target.value })} />
          </div>
          <button className="btn btn-primary">Save compliance record</button>
        </form>
      </div>
    </div>
  );
}
