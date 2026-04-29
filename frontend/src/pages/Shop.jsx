import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import ShopShell from "../components/ShopShell";
import { api, formatUSD } from "../lib/api";
import {
  MagnifyingGlass, Truck, Storefront, Package as PackageIcon,
  Coffee, Sparkle, Cube, ShoppingBag, House, Star,
} from "@phosphor-icons/react";
import Pagination, { paginate } from "../components/Pagination";

const PER_PAGE = 20;

const CATS = [
  { value: "fashion", label: "Fashion & Textiles", icon: ShoppingBag, hint: "Adire · Ankara · Kente · Aso-Oke" },
  { value: "agriculture", label: "Agriculture", icon: Coffee, hint: "Cocoa · Sesame · Cashew · Palm Oil" },
  { value: "staple-foods", label: "Staple Foods", icon: PackageIcon, hint: "Ofada Rice · Garri · Suya Spice" },
  { value: "beauty", label: "Beauty & Cosmetics", icon: Sparkle, hint: "Black Soap · Shea Butter · Marula Oil" },
  { value: "home-decor", label: "Home & Decor", icon: House, hint: "Bolga Baskets · Masks · Mudcloth" },
  { value: "accessories", label: "Accessories", icon: Cube, hint: "Leather · Maasai Beads · Raffia" },
  { value: "beverages", label: "Beverages", icon: Coffee, hint: "Hibiscus · Baobab · Rooibos" },
];

const FALLBACK_IMG = "https://images.unsplash.com/photo-1604329760661-e71dc83f8f26?auto=format&fit=crop&w=900&q=80";

