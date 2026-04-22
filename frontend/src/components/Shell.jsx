import Sidebar from "./Sidebar";
import ThemeToggle from "./ThemeToggle";

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
            <div className="flex items-center gap-3 flex-wrap">
              {actions}
              <ThemeToggle />
            </div>
          </div>
        </header>
        <main className="max-w-[1400px] mx-auto px-6 lg:px-10 py-8 fade-up">
          {children}
        </main>
        <footer className="border-t border-[#1A7A6E]/15 py-6 px-6 lg:px-10 max-w-[1400px] mx-auto">
          <div className="text-[10px] font-mono tracking-[0.2em] text-[#1A7A6E] flex flex-wrap gap-x-3 gap-y-1 justify-center uppercase">
            <span>Jomp Trade · Powered by</span>
            <span className="text-[#9CA3AF]">Riby Inc</span><span>·</span>
            <span className="text-[#9CA3AF]">JompStart Digital Limited</span><span>·</span>
            <span className="text-[#9CA3AF]">Anchor</span>
          </div>
        </footer>
      </div>
    </div>
  );
}
