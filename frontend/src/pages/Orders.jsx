import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Shell from "../components/Shell";
import { api, formatUSD, formatDate } from "../lib/api";
import { useAuth } from "../lib/auth-context";
import { StatusPill } from "../components/StatusPill";
import Pagination, { paginate } from "../components/Pagination";

const PER_PAGE = 15;

export default function Orders() {
  const { user } = useAuth();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/orders/mine");
        setOrders(data);
      } finally { setLoading(false); }
    })();
  }, []);
  return (
    <Shell title="Orders" kicker="Trade Lifecycle">
      {loading ? <div className="text-[#9CA3AF]">Loading…</div> :
        orders.length === 0 ? (
          <div className="helix-card p-12 text-center text-[#9CA3AF]">
            No orders yet. {user?.role === "buyer" ? "Browse the marketplace to submit an RFQ." : "Inbound RFQs and confirmed trades will appear here."}
          </div>
        ) : (() => {
          const p = paginate(orders, page, PER_PAGE);
          return (
        <div className="helix-card overflow-hidden">
          <table className="helix-table">
            <thead>
              <tr>
                <th>Order</th><th>Role</th><th>Product</th><th>Qty</th><th>Amount</th><th>Delivery</th><th>Status</th><th>Payment</th>
              </tr>
            </thead>
            <tbody>
              {p.items.map((o) => (
                <tr key={o.id} data-testid={`order-row-${o.id}`}>
                  <td><Link to={`/orders/${o.id}`} className="font-mono text-[#C9922A]">{o.order_number}</Link></td>
                  <td className="text-[12px]">{o.buyer_user_id === user.user_id ? "Buyer" : "Supplier"}</td>
                  <td className="max-w-[220px] truncate">{o.product_name}</td>
                  <td className="font-mono">{o.quantity}</td>
                  <td className="font-mono">{formatUSD(o.agreed_price_usd)}</td>
                  <td className="text-[12px] text-[#9CA3AF]">{formatDate(o.target_delivery_date)}</td>
                  <td><StatusPill status={o.status}/></td>
                  <td><StatusPill status={o.payment_status}/></td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pagination page={p.page} totalPages={p.totalPages} onChange={setPage}/>
        </div>
          );
        })()
      }
    </Shell>
  );
}
