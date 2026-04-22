import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth-context";
import { AuthShell } from "./Login";
import { toast } from "sonner";

export default function Register() {
  const { register } = useAuth();
  const nav = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "exporter" });
  const [busy, setBusy] = useState(false);

  const upd = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const user = await register(form);
          toast.success(`Welcome to Jomp Trade, ${user.name.split(" ")[0]}`);
      if (user.role === "consumer") nav("/shop"); else nav("/onboarding");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Register failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell>
      <div className="w-full max-w-md helix-card p-8 fade-up">
        <div className="helix-kicker mb-2">Jomp Trade · Create account</div>
        <h1 className="helix-h2">Start trading in minutes</h1>
        <p className="text-[#9CA3AF] text-sm mt-2">Open your business profile, upload CAC, receive USD.</p>
        <form onSubmit={submit} className="mt-7 space-y-4" data-testid="register-form">
          <div>
            <label className="helix-label">Full name</label>
            <input data-testid="reg-name" className="helix-input" value={form.name} onChange={upd("name")} required />
          </div>
          <div>
            <label className="helix-label">Email</label>
            <input data-testid="reg-email" type="email" className="helix-input" value={form.email} onChange={upd("email")} required />
          </div>
          <div>
            <label className="helix-label">Password</label>
            <input data-testid="reg-password" type="password" className="helix-input" value={form.password} onChange={upd("password")} required minLength={6} />
          </div>
          <div>
            <label className="helix-label">I am registering as</label>
            <select data-testid="reg-role" className="helix-input" value={form.role} onChange={upd("role")}>
              <option value="exporter">Exporter / Supplier (Business)</option>
              <option value="buyer">Buyer / Importer (Business)</option>
              <option value="consumer">Consumer — just shopping</option>
            </select>
          </div>
          <button data-testid="register-submit" disabled={busy} className="helix-btn-primary w-full">
            {busy ? "Creating…" : "Create account"}
          </button>
        </form>
        <div className="mt-8 text-center text-[13px] text-[#9CA3AF]">
          Already have an account? <Link to="/login" className="text-[#C9922A] font-semibold">Sign in</Link>
        </div>
      </div>
    </AuthShell>
  );
}
