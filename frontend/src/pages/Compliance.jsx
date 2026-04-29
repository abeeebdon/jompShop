import { useEffect, useState } from "react";
import Shell from "../components/Shell";
import { api, formatDate } from "../lib/api";
import { StatusPill } from "../components/StatusPill";
import { toast } from "sonner";
import { Plus, FileText, Trash } from "@phosphor-icons/react";

const DOC_TYPES = ["SON Certification", "NAFDAC", "Phytosanitary Certificate", "Fumigation Certificate", "FSSAI / FDA Equivalence", "Halal Certification", "Country of Origin Label", "Other"];

export default function Compliance() {
  const [docs, setDocs] = useState([]);
  const [score, setScore] = useState(null);
  const [requirements, setRequirements] = useState({});
  const [open, setOpen] = useState(false);

  const load = async () => {
    const [d, s] = await Promise.all([api.get("/compliance/documents"), api.get("/compliance/score")]);
    setDocs(d.data); setScore(s.data);
    if (s.data.category_scores) {
      const reqs = {};
      for (const cat of Object.keys(s.data.category_scores)) {
        const r = await api.get("/compliance/requirements", { params: { category: cat } });
        reqs[cat] = r.data;
      }
      setRequirements(reqs);
    }
  };
  useEffect(() => { load(); }, []);

  const del = async (id) => {
    if (!window.confirm("Remove this document?")) return;
    await api.delete(`/compliance/documents/${id}`);
    toast.success("Removed"); load();
  };

  return (
    <Shell title="Compliance Vault" kicker="Documents · Score · Alerts"
      actions={<button onClick={()=>setOpen(true)} className="helix-btn-primary inline-flex items-center gap-2" data-testid="add-doc-btn"><Plus size={14}/> Add document</button>}>
      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-4">
          <div className="helix-card p-6">
            <div className="helix-label">Compliance Score</div>
            <div className="font-mono text-5xl font-bold mt-2">
              {score?.score ?? "—"}<span className="text-[#9CA3AF] text-xl">/100</span>
            </div>
            <div className="mt-3 h-2 bg-[#0A1628] rounded-full overflow-hidden">
              <div className="h-full bg-[#C9922A]" style={{ width: `${score?.score || 0}%` }}/>
            </div>
          </div>
          {score?.missing?.length > 0 && (
            <div className="helix-card p-6">
              <div className="helix-label">Missing documents</div>
              <ul className="mt-3 space-y-2">
                {score.missing.map((m) => (
                  <li key={m} className="text-[13px] flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#C9922A]"/> {m}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {Object.entries(requirements).map(([cat, r]) => (
            <div key={cat} className="helix-card p-5">
              <div className="helix-label">{cat.replace("-"," ")} · US import guide</div>
              <ul className="mt-2 space-y-1.5 text-[12px] text-[#9CA3AF] leading-relaxed">
                {r.us_import_guide?.map((g) => <li key={g}>• {g}</li>)}
              </ul>
            </div>
          ))}
        </div>

        <div className="lg:col-span-2">
          <div className="helix-card overflow-hidden">
            <div className="px-5 py-4 border-b border-[#1A7A6E]/20"><div className="helix-label">Document Vault</div><div className="helix-h3 mt-1">{docs.length} document(s)</div></div>
            {docs.length === 0 ? (
              <div className="p-10 text-center text-[#9CA3AF]">No documents uploaded yet.</div>
            ) : (
              <table className="helix-table">
                <thead><tr><th>Type</th><th>Authority</th><th>Issued</th><th>Expiry</th><th>Status</th><th></th></tr></thead>
                <tbody>
                  {docs.map((d) => (
                    <tr key={d.id} data-testid={`doc-${d.id}`}>
                      <td><div className="flex items-center gap-2"><FileText size={16} className="text-[#C9922A]"/>{d.document_type}</div><div className="text-[11px] text-[#9CA3AF]">{d.original_filename}</div></td>
                      <td className="text-[12px]">{d.issuing_authority}</td>
                      <td className="font-mono text-[12px] text-[#9CA3AF]">{formatDate(d.issued_date)}</td>
                      <td className="font-mono text-[12px]">{formatDate(d.expiry_date)}</td>
                      <td><StatusPill status={d.status}/></td>
                      <td><button onClick={()=>del(d.id)} className="text-[#E74C3C] hover:text-[#ff8e82]"><Trash size={14}/></button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
      {open && <AddDocModal onClose={() => { setOpen(false); load(); }} />}
    </Shell>
  );
}

function AddDocModal({ onClose }) {
  const [form, setForm] = useState({ document_type: DOC_TYPES[0], issuing_authority: "", issued_date: "", expiry_date: "", file_url: "", original_filename: "" });
  const upload = async (e) => {
    const file = e.target.files?.[0]; if (!file) return;
    const fd = new FormData(); fd.append("file", file);
    const { data } = await api.post("/upload?kind=compliance", fd, { headers: { "Content-Type": "multipart/form-data" }});
    setForm({ ...form, file_url: data.storage_path, original_filename: file.name });
    toast.success("File uploaded");
  };
  const save = async () => {
    try { await api.post("/compliance/documents", form); toast.success("Added"); onClose(); }
    catch (err) { toast.error(err.response?.data?.detail || "Failed"); }
  };
  return (
    <div className="fixed inset-0 bg-[#0A1628]/80 flex items-start justify-center pt-16 pb-10 overflow-y-auto z-50 p-4" onClick={onClose}>
      <div onClick={(e)=>e.stopPropagation()} className="helix-card p-6 w-full max-w-md" data-testid="add-doc-modal">
        <h3 className="helix-h3">Add compliance document</h3>
        <div className="space-y-3 mt-4">
          <div><label className="helix-label">Type</label>
            <select className="helix-input" value={form.document_type} onChange={(e)=>setForm({...form, document_type: e.target.value})} data-testid="doc-type">
              {DOC_TYPES.map(t=><option key={t}>{t}</option>)}
            </select></div>
          <div><label className="helix-label">Issuing authority</label><input className="helix-input" value={form.issuing_authority} onChange={(e)=>setForm({...form, issuing_authority: e.target.value})}/></div>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="helix-label">Issued</label><input type="date" className="helix-input" value={form.issued_date} onChange={(e)=>setForm({...form, issued_date: e.target.value})}/></div>
            <div><label className="helix-label">Expires</label><input type="date" className="helix-input" value={form.expiry_date} onChange={(e)=>setForm({...form, expiry_date: e.target.value})}/></div>
          </div>
          <div><label className="helix-label">File</label><input type="file" className="helix-input" onChange={upload} data-testid="doc-file"/></div>
          <div className="flex gap-2 pt-2"><button onClick={onClose} className="helix-btn-secondary flex-1">Cancel</button><button onClick={save} className="helix-btn-primary flex-1" data-testid="doc-save">Save</button></div>
        </div>
      </div>
    </div>
  );
}
