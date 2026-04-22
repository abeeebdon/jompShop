import { useEffect, useState } from "react";
import Shell from "../components/Shell";
import { api, formatUSD, formatNGN, formatDateTime } from "../lib/api";
import { StatusPill } from "../components/StatusPill";
import { toast } from "sonner";
import { Bank, ArrowSquareOut, Copy } from "@phosphor-icons/react";

export default function Finance() {
  const [dash, setDash] = useState(null);
  const [txs, setTxs] = useState([]);
  const [wOpen, setWOpen] = useState(false);
  const [filter, setFilter] = useState({ currency: "", type: "" });

  const load = async () => {
    const d = await api.get("/finance/dashboard");
    setDash(d.data);
    const t = await api.get("/finance/transactions", { params: filter });
    setTxs(t.data);
  };
  useEffect(() => { load(); // eslint-disable-next-line
  }, [filter]);

  const copy = (v) => { navigator.clipboard.writeText(v); toast.success("Copied"); };

  if (!dash) return <Shell title="Finance"><div/></Shell>;

  return (
    <Shell title="Financial Command" kicker="NGN · USD · Anchor Sandbox"
      actions={<button onClick={() => setWOpen(true)} className="helix-btn-primary inline-flex items-center gap-2" data-testid="withdraw-btn">
        <Bank size={14}/> Withdraw NGN
      </button>}>

      <div className="grid md:grid-cols-2 gap-4 mb-6">
        <BalanceBlock currency="USD" label="USD Balance" balance={dash.usd_balance} va={dash.virtual_accounts?.usd} onCopy={copy} accent/>
        <BalanceBlock currency="NGN" label="NGN Balance" balance={dash.ngn_balance} va={dash.virtual_accounts?.ngn} onCopy={copy}/>
      </div>

      <div className="helix-card overflow-hidden">
        <div className="px-5 py-4 border-b border-[#1A7A6E]/20 flex flex-wrap justify-between gap-3 items-center">
          <div><div className="helix-label">Transaction Ledger</div><div className="helix-h3 mt-1">{txs.length} transaction(s)</div></div>
          <div className="flex gap-2">
            <select className="helix-input w-32" value={filter.currency} onChange={(e)=>setFilter({...filter, currency: e.target.value})}><option value="">All ccy</option><option>USD</option><option>NGN</option></select>
            <select className="helix-input w-36" value={filter.type} onChange={(e)=>setFilter({...filter, type: e.target.value})}><option value="">All types</option><option value="credit">Credit</option><option value="debit">Debit</option><option value="transfer">Transfer</option><option value="fee">Fee</option></select>
          </div>
        </div>
        {txs.length === 0 ? (
          <div className="p-10 text-center text-[#9CA3AF]">No transactions.</div>
        ) : (
          <table className="helix-table">
            <thead><tr><th>When</th><th>Type</th><th>Description</th><th>Reference</th><th>Status</th><th className="text-right">Amount</th></tr></thead>
            <tbody>
              {txs.map((t) => (
                <tr key={t.id} data-testid={`tx-${t.id}`}>
                  <td className="font-mono text-[12px] text-[#9CA3AF]">{formatDateTime(t.timestamp)}</td>
                  <td className="uppercase text-[11px] font-mono tracking-wider">{t.type}</td>
                  <td className="max-w-sm truncate">{t.description}</td>
                  <td className="font-mono text-[11px] text-[#1A7A6E]">{t.anchor_transaction_ref}</td>
                  <td><StatusPill status={t.status}/></td>
                  <td className={`font-mono text-right ${t.type === "credit" ? "text-[#C9922A]" : "text-[#F5F5F5]"}`}>
                    {t.type === "credit" ? "+" : "-"}{t.currency === "USD" ? formatUSD(t.amount) : formatNGN(t.amount)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {wOpen && <WithdrawModal onClose={() => { setWOpen(false); load(); }} balance={dash.ngn_balance}/>}
    </Shell>
  );
}

function BalanceBlock({ label, balance, va, onCopy, accent, currency }) {
  return (
    <div className={`helix-card p-6 ${accent ? "relative overflow-hidden" : ""}`}>
      {accent && <div className="absolute -top-10 -right-10 w-32 h-32 rounded-full bg-[#C9922A]/10 blur-2xl pointer-events-none"/>}
      <div className="helix-label">{label}</div>
      <div className="font-mono text-4xl font-bold mt-2 tracking-tight">{currency === "USD" ? formatUSD(balance) : formatNGN(balance)}</div>
      {va?.account_number && (
        <div className="mt-5 pt-4 border-t border-[#1A7A6E]/15">
          <div className="text-[10px] uppercase tracking-widest text-[#9CA3AF] mb-1">Virtual Account · {va.bank}</div>
          <div className="flex items-center gap-2">
            <div className="font-mono text-[15px] text-[#C9922A]">{va.account_number}</div>
            <button onClick={() => onCopy(va.account_number)} className="text-[#9CA3AF] hover:text-[#C9922A]" data-testid={`copy-${currency}`}><Copy size={14}/></button>
          </div>
        </div>
      )}
    </div>
  );
}

function WithdrawModal({ onClose, balance }) {
  const [form, setForm] = useState({ amount: "", bank_code: "058", account_number: "", narration: "Helix withdrawal" });
  const submit = async () => {
    try {
      const { data } = await api.post("/finance/withdraw", { ...form, amount: Number(form.amount) });
      toast.success(`Withdrawal ${data.transfer.status}`);
      onClose();
    } catch (err) { toast.error(err.response?.data?.detail || "Failed"); }
  };
  return (
    <div className="fixed inset-0 bg-[#0A1628]/80 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div onClick={(e)=>e.stopPropagation()} className="helix-card p-6 w-full max-w-md" data-testid="withdraw-modal">
        <h3 className="helix-h3">Withdraw NGN to bank</h3>
        <div className="text-[12px] text-[#9CA3AF] mt-1 font-mono">Available: {formatNGN(balance)}</div>
        <div className="space-y-3 mt-5">
          <div><label className="helix-label">Amount (NGN)</label><input type="number" className="helix-input" value={form.amount} onChange={(e)=>setForm({...form, amount: e.target.value})} data-testid="w-amount"/></div>
          <div><label className="helix-label">Bank code</label><select className="helix-input" value={form.bank_code} onChange={(e)=>setForm({...form, bank_code: e.target.value})}>
            <option value="058">GTBank (058)</option><option value="044">Access (044)</option><option value="011">First Bank (011)</option><option value="033">UBA (033)</option><option value="057">Zenith (057)</option></select></div>
          <div><label className="helix-label">Account number</label><input className="helix-input" value={form.account_number} onChange={(e)=>setForm({...form, account_number: e.target.value})} maxLength={10} data-testid="w-account"/></div>
          <div><label className="helix-label">Narration</label><input className="helix-input" value={form.narration} onChange={(e)=>setForm({...form, narration: e.target.value})}/></div>
          <div className="flex gap-2 pt-2"><button onClick={onClose} className="helix-btn-secondary flex-1">Cancel</button><button onClick={submit} className="helix-btn-primary flex-1" data-testid="w-submit">Send via NIP</button></div>
        </div>
      </div>
    </div>
  );
}
