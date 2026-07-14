import { useState } from "react";
import api from "../api";
import { useAuth } from "../context/AuthContext";

const TABS = [
  { key: "login", label: "Log in" },
  { key: "broker", label: "New broker" },
  { key: "carrier", label: "New carrier" },
  { key: "shipper", label: "New shipper" },
];

export default function AuthPage() {
  const [tab, setTab] = useState("login");
  const [form, setForm] = useState({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const { applyToken } = useAuth();

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      let res;
      if (tab === "login") {
        res = await api.post("/auth/login", { email: form.email, password: form.password });
      } else if (tab === "shipper") {
        res = await api.post("/auth/signup-shipper", {
          email: form.email, password: form.password, full_name: form.full_name || "",
        });
      } else {
        res = await api.post("/auth/bootstrap-org", {
          org_name: form.org_name,
          org_type: tab, // "broker" | "carrier"
          admin_email: form.email,
          admin_password: form.password,
          admin_full_name: form.full_name || "",
        });
      }
      await applyToken(res.data.access_token);
    } catch (err) {
      setError(err?.response?.data?.detail || "Something went wrong");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="center-screen">
      <div className="auth-card">
        <div className="brand" style={{ marginBottom: 18, fontSize: 16 }}>
          <span className="dot">●</span> LoadFlow
        </div>
        <div className="auth-tabs">
          {TABS.map((t) => (
            <div
              key={t.key}
              className={`auth-tab ${tab === t.key ? "active" : ""}`}
              onClick={() => { setTab(t.key); setError(""); }}
            >
              {t.label}
            </div>
          ))}
        </div>

        {error && <div className="error-box">{error}</div>}

        <form onSubmit={submit}>
          {(tab === "broker" || tab === "carrier") && (
            <div className="form-group">
              <label>{tab === "broker" ? "Brokerage" : "Carrier"} name</label>
              <input required value={form.org_name || ""} onChange={set("org_name")}
                     placeholder={tab === "broker" ? "Acme Brokerage" : "Speedy Carriers"} />
            </div>
          )}
          {tab === "shipper" && (
            <div className="form-group">
              <label>Full name</label>
              <input value={form.full_name || ""} onChange={set("full_name")} placeholder="Jane Shipper" />
            </div>
          )}
          {(tab === "broker" || tab === "carrier") && (
            <div className="form-group">
              <label>Admin full name</label>
              <input value={form.full_name || ""} onChange={set("full_name")} placeholder="Admin name" />
            </div>
          )}
          <div className="form-group">
            <label>Email</label>
            <input required type="email" value={form.email || ""} onChange={set("email")} placeholder="you@company.com" />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input required type="password" value={form.password || ""} onChange={set("password")} placeholder="••••••••" />
          </div>
          <button className="btn btn-primary" style={{ width: "100%", marginTop: 6 }} disabled={busy}>
            {busy ? "Working…" : tab === "login" ? "Log in" : "Create account"}
          </button>
        </form>

        <p style={{ color: "var(--text-dim)", fontSize: 11, marginTop: 16, lineHeight: 1.5 }}>
          Broker/Carrier signup creates a new org with you as its admin.
          Admins invite staff and define custom roles from inside the app.
        </p>
      </div>
    </div>
  );
}
