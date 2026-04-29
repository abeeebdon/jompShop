import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Shell from "../components/Shell";
import { api, formatUSD, formatDateTime } from "../lib/api";
import { StatusPill } from "../components/StatusPill";
import { toast } from "sonner";
import { HandCoins, TrendUp, CheckCircle, Warning, ArrowRight } from "@phosphor-icons/react";

export default function Credit() {
  const [elig, setElig] = useState(null);
  const [apps, setApps] = useState([]);
  const [open, setOpen] = useState(false);

  const load = async () => {
    const [e, a] = await Promise.all([api.get("/credit/eligibility"), api.get("/credit/applications/mine")]);
    setElig(e.data); setApps(a.data);
  };
  useEffect(() => { load(); }, []);

  if (!elig) return <Shell title="Business Credit · JompStart"><div/></Shell>;

  return (
    <Shell title="Business Credit" kicker="JompStart Digital · Export Financing"
      actions={
        elig.eligible ? (
          <button onClick={() => setOpen(true)} className="helix-btn-primary inline-flex items-center gap-2" data-testid="apply-credit-btn">
            <HandCoins size={14}/> Apply for credit
          </button>
        ) : null
      }>

      {/* Partner banner */}
      <div className="helix-card p-6 mb-6 relative overflow-hidden">
        <div className="absolute -top-10 -right-10 w-64 h-64 rounded-full bg-[#C9922A]/10 blur-3xl pointer-events-none"/>
        <div className="flex items-start gap-4 relative">
          <div className="w-12 h-12 rounded-md flex items-start justify-center pt-16 pb-10 overflow-y-auto font-bold text-[#0A1628] text-lg" style={{ background: "linear-gradient(135deg,#C9922A,#1A7A6E)" }}>J</div>
          <div className="flex-1">
            <div className="helix-kicker">Credit · Technology Partner</div>
            <h2 className="helix-h3 mt-1">JompStart Digital Limited</h2>
            <p className="text-[13px] text-[#9CA3AF] mt-2 max-w-2xl leading-relaxed">
              JompStart builds &amp; maintains Helix alongside our operating partners, and — as the platform&rsquo;s business-credit partner —
              offers working-capital financing to exporters against their verified sales history on Helix.
            </p>
          </div>
        </div>
      </div>

      {/* Eligibility block */}
      <div className="grid lg:grid-cols-3 gap-4 mb-8">
        <div className="helix-card p-6">
          <div className="helix-label">Eligibility</div>
          <div className="mt-3 flex items-center gap-3">
            {elig.eligible ? (
              <><CheckCircle size={28} weight="fill" className="text-[#1A7A6E]"/><span className="helix-h3">Approved to apply</span></>
            ) : (
              <><Warning size={28} weight="fill" className="text-[#C9922A]"/><span className="helix-h3">Not yet eligible</span></>
            )}
          </div>
          {!elig.eligible && elig.reasons_blocked?.length > 0 && (
            <ul className="mt-4 space-y-1.5 text-[12px] text-[#9CA3AF]">
              {elig.reasons_blocked.map((r) => <li key={r}>• {r}</li>)}
            </ul>
          )}
        </div>

        <div className="helix-card p-6">
          <div className="helix-label">Indicative credit limit</div>
          <div className="font-mono text-4xl font-bold text-[#C9922A] mt-2 tracking-tight" data-testid="credit-limit">
            {formatUSD(elig.max_limit_usd || 0)}
          </div>
          {elig.indicative_apr_percent !== null && elig.indicative_apr_percent !== undefined && (
            <div className="text-[12px] text-[#9CA3AF] mt-1 font-mono">
              APR ~{elig.indicative_apr_percent}% · {elig.indicative_term_months}mo · Risk score {elig.risk_score}/100
            </div>
          )}
          <div className="mt-4 h-1.5 bg-[#0A1628] rounded overflow-hidden">
            <div className="h-full bg-gradient-to-r from-[#1A7A6E] to-[#C9922A]" style={{ width: `${elig.risk_score || 0}%` }}/>
          </div>
        </div>

        <div className="helix-card p-6">
          <div className="helix-label">Sales basis (Helix history)</div>
          <div className="mt-3 space-y-2 text-[13px]">
            <Row k="Paid orders" v={<span className="font-mono">{elig.sales?.paid_order_count ?? 0}</span>}/>
            <Row k="Total volume" v={<span className="font-mono text-[#C9922A]">{formatUSD(elig.sales?.total_volume_usd || 0)}</span>}/>
            <Row k="Average order" v={<span className="font-mono">{formatUSD(elig.sales?.average_order_usd || 0)}</span>}/>
            <Row k="Compliance" v={<span className="font-mono">{elig.compliance_score}/100</span>}/>
          </div>
        </div>
      </div>

      {/* Applications list */}
      <div className="helix-card overflow-hidden">
        <div className="px-5 py-4 border-b border-[#1A7A6E]/20">
          <div className="helix-label">My Applications</div>
          <div className="helix-h3 mt-1">{apps.length} application(s)</div>
        </div>
        {apps.length === 0 ? (
          <div className="p-12 text-center text-[#9CA3AF]">
            No credit applications yet. {elig.eligible ? "Apply to unlock working capital against your export sales." : "Complete your first paid order to apply."}
          </div>
        ) : (
          <table className="helix-table">
            <thead>
              <tr><th>Application</th><th>Amount</th><th>Term</th><th>APR</th><th>Status</th><th>Submitted</th><th></th></tr>
            </thead>
            <tbody>
              {apps.map((a) => (
                <tr key={a.id} data-testid={`app-${a.id}`}>
                  <td><Link to={`/credit/${a.id}`} className="font-mono text-[#C9922A]">{a.application_number}</Link></td>
                  <td className="font-mono">{formatUSD(a.offered_amount_usd || a.amount_usd)}</td>
                  <td className="font-mono">{a.offered_term_months || a.term_months}mo</td>
                  <td className="font-mono">{a.offered_apr || a.indicative_apr || "—"}%</td>
                  <td><StatusPill status={a.status}/></td>
                  <td className="text-[11px] font-mono text-[#9CA3AF]">{formatDateTime(a.created_at)}</td>
                  <td><Link to={`/credit/${a.id}`} className="text-[#C9922A] text-[12px] inline-flex items-center gap-1">View <ArrowRight size={12}/></Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {open && <ApplyModal elig={elig} onClose={() => { setOpen(false); load(); }}/>}
    </Shell>
  );
}

function Row({ k, v }) {
  return <div className="flex justify-between items-center"><span className="text-[#9CA3AF] text-[12px]">{k}</span>{v}</div>;
}

function ApplyModal({ elig, onClose }) {
  const [amount, setAmount] = useState(Math.min(10_000, elig.max_limit_usd));
  const [term, setTerm] = useState(elig.indicative_term_months || 6);
  const [purpose, setPurpose] = useState("Export production financing");
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    setBusy(true);
    try {
      await api.post("/credit/applications", { amount_usd: Number(amount), term_months: Number(term), purpose });
      toast.success("Application submitted — JompStart will review shortly");
      onClose();
    } catch (err) { toast.error(err.response?.data?.detail || "Failed"); }
    finally { setBusy(false); }
  };
  return (
    <div className="fixed inset-0 bg-[#0A1628]/80 flex items-start justify-center pt-16 pb-10 overflow-y-auto z-50 p-4" onClick={onClose}>
      <div onClick={(e)=>e.stopPropagation()} className="helix-card p-6 w-full max-w-md fade-up" data-testid="apply-modal">
        <div className="helix-kicker">JompStart Digital</div>
        <h2 className="helix-h3 mt-1">Apply for credit</h2>
        <div className="mt-5 space-y-4">
          <div>
            <label className="helix-label">Amount (USD)</label>
            <input type="number" className="helix-input" value={amount} onChange={(e)=>setAmount(e.target.value)} max={elig.max_limit_usd} data-testid="apply-amount"/>
            <div className="text-[11px] text-[#9CA3AF] mt-1 font-mono">Max indicative: {formatUSD(elig.max_limit_usd)}</div>
          </div>
          <div>
            <label className="helix-label">Term (months)</label>
            <select className="helix-input" value={term} onChange={(e)=>setTerm(e.target.value)} data-testid="apply-term">
              {[3,6,9,12].map(t => <option key={t} value={t}>{t} months</option>)}
            </select>
          </div>
          <div>
            <label className="helix-label">Purpose of funds</label>
            <textarea className="helix-input h-20" value={purpose} onChange={(e)=>setPurpose(e.target.value)} data-testid="apply-purpose"/>
          </div>
          <div className="text-[11px] text-[#9CA3AF] border-t border-[#1A7A6E]/15 pt-3 leading-relaxed">
            By submitting, you authorise JompStart Digital to review your Helix sales history, KYB records, and compliance profile.
            An indicative APR of ~{elig.indicative_apr_percent}% is subject to final review.
          </div>
          <div className="flex gap-2">
            <button onClick={onClose} className="helix-btn-secondary flex-1">Cancel</button>
            <button onClick={submit} disabled={busy} className="helix-btn-primary flex-1" data-testid="apply-submit">{busy ? "Submitting…" : "Submit application"}</button>
          </div>
        </div>
      </div>
    </div>
  );
}
