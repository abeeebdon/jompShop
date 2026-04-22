import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../lib/auth-context";
import { toast } from "sonner";
import { GoogleLogo } from "@phosphor-icons/react";

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
function startEmergentOAuth() {
  const redirect = window.location.origin + "/dashboard";
  window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirect)}`;
}

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const user = await login(email, password);
      toast.success(`Welcome back, ${user.name.split(" ")[0]}`);
      const to = loc.state?.from || (["admin", "super_admin"].includes(user.role) ? "/admin" : "/dashboard");
      nav(to, { replace: true });
    } catch (err) {
      toast.error(err.response?.data?.detail || "Login failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell>
      <div className="w-full max-w-md helix-card p-8 fade-up">
        <div className="helix-kicker mb-2">Helix · Sign in</div>
        <h1 className="helix-h2">Access your command center</h1>
        <p className="text-[#9CA3AF] text-sm mt-2">Exporter, buyer, or admin &mdash; one login.</p>

        <form onSubmit={submit} className="mt-7 space-y-4" data-testid="login-form">
          <div>
            <label className="helix-label">Email</label>
            <input data-testid="login-email" className="helix-input" value={email} onChange={(e) => setEmail(e.target.value)} required type="email" placeholder="you@company.com" />
          </div>
          <div>
            <label className="helix-label">Password</label>
            <input data-testid="login-password" className="helix-input" value={password} onChange={(e) => setPassword(e.target.value)} required type="password" placeholder="••••••••" />
          </div>
          <button data-testid="login-submit" disabled={busy} className="helix-btn-primary w-full">
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <div className="flex items-center gap-3 my-6 text-[11px] font-mono tracking-widest text-[#9CA3AF]">
          <div className="flex-1 h-px bg-[#1A7A6E]/25" /> OR <div className="flex-1 h-px bg-[#1A7A6E]/25" />
        </div>

        <button
          data-testid="google-login-btn"
          onClick={startEmergentOAuth}
          className="w-full flex items-center justify-center gap-3 border border-[#1A7A6E]/40 rounded px-4 py-3 text-sm font-medium hover:bg-[#1A7A6E]/10 transition"
        >
          <GoogleLogo size={18} /> Continue with Google
        </button>

        <div className="mt-8 text-center text-[13px] text-[#9CA3AF]">
          New to Helix? <Link to="/register" className="text-[#C9922A] font-semibold">Create an account</Link>
        </div>

        <div className="mt-8 p-4 rounded bg-[#0A1628] border border-dashed border-[#1A7A6E]/30 text-[11px] text-[#9CA3AF] font-mono space-y-1">
          <div className="text-[#C9922A]">DEMO ACCOUNTS</div>
          <div>exporter@helix.com · Helix@123</div>
          <div>buyer@helix.com · Helix@123</div>
          <div>admin@helix.com · Helix@123</div>
        </div>
      </div>
    </AuthShell>
  );
}

export function AuthShell({ children }) {
  return (
    <div className="min-h-screen bg-[#0A1628] text-[#F5F5F5] flex">
      <div className="hidden md:flex md:w-1/2 relative overflow-hidden border-r border-[#1A7A6E]/20">
        <div className="absolute inset-0 helix-dot-bg" />
        <div className="relative z-10 flex flex-col justify-between p-10 w-full">
          <Link to="/" className="flex items-center gap-3" data-testid="brand-auth">
            <div className="w-8 h-8 rounded-sm" style={{ background: "linear-gradient(135deg,#C9922A,#1A7A6E)" }}/>
            <div>
              <div className="font-bold tracking-[0.22em] text-sm">HELIX</div>
              <div className="text-[10px] tracking-[0.3em] text-[#1A7A6E] font-mono">PLATFORM</div>
            </div>
          </Link>
          <div>
            <div className="helix-kicker mb-3">Export Operating System</div>
            <h2 className="helix-h2 max-w-md">One login. Four roles. Every trade in one command center.</h2>
            <p className="text-[#9CA3AF] mt-4 text-sm max-w-md">Operated by DobbleHelix Limited &amp; Riby Inc · Banking powered by GetAnchor.</p>
          </div>
          <div className="font-mono text-[11px] text-[#1A7A6E] tracking-widest">© 2026 · HELIX v1.0</div>
        </div>
      </div>
      <div className="flex-1 flex items-center justify-center p-6">
        {children}
      </div>
    </div>
  );
}
