import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Shell from "../components/Shell";
import { api, formatUSD, formatNGN, formatDateTime } from "../lib/api";
import { StatusPill } from "../components/StatusPill";
import { toast } from "sonner";
import { Bank, Copy, Wallet, Plus } from "@phosphor-icons/react";
import Modal from "../components/Modal";
import Pagination, { paginate } from "../components/Pagination";

const PER_PAGE = 15;

export default function Finance() {
  const [dash, setDash] = useState(null);
  const [txs, setTxs] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [open, setOpen] = useState(null); // 'NGN' | 'USD' | null
  const [filter, setFilter] = useState({ currency: "", type: "" });
  const [page, setPage] = useState(1);

  const load = async () => {
    const [d, t, a] = await Promise.all([
      api.get("/finance/dashboard"),
      api.get("/finance/transactions", { params: filter }),
      api.get("/finance/withdrawal-accounts"),
    ]);
    setDash(d.data); setTxs(t.data); setAccounts(a.data);
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [filter]);
  useEffect(() => { setPage(1); }, [filter]);

  const copy = (v) => { navigator.clipboard.writeText(v); toast.success("Copied"); };

  if (!dash) return <Shell title="Finance"><div/></Shell>;

  const txPage = paginate(txs, page, PER_PAGE);

  const ngnAccs = accounts.filter(a => a.currency === "NGN");
  const usdAccs = accounts.filter(a => a.currency === "USD");

  return (
    <Shell title="Financial Command" kicker="NGN · USD · Anchor"
      actions={
        <div className="flex items-center gap-2 flex-wrap">
          <Link to="/finance/accounts" className="helix-btn-secondary text-[12px] inline-flex items-center gap-1.5" data-testid="manage-accounts-link"><Wallet size={13}/> Accounts</Link>
          <button onClick={() => setOpen("NGN")} className="helix-btn-secondary inline-flex items-center gap-2" data-testid="withdraw-ngn-btn">
            <Bank size={14}/> Withdraw NGN
          </button>
          <button onClick={() => setOpen("USD")} className="helix-btn-primary inline-flex items-center gap-2" data-testid="withdraw-usd-btn">
            <Bank size={14}/> Withdraw USD
          </button>
        </div>
      }>

      <div className="grid md:grid-cols-2 gap-4 mb-6">
        <BalanceBlock currency="USD" label="USD Balance" balance={dash.usd_balance} va={dash.virtual_accounts?.usd} onCopy={copy} accent count={usdAccs.length}/>
        <BalanceBlock currency="NGN" label="NGN Balance" balance={dash.ngn_balance} va={dash.virtual_accounts?.ngn} onCopy={copy} count={ngnAccs.length}/>
      </div>

      <div className="helix-card overflow-hidden">
        <div className="px-5 py-4 border-b border-[#1A7A6E]/20 flex flex-wrap justify-between gap-3 items-center">
          <div>
            <div className="helix-label">Transaction Ledger</div>
            <div className="helix-h3 mt-1">{txs.length} transaction(s)</div>
          </div>
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
              {txPage.items.map((t) => (
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
        <Pagination page={txPage.page} totalPages={txPage.totalPages} onChange={setPage}/>
      </div>

      {open && <WithdrawModal currency={open} accounts={accounts.filter(a => a.currency === open)}
                              balance={open === "USD" ? dash.usd_balance : dash.ngn_balance}
                              onClose={() => { setOpen(null); load(); }}/>}
    </Shell>
  );
}

function BalanceBlock({ label, balance, va, onCopy, accent, currency, count }) {
  return (
    <div className={`helix-card p-6 ${accent ? "relative overflow-hidden" : ""}`}>
      {accent && <div className="absolute -top-10 -right-10 w-32 h-32 rounded-full bg-[#C9922A]/10 blur-2xl pointer-events-none"/>}
      <div className="flex items-center justify-between">
        <div className="helix-label">{label}</div>
        <Link to="/finance/accounts" className="text-[10px] font-mono uppercase tracking-wider text-[#1A7A6E] hover:text-[#C9922A]">{count} saved {currency} acct{count === 1 ? "" : "s"}</Link>
      </div>
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

function WithdrawModal({ currency, accounts, balance, onClose }) {
  const [accId, setAccId] = useState(accounts.find(a => a.is_default)?.id || accounts[0]?.id || "");
  const [amount, setAmount] = useState("");
  const [narration, setNarration] = useState(`Jomp Shop ${currency} withdrawal`);
  const [busy, setBusy] = useState(false);
  const fmt = currency === "USD" ? formatUSD : formatNGN;

  const submit = async () => {
    if (!accId) { toast.error("Pick a destination account first"); return; }
    setBusy(true);
    try {
      const { data } = await api.post("/finance/withdraw-from-account", {
        withdrawal_account_id: accId, amount: Number(amount), narration,
      });
      toast.success(`Withdrawal ${data.transfer.status} via ${data.rail}`);
      onClose();
    } catch (err) { toast.error(err.response?.data?.detail || "Failed"); }
    finally { setBusy(false); }
  };

  return (
    <Modal onClose={onClose} title={`Withdraw ${currency}`} testid="withdraw-modal">
      <div className="text-[12px] text-[#9CA3AF] font-mono">Available: <b className="text-[#C9922A]">{fmt(balance)}</b></div>
      {accounts.length === 0 ? (
        <div className="mt-5 border border-dashed border-[#C9922A]/40 rounded p-5 text-center">
          <div className="text-[13px] text-[#9CA3AF]">No pre-approved {currency} accounts yet.</div>
          <Link to="/finance/accounts" onClick={onClose} className="helix-btn-primary inline-flex items-center gap-1.5 mt-4 text-sm" data-testid="add-account-from-withdraw"><Plus size={13}/> Add a {currency} account</Link>
        </div>
      ) : (
        <div className="space-y-4 mt-5">
          <div>
            <label className="helix-label">Destination ({currency})</label>
            <select className="helix-input" value={accId} onChange={(e)=>setAccId(e.target.value)} data-testid="w-account-select">
              {accounts.map(a => (
                <option key={a.id} value={a.id}>
                  {a.label} — {a.bank_name} • {a.account_number_masked}{a.is_default ? " · default" : ""}
                </option>
              ))}
            </select>
            <div className="mt-1.5 text-[11px] text-[#9CA3AF]">
              <Link to="/finance/accounts" onClick={onClose} className="text-[#C9922A] hover:underline">+ Add another account</Link>
            </div>
          </div>
          <div>
            <label className="helix-label">Amount ({currency})</label>
            <input type="number" min={0} max={balance} className="helix-input" value={amount} onChange={(e)=>setAmount(e.target.value)} data-testid="w-amount"/>
          </div>
          <div>
            <label className="helix-label">Narration / memo</label>
            <input className="helix-input" value={narration} onChange={(e)=>setNarration(e.target.value)} data-testid="w-narration"/>
          </div>
          <div className="flex gap-2 pt-1">
            <button onClick={onClose} className="helix-btn-secondary flex-1">Cancel</button>
            <button onClick={submit} disabled={busy || !amount || Number(amount) <= 0} className="helix-btn-primary flex-1" data-testid="w-submit">
              {busy ? "Sending…" : `Send ${currency === "NGN" ? "via NIP" : "via ACH/Wire"}`}
            </button>
          </div>
        </div>
      )}
    </Modal>
  );
}
