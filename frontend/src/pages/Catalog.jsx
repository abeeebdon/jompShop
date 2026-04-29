import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import Shell from "../components/Shell";
import { api, formatUSD, formatNGN } from "../lib/api";
import { StatusPill } from "../components/StatusPill";
import { MagnifyingGlass, CheckCircle } from "@phosphor-icons/react";
import Pagination, { paginate } from "../components/Pagination";

const PER_PAGE = 12;

const CATEGORIES = [
  { value: "", label: "All Sectors" },
  { value: "fashion", label: "Fashion & Textiles" },
  { value: "agriculture", label: "Agriculture" },
  { value: "staple-foods", label: "Staple Foods" },
  { value: "general-goods", label: "General Goods" },
];

export default function Catalog() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState("");
  const [country, setCountry] = useState("");
  const [search, setSearch] = useState("");

  useEffect(() => {
    (async () => {
      setLoading(true);
      const params = {};
      if (category) params.category = category;
      if (country) params.country = country;
      if (search) params.search = search;
      const { data } = await api.get("/products", { params });
      setItems(data);
      setLoading(false);
    })();
  }, [category, country, search]);

  return (
    <Shell title="Marketplace" kicker="Verified African Suppliers"
      actions={
        <div className="relative">
          <MagnifyingGlass size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#9CA3AF]"/>
          <input data-testid="catalog-search" placeholder="Search products..." value={search} onChange={(e)=>setSearch(e.target.value)}
                 className="helix-input pl-9 w-64"/>
        </div>
      }>
      <div className="flex flex-wrap gap-2 mb-8">
        {CATEGORIES.map((c) => (
          <button
            key={c.value}
            data-testid={`filter-${c.value || 'all'}`}
            onClick={() => setCategory(c.value)}
            className={`px-4 py-2 rounded-full text-[12px] font-medium border transition ${
              category === c.value
                ? "bg-[#C9922A] text-[#0A1628] border-[#C9922A]"
                : "bg-transparent text-[#9CA3AF] border-[#1A7A6E]/40 hover:border-[#1A7A6E]"
            }`}>{c.label}</button>
        ))}
        <select className="helix-input ml-auto w-40" value={country} onChange={(e)=>setCountry(e.target.value)} data-testid="filter-country">
          <option value="">All Countries</option>
          <option value="Nigeria">Nigeria</option>
          <option value="Ghana">Ghana</option>
          <option value="Kenya">Kenya</option>
        </select>
      </div>

      {loading ? <div className="text-[#9CA3AF]">Loading marketplace…</div> : (() => {
        const p = paginate(items, page, PER_PAGE);
        return (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {p.items.map((it) => <ProductCard key={it.id} p={it} />)}
              {items.length === 0 && <div className="col-span-full text-center text-[#9CA3AF] py-20">No products match your filters.</div>}
            </div>
            <Pagination page={p.page} totalPages={p.totalPages} onChange={(np)=>{ setPage(np); window.scrollTo({ top: 0, behavior: "smooth" }); }}/>
          </>
        );
      })()}
    </Shell>
  );
}

function ProductCard({ p }) {
  return (
    <Link to={`/products/${p.id}`} className="helix-card group overflow-hidden flex flex-col" data-testid={`product-${p.id}`}>
      <div className="aspect-[4/3] bg-[#0A1628] relative overflow-hidden">
        <img src={p.photos?.[0]} alt={p.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
        <div className="absolute top-3 left-3 flex gap-1 flex-wrap">
          {p.compliance_badges?.slice(0, 2).map((b) => (
            <span key={b} className="helix-status helix-status-gold">{b}</span>
          ))}
        </div>
        <div className="absolute bottom-3 right-3">
          {p.export_readiness_score >= 80 && (
            <span className="helix-status helix-status-ok"><CheckCircle size={10} weight="fill"/> Export Ready</span>
          )}
        </div>
      </div>
      <div className="p-4 flex-1 flex flex-col">
        <div className="text-[11px] font-mono uppercase tracking-wider text-[#1A7A6E]">{p.category.replace("-", " ")}</div>
        <div className="helix-h3 mt-1 line-clamp-2">{p.name}</div>
        <div className="mt-auto pt-4 flex items-end justify-between">
          <div>
            <div className="font-mono text-xl text-[#C9922A] font-bold">{formatUSD(p.price_usd)}</div>
            <div className="text-[11px] text-[#9CA3AF] font-mono">{formatNGN(p.price_ngn)}</div>
          </div>
          <div className="text-right">
            <div className="text-[10px] uppercase tracking-wider text-[#9CA3AF]">MOQ</div>
            <div className="font-mono text-[13px]">{p.min_order_qty} {p.unit}</div>
          </div>
        </div>
      </div>
    </Link>
  );
}
