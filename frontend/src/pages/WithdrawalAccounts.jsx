import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Shell from "../components/Shell";
import { api } from "../lib/api";
import { toast } from "sonner";
import { Plus, Trash, Star, Bank, Globe, X, Check } from "@phosphor-icons/react";
import Modal from "../components/Modal";

export default function WithdrawalAccounts() {
  const [accounts, setAccounts] = useState([]);
  const [banks, setBanks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);

  const load = async () => {
    setLoading(true);
    const [a, b] = await Promise.all([
      api.get("/finance/withdrawal-accounts"),
      api.get("/finance/withdrawal-banks"),
    ]);
    setAccounts(a.data);
    setBanks(b.data);
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  const setDefault = async (id) => {
    try { await api.patch(`/finance/withdrawal-accounts/${id}`, { is_default: true }); toast.success("Set as default"); load(); }
    catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
  };
  const remove = async (id) => {
    if (!window.confirm("Deactivate this account? Existing withdrawals to it stay in your history.")) return;
    try { await api.delete(`/finance/withdrawal-accounts/${id}`); toast.success("Account deactivated"); load(); }
    catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
  };

  return (
    <Shell title="Withdrawal accounts" kicker="Pre-approved · NGN + USD"
      actions={<button onClick={() => setOpen(true)} className="helix-btn-primary inline-flex items-center gap-2" data-testid="add-account-btn"><Plus size={14}/> Add account</button>}>
      <p className="text-[13px] text-[#9CA3AF] mb-6 max-w-2xl">
        Save your destination bank accounts once. Add multiple in NGN and USD, mark a default per currency,
        and then withdraw to them with a single click — no need to retype routing numbers each time.
      </p>

      <Section title="USD accounts" icon={Globe} items={accounts.filter(a => a.currency === "USD")} loading={loading}
               onDefault={setDefault} onRemove={remove} testid="usd-accounts" empty="No USD accounts. Add one to receive USD payouts." />
      <Section title="NGN accounts" icon={Bank} items={accounts.filter(a => a.currency === "NGN")} loading={loading}
               onDefault={setDefault} onRemove={remove} testid="ngn-accounts" empty="No NGN accounts. Add one to withdraw via NIP." />

      <div className="mt-8 flex items-center justify-between">
        <Link to="/finance" className="text-[12px] text-[#9CA3AF] hover:text-[#F5F5F5]">← Back to Finance</Link>
      </div>

      {open && (
        <AddAccountModal banks={banks} onClose={() => setOpen(false)} onSaved={() => { setOpen(false); load(); }}/>
      )}
    </Shell>
  );
}

function Section({ title, icon: Icon, items, loading, onDefault, onRemove, testid, empty }) {
  return (
    <div className="helix-card p-5 mb-5" data-testid={testid}>
      <div className="flex items-center gap-2 mb-3">
        <Icon size={16} className="text-[#C9922A]"/><div className="helix-h3">{title}</div>
        <span className="ml-auto text-[11px] font-mono uppercase tracking-wider text-[#9CA3AF]">{items.length}</span>
      </div>
      {loading ? <div className="text-[#9CA3AF] text-[13px]">Loading…</div> : items.length === 0 ? (
        <div className="text-[#9CA3AF] text-[13px] py-3">{empty}</div>
      ) : (
        <div className="grid md:grid-cols-2 gap-3">
          {items.map(a => (
            <div key={a.id} data-testid={`acc-${a.id}`} className="border border-[#1A7A6E]/25 rounded p-4 flex items-start justify-between gap-3 bg-[#0A1628]/40">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <div className="font-semibold text-[14px] truncate">{a.label}</div>
                  {a.is_default && <span className="helix-status helix-status-gold text-[9px] py-0.5 px-2"><Star size={9} weight="fill"/> Default</span>}
                  {a.approval_status === "approved" && <span className="helix-status helix-status-ok text-[9px] py-0.5 px-2"><Check size={9}/> Approved</span>}
                </div>
                <div className="text-[12px] text-[#9CA3AF] mt-1 truncate">{a.bank_name}</div>
                <div className="text-[12px] font-mono mt-1">{a.account_number_masked}{a.account_type ? ` · ${a.account_type}` : ""}{a.routing_number ? ` · RTN ${a.routing_number}` : ""}</div>
                <div className="text-[11px] text-[#9CA3AF] mt-1">Holder: {a.account_name}</div>
              </div>
              <div className="flex flex-col gap-1">
                {!a.is_default && <button onClick={() => onDefault(a.id)} title="Set default" className="text-[#9CA3AF] hover:text-[#C9922A]" data-testid={`default-${a.id}`}><Star size={14}/></button>}
                <button onClick={() => onRemove(a.id)} title="Deactivate" className="text-[#9CA3AF] hover:text-[#E74C3C]" data-testid={`remove-${a.id}`}><Trash size={14}/></button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function AddAccountModal({ banks, onClose, onSaved }) {
  const [currency, setCurrency] = useState("USD");
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    label: "", account_name: "", is_default: true,
    // NGN
    bank_code: "058", account_number: "",
    // USD
    bank_name: "", routing_number: "", account_type: "checking", swift_code: "",
  });
  const upd = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const save = async () => {
    setBusy(true);
    try {
      await api.post("/finance/withdrawal-accounts", { ...form, currency });
      toast.success("Account added & approved");
      onSaved();
    } catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
    finally { setBusy(false); }
  };

  return (
    <Modal onClose={onClose} title="Add withdrawal account" testid="add-account-modal">
      <div className="grid grid-cols-2 gap-2">
        <button onClick={() => setCurrency("USD")} className={`p-3 border rounded text-[13px] ${currency === "USD" ? "border-[#C9922A] bg-[#C9922A]/8" : "border-[#1A7A6E]/30"}`} data-testid="ccy-USD">USD · ACH / Wire</button>
        <button onClick={() => setCurrency("NGN")} className={`p-3 border rounded text-[13px] ${currency === "NGN" ? "border-[#C9922A] bg-[#C9922A]/8" : "border-[#1A7A6E]/30"}`} data-testid="ccy-NGN">NGN · NIP</button>
      </div>
      <div className="mt-4 space-y-3">
        <div><label className="helix-label">Nickname</label><input className="helix-input" placeholder={currency === "USD" ? "Chase business · primary" : "GTBank Lagos"} value={form.label} onChange={upd("label")} data-testid="acc-label"/></div>
        <div><label className="helix-label">Account holder name</label><input className="helix-input" value={form.account_name} onChange={upd("account_name")} required data-testid="acc-name"/></div>
        {currency === "NGN" ? (
          <>
            <div><label className="helix-label">Bank</label>
              <select className="helix-input" value={form.bank_code} onChange={upd("bank_code")} data-testid="acc-bank-code">
                {banks.map(b => <option key={b.code} value={b.code}>{b.name}</option>)}
              </select>
            </div>
            <div><label className="helix-label">Account number (10 digits)</label>
              <input className="helix-input" maxLength={10} value={form.account_number} onChange={upd("account_number")} required data-testid="acc-number"/>
            </div>
          </>
        ) : (
          <>
            <div><label className="helix-label">Bank name</label>
              <input className="helix-input" placeholder="Chase, Bank of America, Wells Fargo…" value={form.bank_name} onChange={upd("bank_name")} required data-testid="acc-usd-bank"/>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div><label className="helix-label">Routing # (9 digits ACH)</label>
                <input className="helix-input" maxLength={9} value={form.routing_number} onChange={upd("routing_number")} data-testid="acc-routing"/>
              </div>
              <div><label className="helix-label">Account type</label>
                <select className="helix-input" value={form.account_type} onChange={upd("account_type")} data-testid="acc-type">
                  <option value="checking">Checking</option><option value="savings">Savings</option>
                </select>
              </div>
            </div>
            <div><label className="helix-label">Account number</label>
              <input className="helix-input" value={form.account_number} onChange={upd("account_number")} required data-testid="acc-number"/>
            </div>
            <div><label className="helix-label">SWIFT (optional, for wires)</label>
              <input className="helix-input" maxLength={11} value={form.swift_code} onChange={upd("swift_code")} data-testid="acc-swift"/>
            </div>
          </>
        )}
        <label className="flex items-center gap-2 text-[12px] text-[#9CA3AF]">
          <input type="checkbox" checked={form.is_default} onChange={(e)=>setForm({...form, is_default: e.target.checked})}/>
          Set as default {currency} destination
        </label>
        <div className="flex gap-2 pt-1">
          <button onClick={onClose} className="helix-btn-secondary flex-1">Cancel</button>
          <button onClick={save} disabled={busy} className="helix-btn-primary flex-1" data-testid="acc-save">{busy ? "Saving…" : "Add account"}</button>
        </div>
      </div>
    </Modal>
  );
}
