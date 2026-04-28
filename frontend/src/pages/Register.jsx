import { useState, useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../lib/auth-context";
import { AuthShell } from "./Login";
import { toast } from "sonner";
import { ShoppingBag, Storefront, Globe, ArrowLeft, CheckCircle } from "@phosphor-icons/react";

const ROLES = [
  {
    value: "consumer",
    title: "Direct Customer",
    sub: "I'm here to shop",
    blurb: "Buy authentic African goods for personal use. Escrow-protected on every order.",
    Icon: ShoppingBag,
    pill: "Free · most popular",
  },
  {
    value: "buyer",
    title: "Reseller / Bulk Buyer",
    sub: "I import & resell at scale",
    blurb: "Source bulk inventory from verified African suppliers. RFQs, custom quotes, US-bonded warehousing.",
    Icon: Storefront,
    pill: "Business · Importer",
  },
  {
    value: "exporter",
    title: "African Exporter",
    sub: "I'm a maker / supplier from Africa",
    blurb: "List products, sell direct-to-consumer (Riby of record) or wholesale, access JompStart credit.",
    Icon: Globe,
    pill: "Business · Supplier",
  },
];

export default function Register() {
  const { register } = useAuth();
  const nav = useNavigate();
  const [params] = useSearchParams();
  const [step, setStep] = useState("choose"); // choose | form
  const [selected, setSelected] = useState(null);
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [busy, setBusy] = useState(false);

  // Allow pre-selecting role via ?role=xxx
  useEffect(() => {
    const r = params.get("role");
    if (r && ROLES.some((x) => x.value === r)) {
      setSelected(r);
      setStep("form");
    }
  }, [params]);

  const upd = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    if (!selected) return;
    setBusy(true);
    try {
      const user = await register({ ...form, role: selected });
      toast.success(`Welcome to Jomp Shop, ${user.name.split(" ")[0]}`);
      if (user.role === "consumer") nav("/");
      else if (user.role === "jompstart_admin") nav("/admin/credit");
      else nav("/onboarding");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Register failed");
    } finally {
      setBusy(false);
    }
  };

  if (step === "choose") {
    return (
      <AuthShell>
        <div className="w-full max-w-4xl fade-up">
          <div className="text-center mb-8">
            <div className="helix-kicker mb-2">Jomp Shop · Create account</div>
            <h1 className="helix-h2">How would you like to use Jomp Shop?</h1>
            <p className="text-[#9CA3AF] text-sm mt-2">Pick the path that fits — you can change later in settings.</p>
          </div>
          <div className="grid md:grid-cols-3 gap-4">
            {ROLES.map((r) => {
              const Icon = r.Icon;
              const active = selected === r.value;
              return (
                <button
                  key={r.value}
                  onClick={() => setSelected(r.value)}
                  className={`helix-card p-6 text-left transition-all ${active ? "border-[#C9922A] ring-2 ring-[#C9922A]/30" : "hover:border-[#1A7A6E]/60"}`}
                  data-testid={`role-card-${r.value}`}
                >
                  <div className="flex items-start justify-between">
                    <Icon size={30} weight="duotone" className={active ? "text-[#C9922A]" : "text-[#1A7A6E]"}/>
                    {active && <CheckCircle size={18} weight="fill" className="text-[#C9922A]"/>}
                  </div>
                  <div className="mt-5">
                    <div className="helix-h3 text-[16px]">{r.title}</div>
                    <div className="text-[12px] text-[#1A7A6E] font-mono tracking-wider uppercase mt-1">{r.sub}</div>
                  </div>
                  <p className="text-[13px] text-[#9CA3AF] mt-3 leading-relaxed">{r.blurb}</p>
                  <div className="mt-5 inline-flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-wider text-[#C9922A]/80 border border-[#C9922A]/30 rounded-full px-2.5 py-1">
                    {r.pill}
                  </div>
                </button>
              );
            })}
          </div>
          <div className="mt-8 flex items-center justify-center gap-4">
            <button
              disabled={!selected}
              onClick={() => setStep("form")}
              className="helix-btn-primary px-8"
              data-testid="role-continue-btn"
            >
              Continue {selected ? `as ${ROLES.find((x) => x.value === selected).title}` : "→"}
            </button>
          </div>
          <div className="mt-8 text-center text-[13px] text-[#9CA3AF]">
            Already have an account? <Link to="/login" className="text-[#C9922A] font-semibold">Sign in</Link>
          </div>
        </div>
      </AuthShell>
    );
  }

  const sel = ROLES.find((x) => x.value === selected);
  return (
    <AuthShell>
      <div className="w-full max-w-md helix-card p-8 fade-up">
        <button onClick={() => setStep("choose")} className="text-[12px] text-[#9CA3AF] hover:text-[#F5F5F5] inline-flex items-center gap-1.5 mb-4" data-testid="back-to-roles">
          <ArrowLeft size={12}/> change role
        </button>
        <div className="helix-kicker mb-2">Sign up · {sel.title}</div>
        <h1 className="helix-h2">{sel.value === "consumer" ? "Start shopping in seconds" : "Create your business profile"}</h1>
        <p className="text-[#9CA3AF] text-sm mt-2">{sel.blurb}</p>
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
            <div className="text-[11px] text-[#9CA3AF] mt-1.5">At least 6 characters.</div>
          </div>
          <button data-testid="register-submit" disabled={busy} className="helix-btn-primary w-full">
            {busy ? "Creating…" : `Create my ${sel.title} account`}
          </button>
        </form>
        <div className="mt-8 text-center text-[13px] text-[#9CA3AF]">
          Already have an account? <Link to="/login" className="text-[#C9922A] font-semibold">Sign in</Link>
        </div>
      </div>
    </AuthShell>
  );
}
