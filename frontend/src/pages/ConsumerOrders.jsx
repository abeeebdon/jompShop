import { useEffect, useState } from "react";
import ShopShell from "../components/ShopShell";
import { api, formatUSD, formatDateTime } from "../lib/api";
import { StatusPill } from "../components/StatusPill";
import { Truck } from "@phosphor-icons/react";

export default function ConsumerOrders() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    (async () => {
      try { const { data } = await api.get("/shop/orders/mine"); setOrders(data); }
      finally { setLoading(false); }
    })();
  }, []);
  return (
    <ShopShell>
      <div className="helix-kicker mb-2">My orders</div>
      <h1 className="helix-h2 mb-6">Helix Shop · Order history</h1>
      {loading ? <div className="text-[#9CA3AF]">Loading…</div> : orders.length === 0 ? (
        <div className="helix-card p-12 text-center text-[#9CA3AF]">No orders yet. <a href="/shop" className="text-[#C9922A]">Start shopping →</a></div>
      ) : (
        <div className="space-y-4">
          {orders.map(o => (
            <div key={o.id} className="helix-card p-5" data-testid={`consumer-order-${o.id}`}>
              <div className="flex items-start justify-between flex-wrap gap-3">
                <div>
                  <div className="text-[11px] font-mono tracking-widest text-[#1A7A6E]">{o.order_number}</div>
                  <div className="helix-h3 mt-1">{o.listing_title}</div>
                  <div className="text-[12px] text-[#9CA3AF] mt-1">{o.quantity} × {formatUSD(o.unit_price_usd)} = <span className="text-[#C9922A] font-mono">{formatUSD(o.total_usd)}</span></div>
                  {o.delivery_partner_of_record && (
                    <div className="text-[12px] mt-2 inline-flex items-center gap-1 text-[#C9922A]"><Truck size={12}/> Delivered via <b>{o.delivery_partner_of_record}</b></div>
                  )}
                  {o.tracking_number && <div className="font-mono text-[11px] text-[#1A7A6E] mt-2">Tracking: {o.tracking_number}</div>}
                </div>
                <div className="text-right">
                  <StatusPill status={o.status}/>
                  <div className="text-[11px] text-[#9CA3AF] font-mono mt-2">{formatDateTime(o.created_at)}</div>
                </div>
              </div>
              <div className="mt-3 pt-3 border-t border-[#1A7A6E]/15 text-[12px] text-[#9CA3AF]">
                Ship to: {o.shipping_name}, {o.shipping_address}
              </div>
            </div>
          ))}
        </div>
      )}
    </ShopShell>
  );
}
