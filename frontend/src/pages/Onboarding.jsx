import { useEffect, useState } from "react";
import Shell from "../components/Shell";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth-context";
import { StatusPill } from "../components/StatusPill";
import { toast } from "sonner";
import { CheckCircle, ArrowRight } from "@phosphor-icons/react";

const SECTORS = [
  { value: "fashion", label: "Fashion & Textiles" },
  { value: "agriculture", label: "Agriculture" },
  { value: "staple-foods", label: "Staple Foods" },
  { value: "general-goods", label: "General Goods" },
];

export default function Onboarding() {
  const { user, refresh } = useAuth();
  const [biz, setBiz] = useState(null);
  const [loading, setLoading] = useState(true);
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({
    business_name: "",
    registration_type: "business",
    country: "Nigeria",
    sector: "fashion",
    role: user?.role || "exporter",
    cac_number: "",
    tin: "",
    bvn: "",
    nin: "",
    ein: "",
    director_name: "",
    contact_phone: "",
    contact_email: user?.email || "",
    address: "",
  });
  const [kycForm, setKycForm] = useState({ bvn: "", nin: "", cac_number: "", tin: "", director_name: "", docs: [] });

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/businesses/me");
        if (data) {
          setBiz(data);
          setStep(2);
          setKycForm({
            bvn: data.bvn || "",
            nin: data.nin || "",
            cac_number: data.cac_number || "",
            tin: data.tin || "",
            director_name: data.director_name || "",
            docs: [],
          });
        }
      } finally { setLoading(false); }
    })();
  }, []);

  const upd = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const createBiz = async (e) => {
    e.preventDefault();
    try {
      const { data } = await api.post("/businesses", form);
      setBiz(data);
      toast.success("Business profile created. Anchor customer provisioned.");
      await refresh();
      setStep(2);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to create business");
    }
  };

  const uploadDoc = async (e) => {
    const files = Array.from(e.target.files || []);
    for (const f of files) {
      const fd = new FormData();
      fd.append("file", f);
      try {
        const { data } = await api.post("/upload?kind=kyc", fd, { headers: { "Content-Type": "multipart/form-data" } });
        setKycForm((k) => ({ ...k, docs: [...k.docs, data.storage_path] }));
        toast.success(`Uploaded ${f.name}`);
      } catch {
        toast.error(`Failed to upload ${f.name}`);
      }
    }
  };

  const submitKyc = async () => {
    try {
      const endpoint = biz.registration_type === "business" ? "kyb" : "kyc";
      await api.post(`/businesses/${biz.id}/${endpoint}`, kycForm);
      toast.success("Documents submitted — under review");
      const { data } = await api.get("/businesses/me");
      setBiz(data);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Submission failed");
    }
  };

  if (loading) return <Shell title="Onboarding"><div className="p-10 text-[#9CA3AF]">Loading…</div></Shell>;

  return (
    <Shell title="Business Onboarding" kicker="Step by step · KYC & KYB">
      <div className="max-w-4xl">
        {/* Stepper */}
        <div className="flex items-center gap-4 mb-10">
          {[
            { n: 1, label: "Business Profile", done: !!biz },
            { n: 2, label: biz?.registration_type === "individual" ? "KYC Documents" : "KYB Documents", done: biz && (biz.kyc_status === "under_review" || biz.kyb_status === "under_review" || biz.kyc_status === "approved" || biz.kyb_status === "approved") },
            { n: 3, label: "Anchor Accounts", done: !!biz?.anchor_account_ngn },
          ].map((s, i) => (
            <div key={s.n} className="flex items-center gap-3">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center font-mono text-sm ${s.done ? "bg-[#C9922A] text-[#0A1628]" : step === s.n ? "bg-[#1A7A6E] text-white" : "bg-[#0F2040] border border-[#1A7A6E]/30 text-[#9CA3AF]"}`}>
                {s.done ? <CheckCircle size={16} weight="fill"/> : s.n}
              </div>
              <div>
                <div className="text-[13px] font-medium">{s.label}</div>
              </div>
              {i < 2 && <div className="w-10 h-px bg-[#1A7A6E]/30"/>}
            </div>
          ))}
        </div>

        {step === 1 && !biz && (
          <form onSubmit={createBiz} className="helix-card p-6 space-y-5 fade-up" data-testid="biz-create-form">
            <h2 className="helix-h3">Create your business profile</h2>
            <div className="grid md:grid-cols-2 gap-4">
              <Field label="Business name"><input data-testid="biz-name" className="helix-input" value={form.business_name} onChange={upd("business_name")} required/></Field>
              <Field label="Registration type">
                <select data-testid="biz-type" className="helix-input" value={form.registration_type} onChange={upd("registration_type")}>
                  <option value="business">Business Entity</option>
                  <option value="individual">Individual</option>
                </select>
              </Field>
              <Field label="Country">
                <select data-testid="biz-country" className="helix-input" value={form.country} onChange={upd("country")}>
                  <option>Nigeria</option><option>United States</option><option>Ghana</option><option>Kenya</option><option>South Africa</option>
                </select>
              </Field>
              <Field label="Sector">
                <select data-testid="biz-sector" className="helix-input" value={form.sector} onChange={upd("sector")}>
                  {SECTORS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
                </select>
              </Field>
              <Field label="Contact phone"><input className="helix-input" value={form.contact_phone} onChange={upd("contact_phone")} /></Field>
              <Field label="Contact email"><input type="email" className="helix-input" value={form.contact_email} onChange={upd("contact_email")} /></Field>
              <Field label="Address" full><input className="helix-input" value={form.address} onChange={upd("address")} /></Field>
              {form.country === "Nigeria" && form.registration_type === "business" && (
                <>
                  <Field label="CAC Number"><input className="helix-input" value={form.cac_number} onChange={upd("cac_number")} placeholder="RC-XXXXXXX"/></Field>
                  <Field label="TIN"><input className="helix-input" value={form.tin} onChange={upd("tin")} /></Field>
                  <Field label="Director Name"><input className="helix-input" value={form.director_name} onChange={upd("director_name")} /></Field>
                </>
              )}
              {form.country === "Nigeria" && form.registration_type === "individual" && (
                <>
                  <Field label="BVN (11 digits)"><input className="helix-input" value={form.bvn} onChange={upd("bvn")} maxLength={11} /></Field>
                  <Field label="NIN"><input className="helix-input" value={form.nin} onChange={upd("nin")} /></Field>
                </>
              )}
              {form.country === "United States" && (
                <Field label="EIN (9 digits)"><input className="helix-input" value={form.ein} onChange={upd("ein")} placeholder="XX-XXXXXXX"/></Field>
              )}
            </div>
            <button data-testid="biz-submit" className="helix-btn-primary inline-flex items-center gap-2">Continue <ArrowRight size={14}/></button>
          </form>
        )}

        {step >= 2 && biz && (
          <div className="space-y-6">
            <div className="helix-card p-6">
              <div className="flex items-start justify-between flex-wrap gap-3">
                <div>
                  <div className="helix-label">{biz.business_name}</div>
                  <div className="helix-h3 mt-1">{biz.sector.replace("-", " ")} · {biz.country}</div>
                  <div className="text-[12px] text-[#9CA3AF] font-mono mt-1">Anchor customer · {biz.anchor_customer_id}</div>
                </div>
                <div className="flex gap-2">
                  <div>
                    <div className="text-[10px] tracking-widest text-[#9CA3AF] mb-1">KYC</div>
                    <StatusPill status={biz.kyc_status} />
                  </div>
                  <div>
                    <div className="text-[10px] tracking-widest text-[#9CA3AF] mb-1">KYB</div>
                    <StatusPill status={biz.kyb_status} />
                  </div>
                </div>
              </div>
            </div>

            {(biz.kyc_status !== "approved" && biz.kyb_status !== "approved") && (
              <div className="helix-card p-6 space-y-5">
                <h2 className="helix-h3">{biz.registration_type === "business" ? "KYB Documents" : "KYC Documents"}</h2>
                <p className="text-[#9CA3AF] text-sm">
                  Upload scans of {biz.registration_type === "business" ? "CAC certificate, TIN, director ID and proof of address" : "government ID, BVN slip, proof of address"}. Helix will forward to Anchor for verification.
                </p>
                <div className="grid md:grid-cols-2 gap-4">
                  {biz.registration_type === "business" ? (
                    <>
                      <Field label="CAC Number"><input className="helix-input" value={kycForm.cac_number} onChange={(e)=>setKycForm({...kycForm, cac_number: e.target.value})}/></Field>
                      <Field label="TIN"><input className="helix-input" value={kycForm.tin} onChange={(e)=>setKycForm({...kycForm, tin: e.target.value})}/></Field>
                      <Field label="Director Name"><input className="helix-input" value={kycForm.director_name} onChange={(e)=>setKycForm({...kycForm, director_name: e.target.value})}/></Field>
                    </>
                  ) : (
                    <>
                      <Field label="BVN"><input className="helix-input" value={kycForm.bvn} onChange={(e)=>setKycForm({...kycForm, bvn: e.target.value})} maxLength={11}/></Field>
                      <Field label="NIN"><input className="helix-input" value={kycForm.nin} onChange={(e)=>setKycForm({...kycForm, nin: e.target.value})}/></Field>
                    </>
                  )}
                </div>
                <div>
                  <label className="helix-label">Upload documents (PDF, image)</label>
                  <input data-testid="kyc-upload" type="file" multiple accept=".pdf,image/*" onChange={uploadDoc}
                         className="helix-input file:mr-4 file:py-1 file:px-3 file:rounded file:border-0 file:bg-[#C9922A]/20 file:text-[#C9922A] file:font-medium"/>
                  <div className="mt-2 text-[12px] text-[#9CA3AF]">{kycForm.docs.length} file(s) staged.</div>
                </div>
                <button data-testid="kyc-submit" onClick={submitKyc} disabled={kycForm.docs.length === 0}
                        className="helix-btn-primary inline-flex items-center gap-2">
                  Submit for review <ArrowRight size={14}/>
                </button>
              </div>
            )}

            {(biz.kyc_status === "approved" || biz.kyb_status === "approved") && (
              <div className="helix-card p-6">
                <div className="flex items-start gap-4">
                  <CheckCircle size={28} weight="fill" className="text-[#C9922A]"/>
                  <div>
                    <h3 className="helix-h3">Verification approved</h3>
                    <p className="text-[#9CA3AF] text-sm mt-1">Your NGN and USD deposit accounts are active.</p>
                    <div className="mt-4 grid grid-cols-2 gap-4 font-mono">
                      <div>
                        <div className="text-[11px] text-[#9CA3AF] uppercase">NGN Virtual Account</div>
                        <div className="text-[15px] text-[#C9922A]">{biz.anchor_ngn_virtual_account}</div>
                      </div>
                      <div>
                        <div className="text-[11px] text-[#9CA3AF] uppercase">USD Virtual Account</div>
                        <div className="text-[15px] text-[#C9922A]">{biz.anchor_usd_virtual_account}</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </Shell>
  );
}

function Field({ label, children, full }) {
  return (
    <div className={full ? "md:col-span-2" : ""}>
      <label className="helix-label">{label}</label>
      {children}
    </div>
  );
}
