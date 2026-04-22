import { useEffect, useState } from "react";
import Shell from "../components/Shell";
import { api, formatUSD, formatDateTime } from "../lib/api";
import { StatusPill } from "../components/StatusPill";
import { toast } from "sonner";
import { Truck } from "@phosphor-icons/react";

export default function Fulfillment() {
  const [orders, setOrders] = useState([]);
  const load = async () => { const { data } = await api.get("/shop/orders/fulfillment"); setOrders(data); };
  useEffect(() => { load(); }, []);
  const ship = async (id) => {
    const tn = prompt("Tracking number (leave blank to auto-generate)");
    try {
      await api.post(`/shop/orders/${id}/ship`, { tracking_number: tn || "" });
      toast.success("Marked shipped"); load();
    } catch (err) { toast.error(err.response?.data?.detail || "Failed"); }
  };
  const deliver = async (id) => {
    try { await api.post(`/shop/orders/${id}/delivered`); toast.success("Marked delivered"); load(); }
    catch (err) { toast.error(err.response?.data?.detail || "Failed"); }
  };
  return (
    <Shell title="Fulfillment Queue" kicker="Consumer orders · To ship">
      {orders.length === 0 ? (
        <div className="helix-card p-12 text-center text-[#9CA3AF]">No consumer orders yet.</div>
      ) : (
        <div className="space-y-4">
          {orders.map(o => (
            <div key={o.id} className="helix-card p-5" data-testid={`ff-${o.id}`}>
              <div className="flex items-start justify-between flex-wrap gap-3">
                <div>
                  <div className="text-[11px] font-mono tracking-widest text-[#1A7A6E]">{o.order_number}</div>
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
                  <StatusPill status={o.status}/>
                  <div className="text-[11px] text-[#9CA3AF] font-mono mt-1">{formatDateTime(o.created_at)}</div>
                </div>
              </div>
              <div className="mt-4 pt-3 border-t border-[#1A7A6E]/15 text-[12px] text-[#9CA3AF]">
                <div>Ship to: {o.shipping_name}, {o.shipping_address}</div>
                <div>{o.shipping_email} · {o.shipping_phone || "—"}</div>
                {o.tracking_number && <div className="mt-1 font-mono text-[#1A7A6E]">Tracking: {o.tracking_number}</div>}
              </div>
              <div className="mt-4 flex gap-2">
                {o.status === "paid" && <button onClick={() => ship(o.id)} className="helix-btn-primary text-sm" data-testid={`ship-${o.id}`}>Mark shipped</button>}
                {o.status === "shipped" && <button onClick={() => deliver(o.id)} className="helix-btn-secondary text-sm" data-testid={`deliver-${o.id}`}>Mark delivered</button>}
              </div>
            </div>
          ))}
        </div>
      )}
    </Shell>
  );
}
