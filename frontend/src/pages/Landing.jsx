import { Link, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { ArrowRight, Globe, ShieldCheck, CurrencyCircleDollar, Package, ChartLineUp, Lightning } from "@phosphor-icons/react";
import { useAuth } from "../lib/auth-context";

const CARGO_IMG = "https://images.pexels.com/photos/12047372/pexels-photo-12047372.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940";
const TEXTILE_IMG = "https://images.unsplash.com/photo-1768212566108-4ce4f329e4d2?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1ODB8MHwxfHNlYXJjaHwxfHxmYXNoaW9uJTIwdGV4dGlsZXMlMjBhZnJpY2FufGVufDB8fHx8MTc3NjgyNDU2MHww&ixlib=rb-4.1.0&q=85";
const AGRO_IMG = "https://images.unsplash.com/photo-1622676566956-b42b50c84c31?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1NTJ8MHwxfHNlYXJjaHwzfHxhZ3JpY3VsdHVyZSUyMGZhcm1lciUyMGFmcmljYW58ZW58MHx8fHwxNzc2ODI0NTYxfDA&ixlib=rb-4.1.0&q=85";

export default function Landing() {
  const { user } = useAuth();
  const nav = useNavigate();
  useEffect(() => {
    if (!user) return;
    if (user.role === "consumer") nav("/shop");
    else if (user.role === "jompstart_admin") nav("/admin/credit");
    else nav("/dashboard");
  }, [user, nav]);

  return (
    <div className="min-h-screen bg-[#0A1628] text-[#F5F5F5]">
      {/* top bar */}
      <header className="fixed top-0 inset-x-0 z-30 bg-[#0A1628]/85 backdrop-blur border-b border-[#1A7A6E]/15">
        <div className="max-w-[1400px] mx-auto px-6 lg:px-10 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3" data-testid="brand-link">
            <img src="/jomp-favicon.png" alt="Jomp" className="w-9 h-9 rounded-full"/>
            <div className="leading-tight">
              <div className="font-bold tracking-[0.22em] text-sm">JOMP TRADE</div>
              <div className="text-[10px] tracking-[0.3em] text-[#1A7A6E] font-mono">EXPORT OS</div>
            </div>
          </Link>
          <nav className="hidden md:flex items-center gap-8 text-[13px] text-[#9CA3AF]">
            <a href="#solutions" className="hover:text-[#F5F5F5]">Solutions</a>
            <a href="#modules" className="hover:text-[#F5F5F5]">Modules</a>
            <Link to="/shop" className="hover:text-[#F5F5F5]" data-testid="shop-nav-link">Shop</Link>
            <a href="#partners" className="hover:text-[#F5F5F5]">Partners</a>
          </nav>
          <div className="flex items-center gap-3">
            <Link to="/login" data-testid="login-link" className="text-[13px] text-[#9CA3AF] hover:text-[#F5F5F5]">Sign in</Link>
            <Link to="/register" data-testid="register-cta" className="helix-btn-primary text-sm">Get Started</Link>
          </div>
        </div>
      </header>

      {/* HERO */}
      <section className="pt-36 pb-24 relative overflow-hidden">
        <div className="helix-dot-bg absolute inset-0 opacity-70 pointer-events-none" />
        <div className="max-w-[1400px] mx-auto px-6 lg:px-10 grid lg:grid-cols-12 gap-12 items-center relative">
          <div className="lg:col-span-7 fade-up">
            <div className="helix-kicker mb-5">Africa → United States · Export Operating System</div>
            <h1 className="helix-h1 max-w-3xl">
              The <span className="text-[#C9922A]">command center</span> for cross-border trade
              out of Nigeria &amp; Africa.
            </h1>
            <p className="mt-6 text-[17px] text-[#9CA3AF] leading-relaxed max-w-xl">
              Jomp Trade unifies exporter onboarding, US-compliant product listings,
              full order lifecycle, document automation, and USD/NGN banking &mdash;
              with Riby Inc escrow and JompStart credit under the hood &mdash; so one trade
              doesn&rsquo;t take ten tools.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/register" data-testid="hero-cta-primary" className="helix-btn-primary inline-flex items-center gap-2">
                Open an account <ArrowRight size={16} weight="bold" />
              </Link>
              <Link to="/catalog" data-testid="hero-cta-browse" className="helix-btn-secondary inline-flex items-center gap-2">
                Browse marketplace
              </Link>
              <Link to="/shop" data-testid="hero-cta-shop" className="text-[13px] text-[#C9922A] font-semibold inline-flex items-center gap-1 hover:gap-2 transition-all pl-2">
                Or shop direct from Africa →
              </Link>
            </div>

            <div className="mt-12 grid grid-cols-3 gap-6 max-w-xl">
              {[
                { k: "$0", v: "to open an NGN + USD account" },
                { k: "1%", v: "flat platform fee per trade" },
                { k: "7", v: "lifecycle stages tracked" },
              ].map((s) => (
                <div key={s.v}>
                  <div className="font-mono text-3xl text-[#C9922A] font-bold tracking-tight">{s.k}</div>
                  <div className="text-[11px] uppercase tracking-[0.12em] text-[#9CA3AF] mt-1 leading-snug">{s.v}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="lg:col-span-5 relative fade-up-delay-2">
            <div className="relative aspect-[4/5] w-full rounded overflow-hidden border border-[#1A7A6E]/30">
              <img src={CARGO_IMG} alt="Cargo ship" className="w-full h-full object-cover" />
              <div className="absolute inset-0" style={{ background: "linear-gradient(180deg, rgba(10,22,40,0.25) 0%, rgba(10,22,40,0.78) 100%)" }}/>
              <div className="absolute bottom-5 left-5 right-5 helix-card !bg-[#0A1628]/85 p-4">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-[10px] font-mono tracking-widest text-[#1A7A6E]">LIVE · ESCROW BY RIBY INC</span>
                  <span className="helix-status helix-status-ok">ONLINE</span>
                </div>
                <div className="font-mono text-[11px] text-[#F5F5F5] space-y-1">
                  <div className="flex justify-between"><span className="text-[#9CA3AF]">VA · NGN</span><span>016-228-3094</span></div>
                  <div className="flex justify-between"><span className="text-[#9CA3AF]">VA · USD</span><span>HLX-USD-A1F8C22E</span></div>
                  <div className="flex justify-between"><span className="text-[#9CA3AF]">Latest Tx</span><span className="text-[#C9922A]">+USD 15,600.00</span></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* MODULES */}
      <section id="modules" className="py-20 border-t border-[#1A7A6E]/15">
        <div className="max-w-[1400px] mx-auto px-6 lg:px-10">
          <div className="helix-kicker mb-3">Five modules. One platform.</div>
          <h2 className="helix-h2 max-w-2xl">Everything your trade desk needs &mdash; already wired together.</h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4 mt-10">
            {[
              { icon: ShieldCheck, title: "Onboarding & Verification", body: "Nigeria KYC / KYB with CAC, BVN, TIN. US-side EIN. Anchor customers created automatically on approval." },
              { icon: Package, title: "Product & Export Catalog", body: "Dual-currency pricing from live FX, compliance badges, marketplace browsable by buyers." },
              { icon: ChartLineUp, title: "Trade & Order Management", body: "RFQ → Proforma → Confirmation → Production → Shipment → Delivery, with Riby Inc–held escrow accounts per order." },
              { icon: ShieldCheck, title: "Compliance Vault", body: "SON, NAFDAC, phytosanitary, FDA prior notice. Expiry alerts at 30 and 7 days. Auto score per business." },
              { icon: CurrencyCircleDollar, title: "Anchor-Powered Finance", body: "NGN + USD balances, virtual accounts, NIP withdrawals, book transfers, platform fees — all live via Anchor." },
              { icon: Lightning, title: "Document Automation", body: "Commercial Invoice, Packing List, Proforma, Certificate of Origin — generated on demand, ready to ship." },
            ].map((m, i) => {
              const Icon = m.icon;
              return (
                <div key={m.title} className="helix-card p-6 fade-up" style={{ animationDelay: `${80 * i}ms` }}>
                  <Icon size={22} weight="regular" className="text-[#C9922A]" />
                  <h3 className="helix-h3 mt-4">{m.title}</h3>
                  <p className="text-[14px] text-[#9CA3AF] mt-3 leading-relaxed">{m.body}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* SECTORS */}
      <section id="solutions" className="py-20 border-t border-[#1A7A6E]/15">
        <div className="max-w-[1400px] mx-auto px-6 lg:px-10 grid md:grid-cols-2 gap-10 items-center">
          <div>
            <div className="helix-kicker mb-3">Built for the trades we actually move</div>
            <h2 className="helix-h2">Fashion &amp; textiles. Agriculture. Staple foods. Physical goods.</h2>
            <p className="text-[#9CA3AF] mt-5 leading-relaxed">
              From Adire panels shipping out of Abeokuta to single-origin Ofada rice headed to Brooklyn,
              Jomp Trade routes every dollar and document through one place &mdash; with Riby Inc holding
              buyer funds in escrow until goods land.
            </p>
            <div className="mt-8 grid grid-cols-2 gap-3 max-w-md">
              {["Fashion", "Agriculture", "Staple Foods", "General Goods"].map((s) => (
                <div key={s} className="helix-card p-3 text-center text-[13px] font-medium">{s}</div>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <img src={TEXTILE_IMG} alt="Textile" className="w-full h-72 object-cover rounded border border-[#1A7A6E]/25" />
            <img src={AGRO_IMG} alt="Agriculture" className="w-full h-72 object-cover rounded border border-[#1A7A6E]/25 translate-y-8" />
          </div>
        </div>
      </section>

      {/* PARTNERS */}
      <section id="partners" className="py-20 border-t border-[#1A7A6E]/15">
        <div className="max-w-[1400px] mx-auto px-6 lg:px-10">
          <div className="text-center">
            <div className="helix-kicker mb-3">Powered By</div>
            <h2 className="helix-h2 max-w-2xl mx-auto">Three operating partners. One unified platform.</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-10">
            <div className="helix-card p-6">
              <div className="text-[#C9922A] font-bold tracking-[0.22em] text-sm">RIBY INC</div>
              <div className="text-[10px] tracking-[0.3em] text-[#1A7A6E] font-mono mt-1">US &amp; GLOBAL</div>
              <p className="text-[12px] text-[#9CA3AF] mt-4 leading-relaxed">
                US &amp; Global operations and transaction management. Payment collection entity, escrow custodian,
                and Delivery Partner of Record for direct-to-consumer shipments.
              </p>
            </div>
            <div className="helix-card p-6">
              <div className="text-[#C9922A] font-bold tracking-[0.22em] text-sm">JOMPSTART DIGITAL</div>
              <div className="text-[10px] tracking-[0.3em] text-[#1A7A6E] font-mono mt-1">NIGERIA &amp; AFRICA · TECH · CREDIT</div>
              <p className="text-[12px] text-[#9CA3AF] mt-4 leading-relaxed">
                Nigeria &amp; Africa ground operations. Builds and maintains the platform and technology integrations.
                Underwrites and manages Business Credit to suppliers.
              </p>
            </div>
            <div className="helix-card p-6">
              <div className="text-[#C9922A] font-bold tracking-[0.22em] text-sm">ANCHOR</div>
              <div className="text-[10px] tracking-[0.3em] text-[#1A7A6E] font-mono mt-1">BANKING INFRASTRUCTURE</div>
              <p className="text-[12px] text-[#9CA3AF] mt-4 leading-relaxed">
                Global Business Banking and Payment Services &mdash; NGN &amp; USD deposit accounts, virtual accounts,
                transfers, and reconciliation.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* FINAL CTA */}
      <section className="py-24 border-t border-[#1A7A6E]/15">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="helix-h2">Ready to take your exports international?</h2>
          <p className="text-[#9CA3AF] mt-4">Create your account, upload your CAC, and start receiving USD in minutes.</p>
          <div className="mt-8 flex items-center justify-center gap-3">
            <Link to="/register" className="helix-btn-primary inline-flex items-center gap-2">
              Start free <ArrowRight size={16} weight="bold" />
            </Link>
            <Link to="/login" className="helix-btn-secondary">I already have an account</Link>
          </div>
        </div>
      </section>

      <footer className="border-t border-[#1A7A6E]/15 py-10">
        <div className="max-w-[1400px] mx-auto px-6 lg:px-10 text-center">
          <div className="text-[12px] text-[#9CA3AF]">Jomp Trade — Connecting Africa to the World, One Trade at a Time</div>
          <div className="text-[11px] text-[#1A7A6E] font-mono tracking-widest mt-3 flex flex-wrap justify-center gap-x-3 gap-y-1">
            <span>RIBY INC</span><span>·</span>
            <span>JOMPSTART DIGITAL LIMITED</span><span>·</span>
            <span>ANCHOR</span>
          </div>
          <div className="text-[10px] text-[#6b7280] mt-5 max-w-2xl mx-auto leading-relaxed italic">
            Riby Inc and JompStart Digital Limited are DobbleHelix Limited companies
            (<a href="https://dobblehelix.com" className="text-[#9CA3AF] hover:text-[#C9922A]" target="_blank" rel="noopener noreferrer">dobblehelix.com</a> · also known as BusinessLab Africa).
          </div>
        </div>
      </footer>
    </div>
  );
}
