import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import ShopShell from "../components/ShopShell";
import { api, formatUSD } from "../lib/api";
import { useAuth } from "../lib/auth-context";
import { toast } from "sonner";
import { Truck, Storefront, CheckCircle, ShieldCheck, MapPin } from "@phosphor-icons/react";

export default function ShopProduct() {
  const { id } = useParams();
  const { user } = useAuth();
  const nav = useNavigate();
  const [l, setL] = useState(null);
  const [qty, setQty] = useState(1);
  const [form, setForm] = useState({ shipping_name: "", shipping_address: "", shipping_email: "", shipping_phone: "" });
  const [placing, setPlacing] = useState(false);

  useEffect(() => { api.get(`/shop/listings/${id}`).then(r => setL(r.data)); }, [id]);
  useEffect(() => { if (user) setForm(f => ({ ...f, shipping_name: user.name, shipping_email: user.email })); }, [user]);

  if (!l) return <ShopShell><div className="text-[#9CA3AF]">Loading…</div></ShopShell>;
  const isDtc = l.fulfillment_mode === "riby_dtc";

  const checkout = async () => {
    if (!user) { nav("/login", { state: { from: `/shop/product/${id}` } }); return; }
    if (!form.shipping_address || !form.shipping_email) { toast.error("Shipping details required"); return; }
    setPlacing(true);
    try {
      const { data } = await api.post("/shop/orders", { listing_id: id, quantity: qty, ...form });
      toast.success(`Order ${data.order_number} placed!`);
      nav("/shop/orders");
    } catch (err) { toast.error(err.response?.data?.detail || "Checkout failed"); }
    finally { setPlacing(false); }
  };

  return (
    <ShopShell>
      <div className="grid lg:grid-cols-5 gap-8">
        <div className="lg:col-span-3">
          <div className="helix-card overflow-hidden">
            <div className="aspect-[4/3] bg-[#0A1628]">
              <img src={l.photos?.[0]} alt={l.title} className="w-full h-full object-cover"/>
            </div>
            <div className="p-6">
              <div className="flex flex-wrap gap-2 mb-4">
                {isDtc ? (
                  <span className="helix-status helix-status-gold"><Truck size={10}/> Direct · Riby Inc of Record</span>
                ) : (
                  <span className="helix-status helix-status-ok"><Storefront size={10} weight="fill"/> US In-Stock · 48-hour</span>
                )}
                <span className="helix-status helix-status-neutral">{l.category.replace("-"," ")}</span>
              </div>
              <h1 className="helix-h2">{l.title}</h1>
              <p className="text-[15px] text-[#F5F5F5] mt-4 leading-relaxed">{l.description}</p>

              <div className="mt-6 pt-6 border-t border-[#1A7A6E]/15 grid grid-cols-2 gap-6 text-[13px]">
                <div><div className="helix-label">Country of origin</div><div className="mt-1">{l.country_of_origin}</div></div>
                <div><div className="helix-label">Ships from</div><div className="mt-1">{l.ships_from}</div></div>
                <div><div className="helix-label">Seller</div><div className="mt-1">{l.seller?.business_name}</div></div>
                {l.delivery_partner_of_record && (
                  <div>
                    <div className="helix-label">Delivery Partner of Record</div>
                    <div className="mt-1 text-[#C9922A] font-medium">{l.delivery_partner_of_record}</div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="lg:col-span-2 space-y-4">
          <div className="helix-card p-6">
            <div className="helix-label">Price</div>
            <div className="font-mono text-4xl text-[#C9922A] font-bold mt-1">{formatUSD(l.retail_price_usd)}</div>
            <div className="text-[12px] text-[#9CA3AF] mt-1">
              {l.stock_qty > 0 ? `${l.stock_qty} in stock` : "Sold out"}
            </div>
            <div className="mt-5 space-y-4">
              <div className="flex items-center gap-3">
                <label className="helix-label mb-0">Qty</label>
                <input type="number" min={1} max={l.stock_qty} className="helix-input w-24" value={qty} onChange={(e)=>setQty(Math.max(1, Math.min(l.stock_qty, Number(e.target.value))))} data-testid="qty-input"/>
                <div className="font-mono text-[14px] text-[#F5F5F5]">= {formatUSD(l.retail_price_usd * qty)}</div>
              </div>
              <div><label className="helix-label">Ship to (name)</label><input className="helix-input" value={form.shipping_name} onChange={(e)=>setForm({...form, shipping_name: e.target.value})} data-testid="ship-name"/></div>
              <div><label className="helix-label">Address</label><textarea className="helix-input h-20" value={form.shipping_address} onChange={(e)=>setForm({...form, shipping_address: e.target.value})} data-testid="ship-addr"/></div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="helix-label">Email</label><input type="email" className="helix-input" value={form.shipping_email} onChange={(e)=>setForm({...form, shipping_email: e.target.value})} data-testid="ship-email"/></div>
                <div><label className="helix-label">Phone</label><input className="helix-input" value={form.shipping_phone} onChange={(e)=>setForm({...form, shipping_phone: e.target.value})}/></div>
              </div>
              <button disabled={placing || l.stock_qty <= 0} onClick={checkout} className="helix-btn-primary w-full" data-testid="buy-btn">
                {placing ? "Placing…" : user ? "Buy now" : "Sign in to buy"}
              </button>
              <div className="text-[11px] text-[#9CA3AF] text-center">Payment processed securely. Charges appear as HELIX SHOP.</div>
            </div>
          </div>

          <div className="helix-card p-5">
            <div className="helix-label">How this ships</div>
            {isDtc ? (
              <div className="mt-3 space-y-2 text-[13px] text-[#F5F5F5]">
                <div className="flex items-start gap-2"><Truck size={16} className="text-[#C9922A] mt-0.5"/><div>Origin leg handled by {l.seller?.business_name} from {l.country_of_origin}.</div></div>
                <div className="flex items-start gap-2"><MapPin size={16} className="text-[#C9922A] mt-0.5"/><div>US import &amp; last-mile by <b>Riby Inc</b> as your Delivery Partner of Record — clearance, duties, and final delivery.</div></div>
                <div className="flex items-start gap-2"><ShieldCheck size={16} className="text-[#C9922A] mt-0.5"/><div>Verified via Helix KYB · Anchor reconciled payments.</div></div>
              </div>
            ) : (
              <div className="mt-3 space-y-2 text-[13px] text-[#F5F5F5]">
                <div className="flex items-start gap-2"><Storefront size={16} className="text-[#1A7A6E] mt-0.5"/><div>Stocked in the US by {l.seller?.business_name}. Ships from {l.ships_from}.</div></div>
                <div className="flex items-start gap-2"><CheckCircle size={16} className="text-[#1A7A6E] mt-0.5"/><div>Typically arrives in 2–4 business days.</div></div>
              </div>
            )}
          </div>
        </div>
      </div>
    </ShopShell>
  );
}
