import { useEffect, useState } from "react";
import Shell from "../components/Shell";
import { api, formatUSD, formatNGN, formatDateTime } from "../lib/api";
import { useAuth } from "../lib/auth-context";
import { StatusPill } from "../components/StatusPill";
import { Link } from "react-router-dom";
import { ArrowUpRight, Coins, Receipt, Package, ShieldWarning, ArrowRight } from "@phosphor-icons/react";

export default function Dashboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [orders, setOrders] = useState([]);
  const [fx, setFx] = useState(null);
  const [biz, setBiz] = useState(null);
  const [complianceScore, setComplianceScore] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [fin, ord, fxres, mybiz] = await Promise.all([
          api.get("/finance/dashboard"),
          api.get("/orders/mine"),
          api.get("/fx"),
          api.get("/businesses/me"),
        ]);
        setData(fin.data);
        setOrders(ord.data);
        setFx(fxres.data);
        setBiz(mybiz.data);
        if (user?.role === "exporter" && mybiz.data) {
          const cs = await api.get("/compliance/score");
          setComplianceScore(cs.data);
        }
      } finally { setLoading(false); }
    })();
  }, [user]);

  const kicker = user?.role === "buyer" ? "Buyer · Trade Desk" : "Exporter · Command Center";
  const title = `Welcome back, ${user?.name?.split(" ")[0]}`;

  if (loading) return <Shell title={title} kicker={kicker}><Skeleton /></Shell>;

  const anchor_env = "SANDBOX · MOCK";

  return (
    <Shell title={title} kicker={kicker}
      actions={<div className="flex items-center gap-3 text-[11px] font-mono tracking-widest text-[#1A7A6E]">
        ANCHOR · {anchor_env}<span className="w-2 h-2 rounded-full bg-[#1A7A6E] inline-block animate-pulse" />
      </div>}>

      {/* Status banner when not approved */}
      {biz && (biz.kyc_status !== "approved" && biz.kyb_status !== "approved") && (
        <div className="helix-card p-5 mb-6 border-[#C9922A]/40 bg-[#C9922A]/6 flex items-start gap-4">
          <ShieldWarning size={22} className="text-[#C9922A] mt-0.5" />
          <div className="flex-1">
            <div className="font-semibold">Complete verification to unlock trading</div>
            <p className="text-[13px] text-[#9CA3AF] mt-1">Submit your {biz.registration_type === "business" ? "KYB" : "KYC"} documents to provision your NGN and USD accounts.</p>
          </div>
          <Link to="/onboarding" className="helix-btn-primary text-sm whitespace-nowrap">Continue onboarding <ArrowRight size={14} weight="bold" className="inline ml-1"/></Link>
        </div>
      )}
      {!biz && (
        <div className="helix-card p-5 mb-6 border-[#C9922A]/40 bg-[#C9922A]/6 flex items-start gap-4">
          <ShieldWarning size={22} className="text-[#C9922A] mt-0.5" />
          <div className="flex-1">
            <div className="font-semibold">Set up your business profile</div>
            <p className="text-[13px] text-[#9CA3AF] mt-1">Before you can list products or receive payments, create your business profile.</p>
          </div>
          <Link to="/onboarding" className="helix-btn-primary text-sm whitespace-nowrap">Start onboarding <ArrowRight size={14} weight="bold" className="inline ml-1"/></Link>
        </div>
      )}

      {/* BALANCES */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <BalanceCard label="USD Balance" value={formatUSD(data?.usd_balance)} sub="Available · USD" va={data?.virtual_accounts?.usd} accent />
        <BalanceCard label="NGN Balance" value={formatNGN(data?.ngn_balance)} sub="Available · NGN" va={data?.virtual_accounts?.ngn} />
        <div className="helix-card p-5">
          <div className="flex justify-between items-start">
            <div>
              <div className="helix-label">USD / NGN Rate</div>
              <div className="font-mono text-3xl font-bold text-[#C9922A] mt-2 tracking-tight">
                ₦{fx ? Number(fx.usd_to_ngn).toLocaleString() : "—"}
              </div>
            </div>
            <Coins size={22} className="text-[#1A7A6E]" />
          </div>
          <div className="mt-4 text-[11px] font-mono text-[#9CA3AF] tracking-wider">
            {fx?.source?.toUpperCase()} · {fx ? formatDateTime(new Date(fx.fetched_at * 1000).toISOString()) : ""}
          </div>
          {user?.role === "exporter" && (
            <Link to="/finance" className="mt-4 inline-flex items-center gap-1 text-[#C9922A] text-[12px] hover:gap-2 transition-all">
              Manage funds <ArrowUpRight size={14} />
            </Link>
          )}
        </div>
      </div>

      {/* Row 2: orders + compliance */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-8">
        <div className="helix-card lg:col-span-2 overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-[#1A7A6E]/20">
            <div>
              <div className="helix-label">Recent Orders</div>
              <div className="helix-h3 mt-1">{orders.length ? `${orders.length} active` : "No orders yet"}</div>
            </div>
            <Link to="/orders" className="text-[12px] text-[#C9922A] hover:underline">View all</Link>
          </div>
          {orders.length ? (
            <div className="overflow-x-auto">
              <table className="helix-table">
                <thead>
                  <tr>
                    <th>Order</th><th>Product</th><th>Qty</th><th>Amount</th><th>Status</th><th>Payment</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.slice(0, 6).map((o) => (
                    <tr key={o.id}>
                      <td className="font-mono text-[#C9922A]"><Link to={`/orders/${o.id}`}>{o.order_number}</Link></td>
                      <td className="max-w-[220px] truncate">{o.product_name}</td>
                      <td className="font-mono">{o.quantity}</td>
                      <td className="font-mono">{formatUSD(o.agreed_price_usd)}</td>
                      <td><StatusPill status={o.status} /></td>
                      <td><StatusPill status={o.payment_status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-10 text-center text-[#9CA3AF] text-sm">
              <Package size={34} className="mx-auto mb-3 text-[#1A7A6E]" />
              {user?.role === "buyer" ? "Browse the marketplace to submit your first RFQ." : "Orders you receive or place will appear here."}
            </div>
          )}
        </div>

        <div className="helix-card p-5">
          <div className="flex items-start justify-between">
            <div>
              <div className="helix-label">Compliance Score</div>
              <div className="font-mono text-4xl font-bold text-[#F5F5F5] mt-2">
                {complianceScore ? `${complianceScore.score}` : (biz?.compliance_score ?? "—")}
                <span className="text-[#9CA3AF] text-xl">/100</span>
              </div>
            </div>
            <StatusPill status={(complianceScore?.score ?? biz?.compliance_score ?? 0) >= 80 ? "active" : "expiring_soon"} />
          </div>
          {complianceScore?.missing?.length > 0 && (
            <div className="mt-5">
              <div className="text-[11px] uppercase tracking-wider text-[#9CA3AF] mb-2">Missing documents</div>
              <ul className="space-y-1">
                {complianceScore.missing.slice(0, 4).map((m) => (
                  <li key={m} className="text-[13px] flex items-center gap-2 text-[#F5F5F5]">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#C9922A]"/> {m}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <Link to="/compliance" className="mt-5 inline-flex items-center gap-1 text-[#C9922A] text-[12px] hover:gap-2 transition-all">
            Manage vault <ArrowUpRight size={14} />
          </Link>
        </div>
      </div>

      {/* Recent transactions */}
      <div className="helix-card overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#1A7A6E]/20">
          <div>
            <div className="helix-label">Recent Transactions</div>
            <div className="helix-h3 mt-1">Ledger · last 10</div>
          </div>
          <Link to="/finance" className="text-[12px] text-[#C9922A] hover:underline">View full ledger</Link>
        </div>
        {data?.recent_transactions?.length ? (
          <div className="overflow-x-auto">
            <table className="helix-table">
              <thead>
                <tr>
                  <th>When</th><th>Type</th><th>Description</th><th>Reference</th><th className="text-right">Amount</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_transactions.map((t) => (
                  <tr key={t.id}>
                    <td className="font-mono text-[12px] text-[#9CA3AF]">{formatDateTime(t.timestamp)}</td>
                    <td><StatusPill status={t.type === "credit" ? "received" : t.type === "fee" ? "expiring_soon" : "active"} /></td>
                    <td className="max-w-[280px] truncate">{t.description}</td>
                    <td className="font-mono text-[12px] text-[#1A7A6E]">{t.anchor_transaction_ref}</td>
                    <td className={`font-mono text-right ${t.type === "credit" ? "text-[#C9922A]" : "text-[#F5F5F5]"}`}>
                      {t.type === "credit" ? "+" : "-"}{t.currency === "USD" ? formatUSD(t.amount) : formatNGN(t.amount)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-10 text-center text-[#9CA3AF] text-sm">
            <Receipt size={34} className="mx-auto mb-3 text-[#1A7A6E]" />
            No transactions yet.
          </div>
        )}
      </div>
    </Shell>
  );
}

function BalanceCard({ label, value, sub, va, accent }) {
  return (
    <div className={`helix-card p-5 ${accent ? "relative overflow-hidden" : ""}`}>
      {accent && <div className="absolute -top-10 -right-10 w-32 h-32 rounded-full bg-[#C9922A]/10 blur-2xl pointer-events-none"/>}
      <div className="flex justify-between items-start relative">
        <div>
          <div className="helix-label">{label}</div>
          <div className="font-mono text-4xl font-bold mt-2 tracking-tight text-[#F5F5F5]" data-testid={`balance-${label.split(" ")[0].toLowerCase()}`}>{value}</div>
          <div className="text-[11px] text-[#9CA3AF] mt-1 font-mono uppercase tracking-wider">{sub}</div>
        </div>
      </div>
      {va?.account_number && (
        <div className="mt-5 pt-4 border-t border-[#1A7A6E]/15">
          <div className="text-[10px] uppercase tracking-widest text-[#9CA3AF] mb-1">Virtual Account</div>
          <div className="font-mono text-[13px] text-[#C9922A]">{va.account_number}</div>
          <div className="text-[11px] text-[#9CA3AF]">{va.bank}</div>
        </div>
      )}
    </div>
  );
}

function Skeleton() {
  return <div className="grid grid-cols-3 gap-4">{[0,1,2].map(i => <div key={i} className="helix-card p-5 h-32 animate-pulse opacity-40"/>)}</div>;
}
