import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import ShopShell from "../components/ShopShell";
import { api, formatUSD, formatDateTime } from "../lib/api";
import { StatusPill } from "../components/StatusPill";
import { toast } from "sonner";
import { Truck, LockKey, CheckCircle, ChatCircle } from "@phosphor-icons/react";
import Pagination, { paginate } from "../components/Pagination";

const PER_PAGE = 10;

export default function ConsumerOrders() {
  const [orders, setOrders] = useState([]);
  const [quotes, setQuotes] = useState({ as_consumer: [], as_seller: [] });
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const load = async () => {
    const [o, q] = await Promise.all([api.get("/shop/orders/mine"), api.get("/shop/quotes/mine")]);
    setOrders(o.data); setQuotes(q.data);
  };
  useEffect(() => { (async () => { try { await load(); } finally { setLoading(false); } })(); }, []);

  const confirmDelivery = async (oid) => {
    try {
      await api.post(`/shop/orders/${oid}/confirm-delivery`);
      toast.success("Delivery confirmed — escrow released to seller");
      load();
    } catch (err) { toast.error(err.response?.data?.detail || "Failed"); }
  };
  const declineQuote = async (qid) => {
    try { await api.post(`/shop/quotes/${qid}/decline`); toast.success("Quote declined"); load(); }
    catch (err) { toast.error(err.response?.data?.detail || "Failed"); }
  };

  return (
    <ShopShell>
      <div className="helix-kicker mb-2">My orders & quotes</div>
      <h1 className="helix-h2 mb-6">Jomp Shop · Order history</h1>

      {/* Quotes */}
      {quotes.as_consumer.length > 0 && (
        <div className="mb-10">
          <div className="helix-label mb-3">Quote requests</div>
          <div className="space-y-3">
            {quotes.as_consumer.map(q => (
              <div key={q.id} className="helix-card p-5" data-testid={`quote-${q.id}`}>
                <div className="flex items-start justify-between flex-wrap gap-3">
                  <div>
                    <div className="text-[11px] font-mono tracking-widest text-[#1A7A6E]">{q.quote_number}</div>
                    <div className="helix-h3 mt-1">{q.listing_title}</div>
                    <div className="text-[12px] text-[#9CA3AF]">Qty requested: {q.quantity}</div>
                    {q.message && <div className="text-[12px] mt-2 italic">&ldquo;{q.message}&rdquo;</div>}
                  </div>
                  <StatusPill status={q.status}/>
                </div>
                {q.status === "quoted" && (
                  <div className="mt-4 pt-3 border-t border-[#1A7A6E]/15">
                    <div className="grid grid-cols-3 gap-4 text-[13px]">
                      <div><div className="text-[10px] text-[#9CA3AF] tracking-widest">QUOTED UNIT</div><div className="font-mono text-[#C9922A]">{formatUSD(q.quoted_unit_price_usd)}</div></div>
                      <div><div className="text-[10px] text-[#9CA3AF] tracking-widest">QUOTED TOTAL</div><div className="font-mono text-[#C9922A] text-lg">{formatUSD(q.quoted_total_usd)}</div></div>
                      <div><div className="text-[10px] text-[#9CA3AF] tracking-widest">VALID UNTIL</div><div className="font-mono">{q.quote_valid_until}</div></div>
                    </div>
                    {q.quote_note && <p className="text-[12px] text-[#9CA3AF] mt-3">Seller: {q.quote_note}</p>}
                    <div className="flex gap-2 mt-4">
                      <Link to={`/shop/product/${q.listing_id}?quote=${q.id}`} className="helix-btn-primary text-sm inline-flex items-center gap-2" data-testid={`accept-quote-${q.id}`}>
                        <LockKey size={12}/> Accept &amp; prepay (escrow)
                      </Link>
                      <button onClick={() => declineQuote(q.id)} className="helix-btn-secondary text-sm" data-testid={`decline-quote-${q.id}`}>Decline</button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="helix-label mb-3">Orders</div>
      {loading ? <div className="text-[#9CA3AF]">Loading…</div> : orders.length === 0 ? (
        <div className="helix-card p-12 text-center text-[#9CA3AF]">No orders yet. <Link to="/shop" className="text-[#C9922A]">Start shopping →</Link></div>
      ) : (() => {
        const p = paginate(orders, page, PER_PAGE);
        return (
        <div className="space-y-4">
          {p.items.map(o => (
            <div key={o.id} className="helix-card p-5" data-testid={`consumer-order-${o.id}`}>
              <div className="flex items-start justify-between flex-wrap gap-3">
                <div>
                  <div className="text-[11px] font-mono tracking-widest text-[#1A7A6E]">{o.order_number} · {o.checkout_mode === "quote_prepay" ? "QUOTED PRICE" : "LISTED PRICE"}</div>
                  <div className="helix-h3 mt-1">{o.listing_title}</div>
                  <div className="text-[12px] text-[#9CA3AF] mt-1">{o.quantity} × {formatUSD(o.unit_price_usd)} = <span className="text-[#C9922A] font-mono">{formatUSD(o.total_usd)}</span></div>
                  {o.delivery_partner_of_record && (
                    <div className="text-[12px] mt-2 inline-flex items-center gap-1 text-[#C9922A]"><Truck size={12}/> Delivered via <b>{o.delivery_partner_of_record}</b></div>
                  )}
                  {o.tracking_number && <div className="font-mono text-[11px] text-[#1A7A6E] mt-2">Tracking: {o.tracking_number}</div>}
                </div>
                <div className="text-right">
                  <div className="flex flex-col items-end gap-1">
                    <StatusPill status={o.status}/>
                    <span className={`helix-status ${o.escrow_status === "held" ? "helix-status-gold" : "helix-status-ok"}`}>
                      <LockKey size={10}/> ESCROW · {o.escrow_status.toUpperCase()}
                    </span>
                  </div>
                  <div className="text-[11px] text-[#9CA3AF] font-mono mt-2">{formatDateTime(o.created_at)}</div>
                </div>
              </div>
              <div className="mt-3 pt-3 border-t border-[#1A7A6E]/15 text-[12px] text-[#9CA3AF]">
                Ship to: {o.shipping_name}, {o.shipping_address}
              </div>
              {o.escrow_status === "held" && (
                <div className="mt-3 flex items-center justify-between flex-wrap gap-2">
                  <div className="text-[11px] text-[#9CA3AF] inline-flex items-center gap-1">
                    <LockKey size={12} className="text-[#C9922A]"/> Funds ({formatUSD(o.total_usd)}) held by <b className="text-[#C9922A]">{o.escrow_held_by || "Riby Inc"}</b>.
                  </div>
                  {(o.status === "shipped" || o.status === "delivered") && (
                    <button onClick={() => confirmDelivery(o.id)} className="helix-btn-primary text-sm inline-flex items-center gap-1" data-testid={`confirm-${o.id}`}>
                      <CheckCircle size={14} weight="fill"/> Confirm delivery &amp; release
                    </button>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
        );
      })()}
      <Pagination page={Math.min(page, Math.max(1, Math.ceil(orders.length / PER_PAGE)))} totalPages={Math.max(1, Math.ceil(orders.length / PER_PAGE))} onChange={setPage}/>
    </ShopShell>
  );
}
