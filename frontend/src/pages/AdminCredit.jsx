import { useEffect, useState } from "react";
import Shell from "../components/Shell";
import { api, formatUSD, formatDateTime } from "../lib/api";
import { StatusPill } from "../components/StatusPill";
import { toast } from "sonner";

export default function AdminCredit() {
  const [apps, setApps] = useState([]);
  const [selected, setSelected] = useState(null);
  const [offer, setOffer] = useState({ offered_amount_usd: "", offered_apr: "", offered_term_months: "", decision_note: "" });
  const load = async () => { const { data } = await api.get("/credit/admin/applications"); setApps(data); };
  useEffect(() => { load(); }, []);

  const decide = async (decision) => {
    try {
      const payload = decision === "offered"
        ? { decision, ...offer, offered_amount_usd: Number(offer.offered_amount_usd || selected.amount_usd), offered_apr: Number(offer.offered_apr || selected.indicative_apr), offered_term_months: Number(offer.offered_term_months || selected.term_months) }
        : { decision, decision_note: offer.decision_note };
      await api.post(`/credit/admin/applications/${selected.id}/decision`, payload);
      toast.success(`Marked ${decision}`);
      setSelected(null); setOffer({ offered_amount_usd: "", offered_apr: "", offered_term_months: "", decision_note: "" });
      load();
    } catch (err) { toast.error(err.response?.data?.detail || "Failed"); }
  };

  return (
    <Shell title="JompStart Credit Queue" kicker="Business Credit · Admin">
      {apps.length === 0 ? (
        <div className="helix-card p-12 text-center text-[#9CA3AF]">No credit applications submitted yet.</div>
      ) : (
        <div className="helix-card overflow-hidden">
          <table className="helix-table">
            <thead><tr><th>App</th><th>Business</th><th>Country</th><th>Requested</th><th>APR</th><th>Risk</th><th>Status</th><th>Submitted</th><th></th></tr></thead>
            <tbody>
              {apps.map((a) => (
                <tr key={a.id} data-testid={`admin-app-${a.id}`}>
                  <td className="font-mono text-[#C9922A]">{a.application_number}</td>
                  <td>{a.business_name}</td>
                  <td className="text-[12px] text-[#9CA3AF]">{a.business_country}</td>
                  <td className="font-mono">{formatUSD(a.amount_usd)}</td>
                  <td className="font-mono">{a.indicative_apr}%</td>
                  <td className="font-mono">{a.risk_score}</td>
                  <td><StatusPill status={a.status}/></td>
                  <td className="text-[11px] font-mono text-[#9CA3AF]">{formatDateTime(a.created_at)}</td>
                  <td>
                    {["submitted", "under_review"].includes(a.status) && (
                      <button onClick={() => { setSelected(a); setOffer({ offered_amount_usd: a.amount_usd, offered_apr: a.indicative_apr, offered_term_months: a.term_months, decision_note: "" }); }}
                              className="text-[#C9922A] text-[12px] hover:underline" data-testid={`decide-${a.id}`}>Review</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selected && (
        <div className="fixed inset-0 bg-[#0A1628]/80 flex items-start justify-center pt-16 pb-10 overflow-y-auto z-50 p-4" onClick={() => setSelected(null)}>
          <div onClick={(e)=>e.stopPropagation()} className="helix-card p-6 w-full max-w-lg">
            <div className="helix-kicker">JompStart · Decision</div>
            <h3 className="helix-h3 mt-1">{selected.application_number} · {selected.business_name}</h3>
            <div className="mt-4 grid grid-cols-3 gap-3 text-[12px]">
              <div><div className="text-[10px] text-[#9CA3AF] tracking-widest">REQUESTED</div><div className="font-mono text-[#F5F5F5]">{formatUSD(selected.amount_usd)}</div></div>
              <div><div className="text-[10px] text-[#9CA3AF] tracking-widest">RISK</div><div className="font-mono text-[#F5F5F5]">{selected.risk_score}/100</div></div>
              <div><div className="text-[10px] text-[#9CA3AF] tracking-widest">SALES VOL</div><div className="font-mono text-[#F5F5F5]">{formatUSD(selected.snapshot_sales?.total_volume_usd || 0)}</div></div>
            </div>
            <div className="mt-5 grid grid-cols-3 gap-3">
              <div><label className="helix-label">Offer amount</label><input type="number" className="helix-input" value={offer.offered_amount_usd} onChange={(e)=>setOffer({...offer, offered_amount_usd: e.target.value})} data-testid="offer-amt"/></div>
              <div><label className="helix-label">APR %</label><input type="number" step="0.01" className="helix-input" value={offer.offered_apr} onChange={(e)=>setOffer({...offer, offered_apr: e.target.value})}/></div>
              <div><label className="helix-label">Term (mo)</label><input type="number" className="helix-input" value={offer.offered_term_months} onChange={(e)=>setOffer({...offer, offered_term_months: e.target.value})}/></div>
            </div>
            <div className="mt-4">
              <label className="helix-label">Decision note (optional)</label>
              <textarea className="helix-input h-20" value={offer.decision_note} onChange={(e)=>setOffer({...offer, decision_note: e.target.value})}/>
            </div>
            <div className="flex gap-2 mt-5">
              <button onClick={() => setSelected(null)} className="helix-btn-secondary flex-1">Cancel</button>
              <button onClick={() => decide("rejected")} className="helix-btn-secondary !border-[#E74C3C] !text-[#E74C3C] flex-1" data-testid="admin-reject">Reject</button>
              <button onClick={() => decide("offered")} className="helix-btn-primary flex-1" data-testid="admin-offer">Extend offer</button>
            </div>
          </div>
        </div>
      )}
    </Shell>
  );
}
