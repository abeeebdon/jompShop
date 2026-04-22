import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import Shell from "../components/Shell";
import { api, formatUSD, formatDateTime } from "../lib/api";
import { StatusPill } from "../components/StatusPill";
import { toast } from "sonner";
import { CheckCircle } from "@phosphor-icons/react";

export default function CreditDetail() {
  const { id } = useParams();
  const [doc, setDoc] = useState(null);
  const load = async () => { const { data } = await api.get(`/credit/applications/${id}`); setDoc(data); };
  useEffect(() => { load(); }, [id]);
  if (!doc) return <Shell title="Loading…"><div/></Shell>;

  const accept = async () => {
    try { const { data } = await api.post(`/credit/applications/${id}/accept`); toast.success(`Disbursed: ${formatUSD(data.amount_usd)}`); load(); }
    catch (err) { toast.error(err.response?.data?.detail || "Failed"); }
  };

  return (
    <Shell title={doc.application_number} kicker="JompStart Digital · Credit Application"
      actions={<StatusPill status={doc.status}/>}>
      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="helix-card p-6">
            <div className="helix-label mb-3">Application</div>
            <div className="grid sm:grid-cols-2 gap-4">
              <Field label="Requested Amount" value={formatUSD(doc.amount_usd)}/>
              <Field label="Requested Term" value={`${doc.term_months} months`}/>
              <Field label="Indicative APR" value={doc.indicative_apr ? `${doc.indicative_apr}%` : "—"}/>
              <Field label="Risk Score" value={`${doc.risk_score}/100`}/>
              <Field label="Purpose" value={doc.purpose} full/>
            </div>
          </div>

          {doc.status === "offered" && (
            <div className="helix-card p-6 border-[#C9922A]/40 bg-[#C9922A]/5">
              <div className="helix-kicker mb-2">JompStart Offer</div>
              <h3 className="helix-h3">Your application has been approved</h3>
              <div className="grid sm:grid-cols-3 gap-4 mt-4">
                <div>
                  <div className="text-[10px] tracking-widest text-[#9CA3AF]">OFFERED AMOUNT</div>
                  <div className="font-mono text-2xl text-[#C9922A] font-bold">{formatUSD(doc.offered_amount_usd)}</div>
                </div>
                <div>
                  <div className="text-[10px] tracking-widest text-[#9CA3AF]">APR</div>
                  <div className="font-mono text-2xl font-bold">{doc.offered_apr}%</div>
                </div>
                <div>
                  <div className="text-[10px] tracking-widest text-[#9CA3AF]">TERM</div>
                  <div className="font-mono text-2xl font-bold">{doc.offered_term_months}mo</div>
                </div>
              </div>
              {doc.decision_note && <p className="text-[#9CA3AF] text-[13px] mt-3">{doc.decision_note}</p>}
              <button onClick={accept} className="helix-btn-primary mt-5" data-testid="accept-offer-btn">
                Accept &amp; receive disbursement
              </button>
              <div className="text-[11px] text-[#9CA3AF] mt-2">Funds credit to your Helix USD account instantly.</div>
            </div>
          )}

          {doc.status === "disbursed" && (
            <div className="helix-card p-6">
              <div className="flex items-start gap-3">
                <CheckCircle size={28} weight="fill" className="text-[#1A7A6E]"/>
                <div>
                  <h3 className="helix-h3">Disbursed</h3>
                  <p className="text-[13px] text-[#9CA3AF] mt-1">Funds have been credited to your USD account. See Finance → Transactions.</p>
                </div>
              </div>
            </div>
          )}

          {doc.status === "rejected" && doc.decision_note && (
            <div className="helix-card p-6 border-[#E74C3C]/40">
              <div className="helix-kicker text-[#E74C3C]">Not Approved</div>
              <p className="text-[14px] mt-2">{doc.decision_note}</p>
            </div>
          )}

          {/* Timeline */}
          <div className="helix-card p-6">
            <div className="helix-label mb-3">Timeline</div>
            <div className="space-y-3">
              {(doc.timeline || []).slice().reverse().map((t, i) => (
                <div key={i} className="flex gap-3">
                  <div className="w-2 h-2 rounded-full bg-[#1A7A6E] mt-2 flex-shrink-0"/>
                  <div>
                    <div className="text-[13px]">{t.event.replace(/_/g, " ").replace(/decision:/, "→ ")}</div>
                    <div className="text-[11px] text-[#9CA3AF] font-mono">{formatDateTime(t.at)}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="helix-card p-6">
            <div className="helix-label">Sales snapshot at application</div>
            <div className="mt-3 space-y-2 text-[13px]">
              <Row k="Paid orders" v={doc.snapshot_sales?.paid_order_count}/>
              <Row k="Total volume" v={formatUSD(doc.snapshot_sales?.total_volume_usd || 0)}/>
              <Row k="Average order" v={formatUSD(doc.snapshot_sales?.average_order_usd || 0)}/>
            </div>
          </div>
          <div className="helix-card p-6">
            <div className="helix-label">Partner</div>
            <div className="mt-3">
              <div className="font-bold tracking-wide text-[#C9922A]">JompStart Digital Limited</div>
              <div className="text-[12px] text-[#9CA3AF] mt-1">Business credit &amp; technology partner of Helix Platform.</div>
            </div>
          </div>
        </div>
      </div>
    </Shell>
  );
}

function Field({ label, value, full }) {
  return (
    <div className={full ? "sm:col-span-2" : ""}>
      <div className="helix-label">{label}</div>
      <div className="text-[14px] mt-1">{value || "—"}</div>
    </div>
  );
}
function Row({ k, v }) {
  return <div className="flex justify-between"><span className="text-[#9CA3AF] text-[12px]">{k}</span><span className="font-mono">{v}</span></div>;
}
