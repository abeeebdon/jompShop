import { useEffect, useState } from "react";
import Shell from "../components/Shell";
import { api, formatUSD, formatDateTime } from "../lib/api";
import { StatusPill } from "../components/StatusPill";
import { toast } from "sonner";
import { Truck, LockKey, CheckCircle, ChatCircle } from "@phosphor-icons/react";

export default function Fulfillment() {
  const [orders, setOrders] = useState([]);
  const [quotes, setQuotes] = useState([]);
  const [respond, setRespond] = useState(null);
  const [form, setForm] = useState({ quoted_unit_price_usd: "", quote_note: "", valid_days: 7 });
  const load = async () => {
    const [o, q] = await Promise.all([api.get("/shop/orders/fulfillment"), api.get("/shop/quotes/mine")]);
    setOrders(o.data); setQuotes(q.data.as_seller || []);
  };
  useEffect(() => { load(); }, []);

  const ship = async (id) => {
    const tn = prompt("Tracking number (leave blank to auto-generate)");
    try {
      await api.post(`/shop/orders/${id}/ship`, { tracking_number: tn || "" });
      toast.success("Marked shipped"); load();
    } catch (err) { toast.error(err.response?.data?.detail || "Failed"); }
  };
  const deliver = async (id) => {
    if (!window.confirm("Mark delivered? This releases the escrow funds to your USD wallet (net of 2% fee).")) return;
    try {
      const { data } = await api.post(`/shop/orders/${id}/delivered`);
      toast.success(data.released ? `Escrow released · ${formatUSD(data.credit_amount_usd)} credited` : "Delivered");
      load();
    } catch (err) { toast.error(err.response?.data?.detail || "Failed"); }
  };

  const sendQuote = async () => {
    try {
      await api.post(`/shop/quotes/${respond.id}/respond`, {
        quoted_unit_price_usd: Number(form.quoted_unit_price_usd),
        quote_note: form.quote_note,
        valid_days: Number(form.valid_days),
      });
      toast.success("Quote sent to consumer");
      setRespond(null); setForm({ quoted_unit_price_usd: "", quote_note: "", valid_days: 7 });
      load();
    } catch (err) { toast.error(err.response?.data?.detail || "Failed"); }
  };

  return (
    <Shell title="Fulfillment Queue" kicker="Consumer orders · Quotes · Escrow">
      {/* Quote requests */}
      {quotes.length > 0 && (
        <div className="mb-8">
          <div className="helix-label mb-3 flex items-center gap-2"><ChatCircle size={14}/> Quote requests</div>
          <div className="space-y-3">
            {quotes.map(q => (
              <div key={q.id} className="helix-card p-5" data-testid={`seller-quote-${q.id}`}>
                <div className="flex items-start justify-between flex-wrap gap-3">
                  <div>
                    <div className="text-[11px] font-mono tracking-widest text-[#1A7A6E]">{q.quote_number}</div>
                    <div className="helix-h3 mt-1">{q.listing_title}</div>
                    <div className="text-[12px] text-[#9CA3AF] mt-1">Qty: {q.quantity} · From {q.consumer_name} &lt;{q.consumer_email}&gt;</div>
                    {q.message && <div className="text-[12px] mt-2 italic">&ldquo;{q.message}&rdquo;</div>}
                    {q.quoted_unit_price_usd && (
                      <div className="mt-2 text-[12px] text-[#C9922A] font-mono">Quoted: {formatUSD(q.quoted_unit_price_usd)} × {q.quantity} = {formatUSD(q.quoted_total_usd)} (valid {q.quote_valid_until})</div>
                    )}
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <StatusPill status={q.status}/>
                    {q.status === "pending" && (
                      <button onClick={() => { setRespond(q); setForm({ quoted_unit_price_usd: q.quantity ? q.quoted_unit_price_usd || "" : "", quote_note: "", valid_days: 7 }); }}
                              className="helix-btn-primary text-sm" data-testid={`respond-${q.id}`}>Respond</button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Orders */}
      {orders.length === 0 ? (
        <div className="helix-card p-12 text-center text-[#9CA3AF]">No consumer orders yet.</div>
      ) : (
        <div className="space-y-4">
          <div className="helix-label mb-1">Orders in fulfillment queue</div>
          {orders.map(o => (
            <div key={o.id} className="helix-card p-5" data-testid={`ff-${o.id}`}>
              <div className="flex items-start justify-between flex-wrap gap-3">
                <div>
                  <div className="text-[11px] font-mono tracking-widest text-[#1A7A6E]">
                    {o.order_number} · {o.checkout_mode === "quote_prepay" ? "QUOTED" : "LISTED"}
                  </div>
                  <div className="helix-h3 mt-1">{o.listing_title}</div>
                  <div className="text-[13px] mt-1 font-mono">
                    {o.quantity} × {formatUSD(o.unit_price_usd)} = <span className="text-[#C9922A]">{formatUSD(o.total_usd)}</span>
                  </div>
                  {o.delivery_partner_of_record && (
                    <div className="mt-2 text-[12px] inline-flex items-center gap-1 text-[#C9922A]">
                      <Truck size={12}/> Delivery partner of record: <b>{o.delivery_partner_of_record}</b>
                    </div>
                  )}
                </div>
                <div className="text-right">
                  <div className="flex flex-col items-end gap-1">
                    <StatusPill status={o.status}/>
                    <span className={`helix-status ${o.escrow_status === "held" ? "helix-status-gold" : "helix-status-ok"}`}>
                      <LockKey size={10}/> ESCROW · {o.escrow_status.toUpperCase()}
                    </span>
                  </div>
                  <div className="text-[11px] text-[#9CA3AF] font-mono mt-1">{formatDateTime(o.created_at)}</div>
                </div>
              </div>
              <div className="mt-4 pt-3 border-t border-[#1A7A6E]/15 text-[12px] text-[#9CA3AF]">
                <div>Ship to: {o.shipping_name}, {o.shipping_address}</div>
                <div>{o.shipping_email} · {o.shipping_phone || "—"}</div>
                {o.tracking_number && <div className="mt-1 font-mono text-[#1A7A6E]">Tracking: {o.tracking_number}</div>}
              </div>
              <div className="mt-4 flex gap-2 flex-wrap">
                {o.status === "paid" && <button onClick={() => ship(o.id)} className="helix-btn-primary text-sm" data-testid={`ship-${o.id}`}>Mark shipped</button>}
                {(o.status === "shipped" || (o.status === "paid" && o.escrow_status === "held")) && (
                  <button onClick={() => deliver(o.id)} className="helix-btn-primary text-sm inline-flex items-center gap-1" data-testid={`deliver-${o.id}`}>
                    <CheckCircle size={14} weight="fill"/> Mark delivered · release escrow
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {respond && (
        <div className="fixed inset-0 bg-[#0A1628]/80 flex items-center justify-center z-50 p-4" onClick={() => setRespond(null)}>
          <div onClick={(e)=>e.stopPropagation()} className="helix-card p-6 w-full max-w-md">
            <div className="helix-kicker">Respond · {respond.quote_number}</div>
            <h3 className="helix-h3 mt-1">{respond.listing_title}</h3>
            <div className="mt-3 text-[12px] text-[#9CA3AF]">Qty requested: {respond.quantity}</div>
            <div className="mt-4 space-y-3">
              <div><label className="helix-label">Quoted unit price (USD)</label>
                <input type="number" step="0.01" className="helix-input" value={form.quoted_unit_price_usd} onChange={(e)=>setForm({...form, quoted_unit_price_usd: e.target.value})} data-testid="q-unit"/></div>
              <div><label className="helix-label">Note</label>
                <textarea className="helix-input h-20" value={form.quote_note} onChange={(e)=>setForm({...form, quote_note: e.target.value})} data-testid="q-note"/></div>
              <div><label className="helix-label">Valid for (days)</label>
                <input type="number" className="helix-input" value={form.valid_days} onChange={(e)=>setForm({...form, valid_days: e.target.value})}/></div>
              <div className="flex gap-2">
                <button onClick={() => setRespond(null)} className="helix-btn-secondary flex-1">Cancel</button>
                <button onClick={sendQuote} className="helix-btn-primary flex-1" data-testid="q-send">Send quote</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </Shell>
  );
}