export default function Shop() {
  const [params, setParams] = useSearchParams();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState(params.get("q") || "");
  const [page, setPage] = useState(1);
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
  useEffect(() => { setPage(1); }, [category, mode, search]);

  const submitSearch = (e) => {
    e.preventDefault();
    const p = new URLSearchParams(params);
    if (search) p.set("q", search); else p.delete("q");
    setParams(p);
  };

  const showCategoryGrid = !category && !mode && !search;

  return (
    <ShopShell>
      {/* HERO with prominent search */}
      <section className="mb-10 relative">
        <div className="helix-card p-8 md:p-14 relative overflow-hidden">
          <div className="absolute -top-20 -right-20 w-96 h-96 rounded-full bg-[#C9922A]/10 blur-3xl pointer-events-none"/>
          <div className="absolute -bottom-32 -left-20 w-80 h-80 rounded-full bg-[#1A7A6E]/10 blur-3xl pointer-events-none"/>
          <div className="relative">
            <div className="helix-kicker mb-3">Africa's marketplace · From maker to your door</div>
            <h1 className="helix-h1 max-w-4xl">Shop authentic African goods. Direct from makers.</h1>
            <p className="text-[15px] text-[#9CA3AF] mt-5 max-w-2xl leading-relaxed">
              Fashion, food, beauty, art &amp; home — sourced direct from verified African makers.
              Buy from US warehouses for 48-hour delivery, or order direct with <b>Riby Inc</b> as your
              delivery partner of record. Every order is <b>escrow-protected</b>.
            </p>
            <form onSubmit={submitSearch} className="mt-7 flex gap-2 max-w-2xl" data-testid="hero-search-form">
              <div className="relative flex-1">
                <MagnifyingGlass size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-[#9CA3AF]"/>
                <input
                  value={search}
                  onChange={(e)=>setSearch(e.target.value)}
                  placeholder="Search shea butter, ankara, cocoa beans, jewelry…"
                  className="helix-input pl-12 py-3.5 text-[15px]"
                  data-testid="hero-search-input"
                />
              </div>
              <button type="submit" className="helix-btn-primary px-7" data-testid="hero-search-submit">Search</button>
            </form>
          </div>
        </div>
      </section>

      {/* Category tiles — only on default landing */}
      {showCategoryGrid && (
        <section className="mb-10">
          <div className="flex items-end justify-between mb-5">
            <h2 className="helix-h3">Shop by category</h2>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3">
            {CATS.map((c) => {
              const Icon = c.icon;
              return (
                <button
                  key={c.value}
                  onClick={() => { const p = new URLSearchParams(params); p.set("category", c.value); setParams(p); }}
                  className="helix-card p-4 text-left hover:border-[#C9922A]/60 transition-colors group"
                  data-testid={`cat-${c.value}`}
                >
                  <Icon size={26} className="text-[#C9922A] mb-3 group-hover:scale-110 transition-transform" weight="duotone"/>
                  <div className="text-[13px] font-semibold leading-tight">{c.label}</div>
                  <div className="text-[10.5px] text-[#9CA3AF] mt-1.5 line-clamp-2">{c.hint}</div>
                </button>
              );
            })}
          </div>
        </section>
      )}

      {/* Filters bar — visible whenever a category/mode/search is active */}
      <div className="flex flex-wrap gap-3 mb-6 items-center">
        <button onClick={()=>{ setSearch(""); setParams(new URLSearchParams()); }}
                className="px-4 py-2 rounded-full text-[12px] border border-[#1A7A6E]/40 text-[#9CA3AF] hover:border-[#1A7A6E]" data-testid="reset-filters">
          ← All categories
        </button>
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
        {category && (
          <span className="px-3 py-1.5 rounded-full text-[11px] font-mono uppercase tracking-wider border border-[#C9922A]/50 text-[#C9922A] bg-[#C9922A]/10">
            {CATS.find(c=>c.value===category)?.label || category}
          </span>
        )}
        {search && <span className="text-[12px] text-[#9CA3AF]">Showing results for <b className="text-[#F5F5F5]">"{search}"</b></span>}
      </div>

      {/* Category chips (always shown) */}
      {!showCategoryGrid && (
        <div className="flex flex-wrap gap-2 mb-8">
          {CATS.map(c => (
            <button key={c.value} onClick={()=>{ const p = new URLSearchParams(params); p.set("category", c.value); setParams(p); }}
                    className={`px-3 py-1.5 rounded-full text-[11px] font-mono tracking-wider uppercase border ${category === c.value ? "bg-[#1A7A6E]/20 text-[#1A7A6E] border-[#1A7A6E]" : "border-[#1A7A6E]/30 text-[#9CA3AF] hover:border-[#1A7A6E]/60"}`}>
              {c.label}
            </button>
          ))}
        </div>
      )}

      {/* Products grid */}
      <div className="flex items-end justify-between mb-4">
        <h2 className="helix-h3">{showCategoryGrid ? "Featured today" : `${items.length} products`}</h2>
        {!loading && items.length > 0 && (
          <span className="text-[11px] font-mono uppercase tracking-wider text-[#1A7A6E] inline-flex items-center gap-1.5">
            <Star size={11} weight="fill"/> All escrow-protected
          </span>
        )}
      </div>
      {loading ? <div className="text-[#9CA3AF]">Loading shop…</div> : (() => {
        const p = paginate(items, page, PER_PAGE);
        return (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 gap-4">
              {p.items.map(l => <ListingCard key={l.id} l={l}/>)}
              {items.length === 0 && <div className="col-span-full text-center text-[#9CA3AF] py-16">No products match your filters.</div>}
            </div>
            <Pagination page={p.page} totalPages={p.totalPages} onChange={(np)=>{ setPage(np); window.scrollTo({ top: 0, behavior: "smooth" }); }}/>
            {items.length > 0 && (
              <div className="text-center text-[11px] text-[#9CA3AF] font-mono uppercase tracking-wider mt-1">
                Showing {p.start + 1}–{p.end} of {p.total}
              </div>
            )}
          </>
        );
      })()}
    </ShopShell>
  );
}

function ListingCard({ l }) {
  const isDtc = l.fulfillment_mode === "riby_dtc";
  const photo = l.photos?.[0] || FALLBACK_IMG;
  return (
    <Link to={`/shop/product/${l.id}`} data-testid={`listing-${l.id}`} className="helix-card group overflow-hidden flex flex-col">
      <div className="aspect-[4/3] relative overflow-hidden">
        <img src={photo} alt={l.title} loading="lazy" onError={(e)=>{ if (e.currentTarget.src !== FALLBACK_IMG) e.currentTarget.src = FALLBACK_IMG; }} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
        <div className="absolute top-2 left-2">
          {isDtc ? (
            <span className="helix-status helix-status-gold"><Truck size={10}/> Direct · Riby of Record</span>
          ) : (
            <span className="helix-status helix-status-ok"><Storefront size={10} weight="fill"/> US · 48hr</span>
          )}
        </div>
      </div>
      <div className="p-3.5 flex-1 flex flex-col">
        <div className="text-[10px] font-mono uppercase tracking-wider text-[#1A7A6E]">{l.category.replace("-"," ")}</div>
        <div className="helix-h3 mt-1 line-clamp-2 text-[14px] leading-snug">{l.title}</div>
        <div className="mt-auto pt-3 flex items-end justify-between">
          <div>
            <div className="font-mono text-lg text-[#C9922A] font-bold">{formatUSD(l.retail_price_usd)}</div>
            <div className="text-[10px] text-[#9CA3AF] font-mono uppercase tracking-wider truncate max-w-[140px]">{l.seller_name}</div>
          </div>
          <div className="text-right text-[10px] text-[#9CA3AF]">
            {l.stock_qty > 5 ? <span className="text-[#1A7A6E]">In stock</span> : <span className="text-[#C9922A]">Only {l.stock_qty} left</span>}
          </div>
        </div>
      </div>
    </Link>
  );
}
