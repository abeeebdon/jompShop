import { useEffect, useState } from "react";
import Shell from "../components/Shell";
import { api, formatUSD, formatNGN } from "../lib/api";
import { toast } from "sonner";
import { StatusPill } from "../components/StatusPill";
import { Plus, Trash, PencilSimple } from "@phosphor-icons/react";

const CATS = [
  { value: "fashion", label: "Fashion & Textiles" },
  { value: "agriculture", label: "Agriculture" },
  { value: "staple-foods", label: "Staple Foods" },
  { value: "general-goods", label: "General Goods" },
];

export default function MyProducts() {
  const [products, setProducts] = useState([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [fx, setFx] = useState(null);

  const load = async () => {
    const { data } = await api.get("/products/mine");
    setProducts(data);
  };

  useEffect(() => { load(); api.get("/fx").then(r => setFx(r.data)); }, []);

  const del = async (id) => {
    if (!window.confirm("Delete this product?")) return;
    await api.delete(`/products/${id}`);
    toast.success("Deleted");
    load();
  };

  return (
    <Shell title="My Products" kicker="Export Catalog Management"
      actions={
        <button onClick={() => { setEditing(null); setOpen(true); }} className="helix-btn-primary inline-flex items-center gap-2" data-testid="create-product-btn">
          <Plus size={14}/> New product
        </button>
      }>
      {products.length === 0 ? (
        <div className="helix-card p-10 text-center">
          <div className="text-[#9CA3AF]">No products yet. Create your first listing to appear in the marketplace.</div>
          <button onClick={() => setOpen(true)} className="helix-btn-primary mt-4">Create product</button>
        </div>
      ) : (
        <div className="helix-card overflow-hidden">
          <table className="helix-table">
            <thead><tr><th>Photo</th><th>Name</th><th>Category</th><th>Price</th><th>MOQ</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {products.map((p) => (
                <tr key={p.id}>
                  <td><img src={p.photos?.[0]} alt="" className="w-14 h-14 rounded object-cover"/></td>
                  <td className="max-w-xs truncate">{p.name}</td>
                  <td className="text-[13px] text-[#9CA3AF]">{p.category}</td>
                  <td className="font-mono">{formatUSD(p.price_usd)}<div className="text-[11px] text-[#9CA3AF]">{formatNGN(p.price_ngn)}</div></td>
                  <td className="font-mono">{p.min_order_qty} {p.unit}</td>
                  <td><StatusPill status={p.status}/></td>
                  <td>
                    <div className="flex gap-2">
                      <button onClick={() => { setEditing(p); setOpen(true); }} className="text-[#1A7A6E] hover:text-[#C9922A]" data-testid={`edit-${p.id}`}><PencilSimple size={16}/></button>
                      <button onClick={() => del(p.id)} className="text-[#E74C3C] hover:text-[#ff8e82]" data-testid={`del-${p.id}`}><Trash size={16}/></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {open && <ProductForm onClose={() => { setOpen(false); load(); }} editing={editing} fx={fx}/>}
    </Shell>
  );
}

function ProductForm({ onClose, editing, fx }) {
  const [form, setForm] = useState(editing ? {
    name: editing.name, category: editing.category, description: editing.description,
    price_usd: editing.price_usd, min_order_qty: editing.min_order_qty, unit: editing.unit,
    photos: editing.photos || [], status: editing.status,
  } : { name: "", category: "fashion", description: "", price_usd: 50, min_order_qty: 10, unit: "piece", photos: [], status: "draft" });
  const [busy, setBusy] = useState(false);

  const upload = async (e) => {
    const files = Array.from(e.target.files || []);
    for (const f of files) {
      const fd = new FormData();
      fd.append("file", f);
      try {
        const { data } = await api.post("/upload?kind=product", fd, { headers: { "Content-Type": "multipart/form-data" } });
        // use direct file download endpoint with ?auth=
        const token = localStorage.getItem("helix_token");
        const url = `${process.env.REACT_APP_BACKEND_URL}/api/files/${data.storage_path}?auth=${encodeURIComponent(token)}`;
        setForm((x) => ({ ...x, photos: [...x.photos, url] }));
      } catch { toast.error("Upload failed"); }
    }
  };

  const save = async () => {
    setBusy(true);
    try {
      if (editing) {
        await api.patch(`/products/${editing.id}`, form);
        toast.success("Product updated");
      } else {
        await api.post("/products", form);
        toast.success("Product created");
      }
      onClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed");
    } finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-50 bg-[#0A1628]/80 backdrop-blur flex items-center justify-center p-4" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="helix-card w-full max-w-2xl p-6 fade-up max-h-[90vh] overflow-y-auto" data-testid="product-form">
        <h2 className="helix-h3">{editing ? "Edit product" : "Create product"}</h2>
        <div className="mt-5 grid md:grid-cols-2 gap-4">
          <Field label="Name" full><input className="helix-input" value={form.name} onChange={(e)=>setForm({...form, name: e.target.value})} data-testid="pf-name"/></Field>
          <Field label="Category">
            <select className="helix-input" value={form.category} onChange={(e)=>setForm({...form, category: e.target.value})} data-testid="pf-cat">
              {CATS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
          </Field>
          <Field label="Unit"><input className="helix-input" value={form.unit} onChange={(e)=>setForm({...form, unit: e.target.value})}/></Field>
          <Field label="Price USD"><input type="number" step="0.01" className="helix-input" value={form.price_usd} onChange={(e)=>setForm({...form, price_usd: Number(e.target.value)})} data-testid="pf-price"/></Field>
          <Field label="MOQ"><input type="number" className="helix-input" value={form.min_order_qty} onChange={(e)=>setForm({...form, min_order_qty: Number(e.target.value)})}/></Field>
          <Field label="Description" full><textarea className="helix-input h-24" value={form.description} onChange={(e)=>setForm({...form, description: e.target.value})}/></Field>
          <Field label="Photos" full>
            <input type="file" multiple accept="image/*" onChange={upload} className="helix-input" data-testid="pf-photos"/>
            <div className="flex gap-2 mt-2 flex-wrap">
              {form.photos.map((ph, i) => <img key={i} src={ph} alt="" className="w-16 h-16 rounded object-cover"/>)}
            </div>
          </Field>
          <Field label="Status">
            <select className="helix-input" value={form.status} onChange={(e)=>setForm({...form, status: e.target.value})}>
              <option value="draft">Draft</option>
              <option value="active">Active (published)</option>
              <option value="archived">Archived</option>
            </select>
          </Field>
          {fx && <div className="flex items-end text-[12px] text-[#9CA3AF] font-mono">NGN est. @ {fx.usd_to_ngn} = ₦{(form.price_usd * fx.usd_to_ngn).toLocaleString()}</div>}
        </div>
        <div className="flex gap-3 mt-6">
          <button onClick={onClose} className="helix-btn-secondary flex-1">Cancel</button>
          <button onClick={save} disabled={busy} className="helix-btn-primary flex-1" data-testid="pf-save">{busy ? "Saving…" : "Save"}</button>
        </div>
      </div>
    </div>
  );
}
function Field({ label, children, full }) {
  return <div className={full ? "md:col-span-2" : ""}><label className="helix-label">{label}</label>{children}</div>;
}
