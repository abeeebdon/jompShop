import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import Shell from "../components/Shell";
import { api, formatUSD, formatNGN } from "../lib/api";
import { useAuth } from "../lib/auth-context";
import { toast } from "sonner";
import { StatusPill } from "../components/StatusPill";
import { CheckCircle, Warehouse, MapPin } from "@phosphor-icons/react";

export default function ProductDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const nav = useNavigate();
  const [data, setData] = useState(null);
  const [open, setOpen] = useState(false);
  const [rfq, setRfq] = useState({ quantity: 10, delivery_address: "", target_delivery_date: "", message: "" });

  useEffect(() => {
    (async () => {
      const { data } = await api.get(`/products/${id}`);
      setData(data);
      setRfq((r) => ({ ...r, quantity: data.product.min_order_qty || 10 }));
    })();
  }, [id]);

  const submitRfq = async () => {
    try {
      const { data } = await api.post("/rfq", { product_id: id, ...rfq });
      toast.success(`RFQ ${data.order_number} submitted`);
      nav(`/orders/${data.id}`);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to submit RFQ");
    }
  };

  if (!data) return <Shell title="Loading…"><div/></Shell>;
  const p = data.product;
  const s = data.supplier || {};
  const canRfq = user && user.role === "buyer" && user.business_id;

  return (
    <Shell title={p.name} kicker={`${p.category.replace("-"," ").toUpperCase()} · ${s.country || ""}`}>
      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 helix-card overflow-hidden">
          <div className="aspect-[16/9] bg-[#0A1628]">
            <img src={p.photos?.[0]} alt={p.name} className="w-full h-full object-cover"/>
          </div>
          <div className="p-6">
            <div className="flex flex-wrap gap-2 mb-4">
              {p.compliance_badges?.map((b) => <span key={b} className="helix-status helix-status-gold">{b}</span>)}
              {p.export_readiness_score >= 80 && <span className="helix-status helix-status-ok"><CheckCircle size={10} weight="fill"/> EXPORT READY · {p.export_readiness_score}/100</span>}
            </div>
            <p className="text-[15px] leading-relaxed text-[#F5F5F5]">{p.description}</p>
            <div className="grid grid-cols-3 gap-4 mt-6 pt-6 border-t border-[#1A7A6E]/15">
              <Meta label="Min Order Qty" value={`${p.min_order_qty} ${p.unit}`}/>
              <Meta label="Unit" value={p.unit}/>
              <Meta label="Status" value={<StatusPill status={p.status} />}/>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="helix-card p-6">
            <div className="helix-label">Price per {p.unit}</div>
            <div className="font-mono text-4xl text-[#C9922A] font-bold mt-1">{formatUSD(p.price_usd)}</div>
            <div className="text-[12px] text-[#9CA3AF] font-mono">{formatNGN(p.price_ngn)}</div>
            {canRfq ? (
              <button onClick={() => setOpen(true)} className="helix-btn-primary w-full mt-5" data-testid="rfq-open-btn">
                Request quotation
              </button>
            ) : user && user.role === "exporter" ? (
              <div className="mt-5 text-[12px] text-[#9CA3AF]">Exporter view — buyers can RFQ.</div>
            ) : (
              <a href="/login" className="helix-btn-primary w-full mt-5 text-center block">Sign in to RFQ</a>
            )}
          </div>

          <div className="helix-card p-6">
            <div className="helix-label">Supplier</div>
            <div className="helix-h3 mt-1">{s.business_name}</div>
            <div className="mt-3 space-y-2 text-[13px] text-[#9CA3AF]">
              <div className="flex items-center gap-2"><MapPin size={14}/>{s.country} · {s.address || "—"}</div>
              <div className="flex items-center gap-2"><Warehouse size={14}/>Score: <span className="text-[#C9922A] font-mono">{s.compliance_score}/100</span></div>
              <div className="flex gap-2 pt-2">
                <StatusPill status={s.kyb_status || s.kyc_status}/>
                {s.anchor_customer_id && <span className="helix-status helix-status-gold">ANCHOR VERIFIED</span>}
              </div>
            </div>
          </div>
        </div>
      </div>

      {open && (
        <div className="fixed inset-0 bg-[#0A1628]/80 backdrop-blur flex items-center justify-center z-50 p-4" onClick={() => setOpen(false)}>
          <div onClick={(e) => e.stopPropagation()} className="helix-card w-full max-w-md p-6 fade-up" data-testid="rfq-modal">
            <div className="helix-label">Request Quotation</div>
            <h2 className="helix-h3 mt-1">{p.name}</h2>
            <div className="mt-5 space-y-4">
              <div>
                <label className="helix-label">Quantity</label>
                <input type="number" min={p.min_order_qty} className="helix-input" value={rfq.quantity} onChange={(e)=>setRfq({...rfq, quantity: Number(e.target.value)})} data-testid="rfq-qty"/>
                <div className="text-[11px] text-[#9CA3AF] mt-1 font-mono">Est: {formatUSD((rfq.quantity || 0) * p.price_usd)}</div>
              </div>
              <div>
                <label className="helix-label">Delivery address</label>
                <input className="helix-input" value={rfq.delivery_address} onChange={(e)=>setRfq({...rfq, delivery_address: e.target.value})} required data-testid="rfq-address"/>
              </div>
              <div>
                <label className="helix-label">Target delivery date</label>
                <input type="date" className="helix-input" value={rfq.target_delivery_date} onChange={(e)=>setRfq({...rfq, target_delivery_date: e.target.value})} data-testid="rfq-date"/>
              </div>
              <div>
                <label className="helix-label">Message to supplier</label>
                <textarea className="helix-input h-20" value={rfq.message} onChange={(e)=>setRfq({...rfq, message: e.target.value})} data-testid="rfq-message"/>
              </div>
              <div className="flex gap-3">
                <button onClick={() => setOpen(false)} className="helix-btn-secondary flex-1">Cancel</button>
                <button onClick={submitRfq} className="helix-btn-primary flex-1" data-testid="rfq-submit">Submit RFQ</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </Shell>
  );
}

function Meta({ label, value }) {
  return (
    <div>
      <div className="helix-label">{label}</div>
      <div className="text-[14px] mt-1">{value}</div>
    </div>
  );
}
