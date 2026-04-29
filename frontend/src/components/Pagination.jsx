import { ReactNode } from "react";

/**
 * Reusable Pagination for arrays. Use `usePagination` for the data math
 * and render <Pagination .../> for the controls.
 */
export function paginate(arr, page, perPage) {
  const total = Array.isArray(arr) ? arr.length : 0;
  const totalPages = Math.max(1, Math.ceil(total / perPage));
  const safePage = Math.min(Math.max(1, page), totalPages);
  const start = (safePage - 1) * perPage;
  const slice = (arr || []).slice(start, start + perPage);
  return { items: slice, page: safePage, totalPages, total, start, end: start + slice.length };
}

export default function Pagination({ page, totalPages, onChange, testid = "pagination" }) {
  if (totalPages <= 1) return null;
  const pages = [];
  const window = 1; // pages on each side
  for (let i = 1; i <= totalPages; i++) {
    if (i === 1 || i === totalPages || Math.abs(i - page) <= window) pages.push(i);
    else if (pages[pages.length - 1] !== "…") pages.push("…");
  }
  return (
    <div className="flex items-center justify-center gap-1.5 mt-8 mb-2 flex-wrap" data-testid={testid}>
      <button
        disabled={page <= 1}
        onClick={() => onChange(page - 1)}
        className="px-3 py-1.5 text-[12px] rounded border border-[#1A7A6E]/30 text-[#9CA3AF] hover:border-[#1A7A6E] disabled:opacity-40"
        data-testid="page-prev"
      >‹ Prev</button>
      {pages.map((p, i) => p === "…" ? (
        <span key={`gap-${i}`} className="px-2 text-[12px] text-[#9CA3AF]">…</span>
      ) : (
        <button
          key={p}
          onClick={() => onChange(p)}
          className={`min-w-[34px] px-2.5 py-1.5 text-[12px] rounded border ${p === page ? "bg-[#C9922A] text-[#0A1628] border-[#C9922A] font-semibold" : "border-[#1A7A6E]/30 text-[#9CA3AF] hover:border-[#1A7A6E]"}`}
          data-testid={`page-${p}`}
        >{p}</button>
      ))}
      <button
        disabled={page >= totalPages}
        onClick={() => onChange(page + 1)}
        className="px-3 py-1.5 text-[12px] rounded border border-[#1A7A6E]/30 text-[#9CA3AF] hover:border-[#1A7A6E] disabled:opacity-40"
        data-testid="page-next"
      >Next ›</button>
    </div>
  );
}
