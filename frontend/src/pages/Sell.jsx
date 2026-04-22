import { useEffect, useState } from "react";
import Shell from "../components/Shell";
import { api, formatUSD } from "../lib/api";
import { useAuth } from "../lib/auth-context";
import { StatusPill } from "../components/StatusPill";
import { toast } from "sonner";
import { Plus, Truck, Storefront, Trash, PencilSimple } from "@phosphor-icons/react";

const CATS = [
  { value: "fashion", label: "Fashion" },
  { value: "agriculture", label: "Agriculture" },
  { value: "staple-foods", label: "Staple Foods" },
  { value: "general-goods", label: "General Goods" },
];

export default function Sell() {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const load = async () => { const { data } = await api.get("/shop/listings/mine"); setItems(data); };
  useEffect(() => { load(); }, []);
  const del = async (id) => {
    if (!window.confirm("Delete this listing?")) return;
    await api.delete(`/shop/listings/${id}`); toast.success("Deleted"); load();
  };
  const isExporter = user?.role === "exporter";
  return (
    <Shell title="Direct-to-Consumer Listings" kicker={isExporter ? "Exporter · Sell DTC with Riby of Record" : "Buyer · Sell from local inventory"}
      actions={<button onClick={() => { setEditing(null); setOpen(true); }} className="helix-btn-primary inline-flex items-center gap-2" data-testid="create-listing-btn"><Plus size={14}/> New listing</button>}>

      <div className="helix-card p-5 mb-6 border-[#C9922A]/30 bg-[#C9922A]/5">
        <div className="flex items-start gap-3">
          {isExporter ? <Truck size={22} className="text-[#C9922A]"/> : <Storefront size={22} className="text-[#1A7A6E]"/>}
          <div className="text-[13px] text-[#F5F5F5]">
            {isExporter ? (
              <><b>Riby Inc is Delivery Partner of Record</b> for all listings you create here. Consumers pay Helix; you receive USD net of fees; Riby handles US customs &amp; last-mile delivery.</>
            ) : (
              <>Listings here sell your <b>US-stocked inventory</b> to consumers with 48-hour delivery. Helix keeps a 2% marketplace fee; Anchor credits the remainder to your USD wallet instantly.</>
            )}
          </div>
        </div>
      </div>

      {items.length === 0 ? (
        <div className="helix-card p-10 text-center text-[#9CA3AF]">No listings yet.</div>
      ) : (
        <div className="helix-card overflow-hidden">
          <table className="helix-table">
            <thead><tr><th>Photo</th><th>Title</th><th>Category</th><th>Price</th><th>Stock</th><th>Mode</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {items.map(l => (
                <tr key={l.id}>
                  <td><img src={l.photos?.[0]} alt="" className="w-14 h-14 rounded object-cover"/></td>
                  <td className="max-w-xs truncate">{l.title}</td>
                  <td className="text-[12px] text-[#9CA3AF]">{l.category}</td>
                  <td className="font-mono">{formatUSD(l.retail_price_usd)}</td>
                  <td className="font-mono">{l.stock_qty}</td>
                  <td><span className={`helix-status ${l.fulfillment_mode === "riby_dtc" ? "helix-status-gold" : "helix-status-ok"}`}>{l.fulfillment_mode === "riby_dtc" ? "DTC · RIBY" : "LOCAL · 48HR"}</span></td>
                  <td><StatusPill status={l.status}/></td>
                  <td><div className="flex gap-2">
                    <button onClick={()=>{ setEditing(l); setOpen(true); }} className="text-[#1A7A6E] hover:text-[#C9922A]"><PencilSimple size={16}/></button>
                    <button onClick={()=>del(l.id)} className="text-[#E74C3C] hover:text-[#ff8e82]"><Trash size={16}/></button>
                  </div></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {open && <ListingForm isExporter={isExporter} editing={editing} onClose={() => { setOpen(false); load(); }}/>}
    </Shell>
  );
}

function ListingForm({ isExporter, editing, onClose }) {
  const mode = isExporter ? "riby_dtc" : "buyer_local";
  const [form, setForm] = useState(editing ? {
    title: editing.title, description: editing.description, category: editing.category,
    retail_price_usd: editing.retail_price_usd, stock_qty: editing.stock_qty,
    photos: editing.photos || [], ships_from: editing.ships_from, status: editing.status,
  } : {
    title: "", description: "", category: "fashion", retail_price_usd: 29, stock_qty: 10,
    photos: [], ships_from: isExporter ? "Lagos → Riby US fulfillment" : "Brooklyn, NY", status: "active",
  });
  const [busy, setBusy] = useState(false);
  const upload = async (e) => {
    const files = Array.from(e.target.files || []);
    for (const f of files) {
      const fd = new FormData(); fd.append("file", f);
      try {
        const { data } = await api.post("/upload?kind=shop", fd, { headers: { "Content-Type": "multipart/form-data" } });
        const token = localStorage.getItem("helix_token");
        const url = `${process.env.REACT_APP_BACKEND_URL}/api/files/${data.storage_path}?auth=${encodeURIComponent(token)}`;
        setForm(x => ({ ...x, photos: [...x.photos, url] }));
      } catch { toast.error("Upload failed"); }
    }
  };
  const save = async () => {
    setBusy(true);
    try {
      if (editing) { await api.patch(`/shop/listings/${editing.id}`, form); toast.success("Updated"); }
      else { await api.post("/shop/listings", { ...form, fulfillment_mode: mode }); toast.success("Listing live"); }
      onClose();
    } catch (err) { toast.error(err.response?.data?.detail || "Failed"); }
    finally { setBusy(false); }
  };
  return (
    <div className="fixed inset-0 bg-[#0A1628]/80 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div onClick={(e)=>e.stopPropagation()} className="helix-card p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="listing-form">
        <h2 className="helix-h3">{editing ? "Edit listing" : `New ${mode === "riby_dtc" ? "direct-from-Africa" : "US in-stock"} listing`}</h2>
        <div className="mt-5 grid md:grid-cols-2 gap-4">
          <div className="md:col-span-2"><label className="helix-label">Title</label><input className="helix-input" value={form.title} onChange={(e)=>setForm({...form, title: e.target.value})} data-testid="lf-title"/></div>
          <div><label className="helix-label">Category</label>
            <select className="helix-input" value={form.category} onChange={(e)=>setForm({...form, category: e.target.value})}>
              {CATS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select></div>
          <div><label className="helix-label">Retail price (USD)</label><input type="number" step="0.01" className="helix-input" value={form.retail_price_usd} onChange={(e)=>setForm({...form, retail_price_usd: Number(e.target.value)})} data-testid="lf-price"/></div>
          <div><label className="helix-label">Stock qty</label><input type="number" className="helix-input" value={form.stock_qty} onChange={(e)=>setForm({...form, stock_qty: Number(e.target.value)})}/></div>
          <div><label className="helix-label">Ships from</label><input className="helix-input" value={form.ships_from} onChange={(e)=>setForm({...form, ships_from: e.target.value})}/></div>
          <div className="md:col-span-2"><label className="helix-label">Description</label><textarea className="helix-input h-24" value={form.description} onChange={(e)=>setForm({...form, description: e.target.value})}/></div>
          <div className="md:col-span-2"><label className="helix-label">Photos</label>
            <input type="file" multiple accept="image/*" onChange={upload} className="helix-input"/>
            <div className="flex gap-2 mt-2 flex-wrap">{form.photos.map((ph, i) => <img key={i} src={ph} alt="" className="w-16 h-16 rounded object-cover"/>)}</div>
          </div>
          <div><label className="helix-label">Status</label>
            <select className="helix-input" value={form.status} onChange={(e)=>setForm({...form, status: e.target.value})}>
              <option value="active">Active</option><option value="out_of_stock">Out of stock</option><option value="archived">Archived</option>
            </select></div>
        </div>
        <div className="mt-6 flex gap-3">
          <button onClick={onClose} className="helix-btn-secondary flex-1">Cancel</button>
          <button onClick={save} disabled={busy} className="helix-btn-primary flex-1" data-testid="lf-save">{busy ? "Saving…" : "Save listing"}</button>
        </div>
      </div>
    </div>
  );
}
