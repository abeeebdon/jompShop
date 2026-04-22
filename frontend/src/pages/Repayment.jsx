import { useEffect, useState } from "react";
import Shell from "../components/Shell";
import { api, formatUSD, formatDate } from "../lib/api";
import { StatusPill } from "../components/StatusPill";
import { CheckCircle } from "@phosphor-icons/react";

export default function Repayment() {
  const [data, setData] = useState(null);
  useEffect(() => { api.get("/credit/repayments/mine").then(r => setData(r.data)); }, []);
  if (!data) return <Shell title="Repayments"><div/></Shell>;
  if (data.applications.length === 0) {
    return (
      <Shell title="JompStart Repayments" kicker="Auto-debit · Schedule">
        <div className="helix-card p-12 text-center text-[#9CA3AF]">
          No active credit. <a href="/credit" className="text-[#C9922A]">Apply for credit →</a>
        </div>
      </Shell>
    );
  }

  return (
    <Shell title="JompStart Repayments" kicker={`${formatUSD(data.total_outstanding_usd)} outstanding · Auto-debit from incoming USD`}>
      {data.applications.map(a => (
        <div key={a.application.id} className="helix-card p-6 mb-6">
          <div className="flex items-start justify-between flex-wrap gap-3">
            <div>
              <div className="text-[11px] font-mono tracking-widest text-[#1A7A6E]">{a.application.application_number}</div>
              <div className="helix-h3 mt-1">{formatUSD(a.application.offered_amount_usd)} · {a.application.offered_term_months}mo @ {a.application.offered_apr}%</div>
              <div className="text-[12px] text-[#9CA3AF] mt-1">Outstanding: <span className="font-mono text-[#C9922A]">{formatUSD(a.outstanding_usd)}</span></div>
            </div>
            {a.next_due && (
              <div className="text-right">
                <div className="helix-label">Next due</div>
                <div className="font-mono text-lg">{formatUSD(a.next_due.total_due_usd - a.next_due.paid_usd)}</div>
                <div className="text-[11px] text-[#9CA3AF] font-mono">on {formatDate(a.next_due.due_date)}</div>
              </div>
            )}
          </div>

          <div className="mt-5 overflow-x-auto">
            <table className="helix-table">
              <thead><tr><th>#</th><th>Due</th><th>Principal</th><th>Interest</th><th>Total</th><th>Paid</th><th>Status</th></tr></thead>
              <tbody>
                {a.installments.map(i => (
                  <tr key={i.id} data-testid={`inst-${i.installment_number}`}>
                    <td className="font-mono">{i.installment_number}</td>
                    <td className="font-mono text-[12px]">{formatDate(i.due_date)}</td>
                    <td className="font-mono">{formatUSD(i.principal_usd)}</td>
                    <td className="font-mono text-[#9CA3AF]">{formatUSD(i.interest_usd)}</td>
                    <td className="font-mono text-[#C9922A]">{formatUSD(i.total_due_usd)}</td>
                    <td className="font-mono">{formatUSD(i.paid_usd)}</td>
                    <td>
                      {i.status === "paid" ? <span className="helix-status helix-status-ok"><CheckCircle size={10} weight="fill"/> paid</span> : <StatusPill status={i.status}/>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-3 text-[11px] text-[#9CA3AF]">
            Auto-debit: whenever USD lands in your wallet (trade payments or consumer orders), Helix deducts up to the next installment in full and sends it to JompStart.
          </div>
        </div>
      ))}
    </Shell>
  );
}
