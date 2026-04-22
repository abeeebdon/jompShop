import Sidebar from "./Sidebar";

export default function Shell({ children, title, kicker, actions }) {
  return (
    <div className="min-h-screen bg-[#0A1628] text-[#F5F5F5]">
      <Sidebar />
      <div className="pl-16 lg:pl-60">
        <header className="sticky top-0 z-30 bg-[#0A1628]/95 backdrop-blur border-b border-[#1A7A6E]/15">
          <div className="max-w-[1400px] mx-auto px-6 lg:px-10 py-6 flex items-end justify-between gap-4 flex-wrap">
            <div>
              {kicker && <div className="helix-kicker mb-2" data-testid="page-kicker">{kicker}</div>}
              <h1 className="helix-h2" data-testid="page-title">{title}</h1>
            </div>
            {actions && <div className="flex items-center gap-3 flex-wrap">{actions}</div>}
          </div>
        </header>
        <main className="max-w-[1400px] mx-auto px-6 lg:px-10 py-8 fade-up">
          {children}
        </main>
      </div>
    </div>
  );
}
