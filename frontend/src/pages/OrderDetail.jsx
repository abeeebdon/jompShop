import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import Shell from "../components/Shell";
import { api, formatUSD, formatDateTime } from "../lib/api";
import { useAuth } from "../lib/auth-context";
import { StatusPill } from "../components/StatusPill";
import { toast } from "sonner";
import { FileText, Package, Truck, CheckCircle, Warning, Clock, CurrencyDollar, Download } from "@phosphor-icons/react";

const LIFECYCLE = ["draft", "confirmed", "in_production", "ready_to_ship", "shipped", "delivered"];
const LABELS = {
  draft: "Draft (RFQ)", confirmed: "Confirmed", in_production: "In Production",
  ready_to_ship: "Ready to Ship", shipped: "Shipped", delivered: "Delivered", disputed: "Disputed",
};

export default function OrderDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [disputeOpen, setDisputeOpen] = useState(false);
  const [dispute, setDispute] = useState({ reason: "", description: "" });

  const load = async () => {
    const { data } = await api.get(`/orders/${id}`);
    setData(data);
  };
  useEffect(() => { load(); }, [id]);

  if (!data) return <Shell title="Loading order…"><div/></Shell>;
  const o = data.order;
  const isSupplier = o.supplier_user_id === user.user_id;
  const isBuyer = o.buyer_user_id === user.user_id;

  const issueProforma = async () => {
    try { await api.post(`/orders/${id}/proforma`); toast.success("Proforma issued — buyer notified"); load(); }
    catch (err) { toast.error(err.response?.data?.detail || "Failed"); }
  };
  const simulatePayment = async () => {
    try { const r = await api.post(`/orders/${id}/simulate-payment`); toast.success(`Payment received: ${formatUSD(r.data.amount)}`); load(); }
    catch (err) { toast.error(err.response?.data?.detail || "Failed"); }
  };
  const setStatus = async (status) => {
    try { await api.post(`/orders/${id}/status`, { status }); toast.success(`Status → ${status}`); load(); }
    catch (err) { toast.error(err.response?.data?.detail || "Failed"); }
  };
  const downloadPdf = (kind) => {
    const token = localStorage.getItem("helix_token");
    const url = `${process.env.REACT_APP_BACKEND_URL}/api/orders/${id}/pdf/${kind}`;
    fetch(url, { headers: { Authorization: `Bearer ${token}` }, credentials: "include" })
      .then(r => r.blob())
      .then(b => {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(b);
        a.download = `${o.order_number}-${kind}.pdf`;
        a.click();
      });
  };
  const raiseDispute = async () => {
    try { await api.post(`/orders/${id}/dispute`, dispute); toast.success("Dispute raised"); setDisputeOpen(false); load(); }
    catch (err) { toast.error(err.response?.data?.detail || "Failed"); }
  };

  const currentIdx = LIFECYCLE.indexOf(o.status);

  return (
    <Shell title={o.order_number} kicker={`${LABELS[o.status]} · ${o.product_name}`}
      actions={<div className="flex gap-2 flex-wrap"><StatusPill status={o.status}/><StatusPill status={o.payment_status}/></div>}>
      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {/* lifecycle */}
          <div className="helix-card p-6">
            <div className="helix-label mb-4">Trade Lifecycle</div>
            <div className="flex items-center gap-2 overflow-x-auto">
              {LIFECYCLE.map((s, i) => (
                <div key={s} className="flex items-center gap-2 flex-shrink-0">
                  <div className={`w-7 h-7 rounded-full flex items-start justify-center pt-16 pb-10 overflow-y-auto ${i <= currentIdx ? "bg-[#C9922A] text-[#0A1628]" : "bg-[#0A1628] border border-[#1A7A6E]/40 text-[#9CA3AF]"}`}>
                    {i <= currentIdx ? <CheckCircle size={14} weight="fill"/> : <span className="text-[11px] font-mono">{i+1}</span>}
                  </div>
                  <div className="text-[11px] uppercase tracking-wider whitespace-nowrap" style={{ color: i <= currentIdx ? "#F5F5F5" : "#9CA3AF"}}>{LABELS[s]}</div>
                  {i < LIFECYCLE.length - 1 && <div className={`w-6 h-px ${i < currentIdx ? "bg-[#C9922A]" : "bg-[#1A7A6E]/30"}`}/>}
                </div>
              ))}
            </div>
          </div>

          {/* supplier actions */}
          {(isSupplier || isBuyer) && (
            <div className="helix-card p-6">
              <div className="helix-label mb-3">Actions</div>
              <div className="flex flex-wrap gap-2">
                {isSupplier && o.status === "draft" && (
                  <button onClick={issueProforma} className="helix-btn-primary" data-testid="issue-proforma-btn">Issue Proforma Invoice</button>
                )}
                {isBuyer && o.payment_status !== "confirmed" && o.status === "confirmed" && (
                  <button onClick={simulatePayment} className="helix-btn-primary" data-testid="simulate-pay-btn">
                    Simulate Payment (MOCK)
                  </button>
                )}
                {isSupplier && o.status !== "draft" && o.status !== "disputed" && o.status !== "delivered" && (
                  <>
                    {LIFECYCLE.slice(currentIdx + 1, currentIdx + 2).map((s) => (
                      <button key={s} onClick={() => setStatus(s)} className="helix-btn-secondary" data-testid={`advance-${s}`}>Mark {LABELS[s]}</button>
                    ))}
                  </>
                )}
                <button onClick={() => setDisputeOpen(true)} className="helix-btn-secondary !border-[#E74C3C]/60 !text-[#E74C3C]" data-testid="raise-dispute">Raise dispute</button>
              </div>
            </div>
          )}

          {/* Documents */}
          <div className="helix-card p-6">
            <div className="helix-label mb-3">Trade Documents</div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { kind: "proforma", label: "Proforma Invoice", icon: FileText },
                { kind: "commercial", label: "Commercial Invoice", icon: FileText },
                { kind: "packing", label: "Packing List", icon: Package },
                { kind: "origin", label: "Certificate of Origin", icon: Truck },
              ].map((d) => {
                const Icon = d.icon;
                return (
                  <button key={d.kind} onClick={() => downloadPdf(d.kind)} data-testid={`pdf-${d.kind}`}
                          className="p-4 border border-[#1A7A6E]/30 rounded hover:border-[#C9922A] hover:bg-[#C9922A]/5 transition text-left">
                    <Icon size={20} className="text-[#C9922A] mb-2"/>
                    <div className="text-[12px] font-medium">{d.label}</div>
                    <div className="text-[10px] text-[#9CA3AF] flex items-center gap-1 mt-1"><Download size={10}/>Download PDF</div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* timeline */}
          <div className="helix-card p-6">
            <div className="helix-label mb-3">Timeline</div>
            <div className="space-y-3">
              {(o.timeline || []).slice().reverse().map((t, i) => (
                <div key={i} className="flex gap-3">
                  <div className="w-2 h-2 rounded-full bg-[#1A7A6E] mt-2 flex-shrink-0"/>
                  <div>
                    <div className="text-[13px]">{t.event.replace(/_/g, " ").replace(/status:/, "→ ")}</div>
                    <div className="text-[11px] text-[#9CA3AF] font-mono">{formatDateTime(t.at)}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="helix-card p-6">
            <div className="helix-label">Order Value</div>
            <div className="font-mono text-3xl text-[#C9922A] font-bold mt-1">{formatUSD(o.agreed_price_usd)}</div>
            <div className="text-[12px] text-[#9CA3AF]">{o.quantity} × {formatUSD(o.unit_price_usd)}</div>
          </div>
          {o.anchor_reserved_account_number && (
            <div className="helix-card p-6">
              <div className="helix-label">Payment Instructions</div>
              <div className="mt-3 p-3 bg-[#0A1628] rounded border border-[#C9922A]/30 font-mono text-[13px]">
                <div className="text-[10px] tracking-widest text-[#9CA3AF] mb-1">VIRTUAL ACCOUNT (USD)</div>
                <div className="text-[#C9922A] text-base">{o.anchor_reserved_account_number}</div>
                <div className="text-[11px] text-[#9CA3AF] mt-1">Anchor Reserved · FBO Helix</div>
              </div>
              <div className="text-[11px] text-[#9CA3AF] mt-3">
                Send <span className="text-[#C9922A] font-mono">{formatUSD(o.agreed_price_usd)}</span> exactly. Payment auto-reconciles via Anchor webhook.
              </div>
            </div>
          )}
          <div className="helix-card p-6">
            <div className="helix-label">Parties</div>
            <div className="mt-3 space-y-3 text-[13px]">
              <div>
                <div className="text-[10px] text-[#9CA3AF] tracking-widest">SUPPLIER</div>
                <div>{data.supplier?.business_name}</div>
                <div className="text-[11px] text-[#9CA3AF]">{data.supplier?.country}</div>
              </div>
              <div>
                <div className="text-[10px] text-[#9CA3AF] tracking-widest">BUYER</div>
                <div>{data.buyer?.business_name}</div>
                <div className="text-[11px] text-[#9CA3AF]">{data.buyer?.country}</div>
              </div>
              <div>
                <div className="text-[10px] text-[#9CA3AF] tracking-widest">DELIVERY ADDRESS</div>
                <div className="text-[12px]">{o.delivery_address}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {disputeOpen && (
        <div className="fixed inset-0 bg-[#0A1628]/80 flex items-start justify-center pt-16 pb-10 overflow-y-auto z-50 p-4" onClick={() => setDisputeOpen(false)}>
          <div onClick={(e)=>e.stopPropagation()} className="helix-card w-full max-w-md p-6">
            <h3 className="helix-h3">Raise dispute</h3>
            <div className="space-y-3 mt-4">
              <div><label className="helix-label">Reason</label><input className="helix-input" value={dispute.reason} onChange={(e)=>setDispute({...dispute, reason: e.target.value})} data-testid="dispute-reason"/></div>
              <div><label className="helix-label">Description</label><textarea className="helix-input h-24" value={dispute.description} onChange={(e)=>setDispute({...dispute, description: e.target.value})} data-testid="dispute-desc"/></div>
              <div className="flex gap-2"><button onClick={()=>setDisputeOpen(false)} className="helix-btn-secondary flex-1">Cancel</button><button onClick={raiseDispute} className="helix-btn-primary flex-1" data-testid="dispute-submit">Submit</button></div>
            </div>
          </div>
        </div>
      )}
    </Shell>
  );
}
