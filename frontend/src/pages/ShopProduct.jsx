import { useEffect, useState } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import ShopShell from "../components/ShopShell";
import { api, formatUSD } from "../lib/api";
import { useAuth } from "../lib/auth-context";
import { toast } from "sonner";
import { Truck, Storefront, CheckCircle, ShieldCheck, MapPin, LockKey, ChatCircle } from "@phosphor-icons/react";

export default function ShopProduct() {
  const { id } = useParams();
  const { user } = useAuth();
  const nav = useNavigate();
  const [params] = useSearchParams();
  const [l, setL] = useState(null);
  const [qty, setQty] = useState(1);
  const [mode, setMode] = useState(params.get("mode") === "quote" ? "quote" : "prepay");
  const [form, setForm] = useState({ shipping_name: "", shipping_address: "", shipping_email: "", shipping_phone: "" });
  const [quoteMsg, setQuoteMsg] = useState("");
  const [placing, setPlacing] = useState(false);
  const [quote, setQuote] = useState(null);  // if quote_id passed in URL

  useEffect(() => { api.get(`/shop/listings/${id}`).then(r => setL(r.data)); }, [id]);
  useEffect(() => { if (user) setForm(f => ({ ...f, shipping_name: user.name, shipping_email: user.email })); }, [user]);
  useEffect(() => {
    const qid = params.get("quote");
    if (qid) api.get(`/shop/quotes/${qid}`).then(r => { setQuote(r.data); setQty(r.data.quantity); setMode("accept-quote"); }).catch(()=>{});
  }, [params]);

  if (!l) return <ShopShell><div className="text-[#9CA3AF]">Loading…</div></ShopShell>;
  const isDtc = l.fulfillment_mode === "riby_dtc";
  const effectiveUnit = quote?.quoted_unit_price_usd || l.retail_price_usd;
  const totalDisplay = effectiveUnit * qty;

  const checkout = async () => {
    if (!user) { nav("/login", { state: { from: `/shop/product/${id}` } }); return; }
    if (!form.shipping_address || !form.shipping_email) { toast.error("Shipping details required"); return; }
    setPlacing(true);
    try {
      const body = { listing_id: id, quantity: qty, ...form };
      if (quote?.id) body.quote_id = quote.id;
      const { data } = await api.post("/shop/orders", body);
      toast.success(`Order ${data.order_number} placed — funds in Riby escrow`);
      nav("/shop/orders");
    } catch (err) { toast.error(err.response?.data?.detail || "Checkout failed"); }
    finally { setPlacing(false); }
  };

  const requestQuote = async () => {
    if (!user) { nav("/login", { state: { from: `/shop/product/${id}?mode=quote` } }); return; }
    try {
      const { data } = await api.post("/shop/quotes", { listing_id: id, quantity: qty, message: quoteMsg });
      toast.success(`Quote ${data.quote_number} sent — seller will respond`);
      nav("/shop/orders");
    } catch (err) { toast.error(err.response?.data?.detail || "Failed"); }
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
                <span className="helix-status helix-status-gold"><LockKey size={10}/> Riby Escrow Protected</span>
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
            <div className="font-mono text-4xl text-[#C9922A] font-bold mt-1">{formatUSD(effectiveUnit)}</div>
            <div className="text-[12px] text-[#9CA3AF] mt-1">
              {l.stock_qty > 0 ? `${l.stock_qty} in stock` : "Sold out"}
              {quote && <> · <span className="text-[#C9922A]">custom quote {quote.quote_number}</span></>}
            </div>

            {/* Mode switch */}
            {!quote && (
              <div className="mt-4 grid grid-cols-2 gap-2">
                <button onClick={()=>setMode("prepay")} data-testid="mode-prepay"
                        className={`p-3 rounded border text-left text-[12px] ${mode === "prepay" ? "border-[#C9922A] bg-[#C9922A]/8" : "border-[#1A7A6E]/30 hover:border-[#1A7A6E]"}`}>
                  <div className="font-semibold text-[#F5F5F5] inline-flex items-center gap-1"><LockKey size={12}/> Order & Prepay</div>
                  <div className="text-[#9CA3AF] mt-0.5">Pay listed price · funds held in escrow</div>
                </button>
                <button onClick={()=>setMode("quote")} data-testid="mode-quote"
                        className={`p-3 rounded border text-left text-[12px] ${mode === "quote" ? "border-[#C9922A] bg-[#C9922A]/8" : "border-[#1A7A6E]/30 hover:border-[#1A7A6E]"}`}>
                  <div className="font-semibold text-[#F5F5F5] inline-flex items-center gap-1"><ChatCircle size={12}/> Request Quote</div>
                  <div className="text-[#9CA3AF] mt-0.5">Bulk / custom · seller responds with price</div>
                </button>
              </div>
            )}

            <div className="mt-5 space-y-4">
              <div className="flex items-center gap-3">
                <label className="helix-label mb-0">Qty</label>
                <input type="number" min={1} max={l.stock_qty} className="helix-input w-24" value={qty}
                       disabled={!!quote}
                       onChange={(e)=>setQty(Math.max(1, Math.min(l.stock_qty, Number(e.target.value))))} data-testid="qty-input"/>
                <div className="font-mono text-[14px] text-[#F5F5F5]">= {formatUSD(totalDisplay)}</div>
              </div>

              {mode === "quote" ? (
                <>
                  <div><label className="helix-label">Message to seller</label>
                    <textarea className="helix-input h-24" value={quoteMsg} onChange={(e)=>setQuoteMsg(e.target.value)} data-testid="quote-msg"
                              placeholder="E.g. Bulk order of 200 units, need delivered by..."/></div>
                  <button disabled={placing} onClick={requestQuote} className="helix-btn-primary w-full" data-testid="quote-btn">
                    {user ? "Request quote" : "Sign in to request quote"}
                  </button>
                </>
              ) : (
                <>
                  <div><label className="helix-label">Ship to (name)</label><input className="helix-input" value={form.shipping_name} onChange={(e)=>setForm({...form, shipping_name: e.target.value})} data-testid="ship-name"/></div>
                  <div><label className="helix-label">Address</label><textarea className="helix-input h-20" value={form.shipping_address} onChange={(e)=>setForm({...form, shipping_address: e.target.value})} data-testid="ship-addr"/></div>
                  <div className="grid grid-cols-2 gap-3">
                    <div><label className="helix-label">Email</label><input type="email" className="helix-input" value={form.shipping_email} onChange={(e)=>setForm({...form, shipping_email: e.target.value})} data-testid="ship-email"/></div>
                    <div><label className="helix-label">Phone</label><input className="helix-input" value={form.shipping_phone} onChange={(e)=>setForm({...form, shipping_phone: e.target.value})}/></div>
                  </div>
                  <button disabled={placing || l.stock_qty <= 0} onClick={checkout} className="helix-btn-primary w-full" data-testid="buy-btn">
                    {placing ? "Placing…" : user ? (quote ? `Accept quote & prepay ${formatUSD(totalDisplay)}` : `Prepay ${formatUSD(totalDisplay)} · Escrow`) : "Sign in to buy"}
                  </button>
                  <div className="text-[11px] text-[#9CA3AF] text-center inline-flex items-center justify-center gap-1 w-full">
                    <LockKey size={10}/> Funds held by <b className="text-[#C9922A]">Riby Inc</b> until delivery is confirmed.
                  </div>
                </>
              )}
            </div>
          </div>

          <div className="helix-card p-5">
            <div className="helix-label">How this ships</div>
            {isDtc ? (
              <div className="mt-3 space-y-2 text-[13px] text-[#F5F5F5]">
                <div className="flex items-start gap-2"><Truck size={16} className="text-[#C9922A] mt-0.5"/><div>Origin leg handled by {l.seller?.business_name} from {l.country_of_origin}.</div></div>
                <div className="flex items-start gap-2"><MapPin size={16} className="text-[#C9922A] mt-0.5"/><div>US import &amp; last-mile by <b>Riby Inc</b> as your Delivery Partner of Record — clearance, duties, and final delivery.</div></div>
                <div className="flex items-start gap-2"><ShieldCheck size={16} className="text-[#C9922A] mt-0.5"/><div>Your payment is held in escrow until you confirm delivery.</div></div>
              </div>
            ) : (
              <div className="mt-3 space-y-2 text-[13px] text-[#F5F5F5]">
                <div className="flex items-start gap-2"><Storefront size={16} className="text-[#1A7A6E] mt-0.5"/><div>Stocked in the US by {l.seller?.business_name}. Ships from {l.ships_from}.</div></div>
                <div className="flex items-start gap-2"><CheckCircle size={16} className="text-[#1A7A6E] mt-0.5"/><div>Typically arrives in 2–4 business days.</div></div>
                <div className="flex items-start gap-2"><LockKey size={16} className="text-[#C9922A] mt-0.5"/><div>Escrow-protected — seller is paid only once you confirm receipt.</div></div>
              </div>
            )}
          </div>
        </div>
      </div>
    </ShopShell>
  );
}
