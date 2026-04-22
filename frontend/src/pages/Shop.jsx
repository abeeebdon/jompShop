import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import ShopShell from "../components/ShopShell";
import { api, formatUSD } from "../lib/api";
import { MagnifyingGlass, Truck, Storefront, CheckCircle } from "@phosphor-icons/react";

const CATS = [
  { value: "", label: "All" },
  { value: "fashion", label: "Fashion" },
  { value: "agriculture", label: "Agriculture" },
  { value: "staple-foods", label: "Staple Foods" },
  { value: "general-goods", label: "General" },
];

export default function Shop() {
  const [params, setParams] = useSearchParams();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const category = params.get("category") || "";
  const mode = params.get("mode") || "";

  useEffect(() => {
    (async () => {
      setLoading(true);
      const q = {};
      if (category) q.category = category;
      if (mode) q.fulfillment = mode;
      if (search) q.search = search;
      const { data } = await api.get("/shop/listings", { params: q });
      setItems(data); setLoading(false);
    })();
  }, [category, mode, search]);

  return (
    <ShopShell>
      {/* Hero */}
      <section className="mb-10 relative">
        <div className="helix-card p-8 md:p-12 relative overflow-hidden">
          <div className="absolute -top-20 -right-20 w-96 h-96 rounded-full bg-[#C9922A]/10 blur-3xl pointer-events-none"/>
          <div className="helix-kicker mb-3">Helix Shop · From Africa, to your door</div>
          <h1 className="helix-h1 max-w-3xl">Shop direct from verified African makers &amp; US warehouses.</h1>
          <p className="text-[15px] text-[#9CA3AF] mt-5 max-w-2xl leading-relaxed">
            Two ways to buy: pick from our US-stocked warehouse inventory for 48-hour delivery,
            or order direct from Africa — <b>Riby Inc</b> is the delivery partner of record, handling import and last-mile.
          </p>
        </div>
      </section>

      {/* Mode filters */}
      <div className="flex flex-wrap gap-3 mb-8 items-center">
        <button onClick={()=>{ const p = new URLSearchParams(params); p.delete("mode"); setParams(p); }}
                className={`px-4 py-2 rounded-full text-[12px] border ${!mode ? "bg-[#C9922A] text-[#0A1628] border-[#C9922A]" : "border-[#1A7A6E]/40 text-[#9CA3AF] hover:border-[#1A7A6E]"}`} data-testid="mode-all">
          All sources
        </button>
        <button onClick={()=>{ const p = new URLSearchParams(params); p.set("mode","buyer_local"); setParams(p); }}
                className={`px-4 py-2 rounded-full text-[12px] border inline-flex items-center gap-2 ${mode === "buyer_local" ? "bg-[#C9922A] text-[#0A1628] border-[#C9922A]" : "border-[#1A7A6E]/40 text-[#9CA3AF] hover:border-[#1A7A6E]"}`} data-testid="mode-local">
          <Storefront size={14}/> US In-Stock · 48hr
        </button>
        <button onClick={()=>{ const p = new URLSearchParams(params); p.set("mode","riby_dtc"); setParams(p); }}
                className={`px-4 py-2 rounded-full text-[12px] border inline-flex items-center gap-2 ${mode === "riby_dtc" ? "bg-[#C9922A] text-[#0A1628] border-[#C9922A]" : "border-[#1A7A6E]/40 text-[#9CA3AF] hover:border-[#1A7A6E]"}`} data-testid="mode-dtc">
          <Truck size={14}/> Direct from Africa · Riby of Record
        </button>
        <div className="relative ml-auto">
          <MagnifyingGlass size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#9CA3AF]"/>
          <input placeholder="Search products..." value={search} onChange={(e)=>setSearch(e.target.value)} className="helix-input pl-9 w-64" data-testid="shop-search"/>
        </div>
      </div>

      {/* Category chips */}
      <div className="flex flex-wrap gap-2 mb-8">
        {CATS.map(c => (
          <button key={c.value} onClick={()=>{ const p = new URLSearchParams(params); if (c.value) p.set("category", c.value); else p.delete("category"); setParams(p); }}
                  className={`px-3 py-1.5 rounded-full text-[11px] font-mono tracking-wider uppercase border ${category === c.value ? "bg-[#1A7A6E]/20 text-[#1A7A6E] border-[#1A7A6E]" : "border-[#1A7A6E]/30 text-[#9CA3AF] hover:border-[#1A7A6E]/60"}`}>
            {c.label}
          </button>
        ))}
      </div>

      {loading ? <div className="text-[#9CA3AF]">Loading shop…</div> : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
          {items.map(l => <ListingCard key={l.id} l={l}/>)}
          {items.length === 0 && <div className="col-span-full text-center text-[#9CA3AF] py-16">No listings match your filters.</div>}
        </div>
      )}
    </ShopShell>
  );
}

function ListingCard({ l }) {
  const isDtc = l.fulfillment_mode === "riby_dtc";
  return (
    <Link to={`/shop/product/${l.id}`} data-testid={`listing-${l.id}`} className="helix-card group overflow-hidden flex flex-col">
      <div className="aspect-[4/3] relative overflow-hidden">
        <img src={l.photos?.[0]} alt={l.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
        <div className="absolute top-2 left-2">
          {isDtc ? (
            <span className="helix-status helix-status-gold"><Truck size={10}/> Direct · Riby of Record</span>
          ) : (
            <span className="helix-status helix-status-ok"><Storefront size={10} weight="fill"/> US · 48hr</span>
          )}
        </div>
      </div>
      <div className="p-4 flex-1 flex flex-col">
        <div className="text-[10px] font-mono uppercase tracking-wider text-[#1A7A6E]">{l.category.replace("-"," ")}</div>
        <div className="helix-h3 mt-1 line-clamp-2 text-[15px]">{l.title}</div>
        <div className="mt-auto pt-4 flex items-end justify-between">
          <div>
            <div className="font-mono text-xl text-[#C9922A] font-bold">{formatUSD(l.retail_price_usd)}</div>
            <div className="text-[10px] text-[#9CA3AF] font-mono uppercase tracking-wider">{l.seller_name}</div>
          </div>
          <div className="text-right text-[10px] text-[#9CA3AF]">
            {l.stock_qty > 5 ? <span className="text-[#1A7A6E]">In stock</span> : <span className="text-[#C9922A]">Only {l.stock_qty} left</span>}
          </div>
        </div>
      </div>
    </Link>
  );
}
