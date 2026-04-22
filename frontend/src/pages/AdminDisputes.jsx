import { useEffect, useState } from "react";
import Shell from "../components/Shell";
import { api, formatDateTime } from "../lib/api";
import { StatusPill } from "../components/StatusPill";
import { toast } from "sonner";

export default function AdminDisputes() {
  const [items, setItems] = useState([]);
  const [resolution, setResolution] = useState({});
  const load = async () => { const { data } = await api.get("/admin/disputes"); setItems(data); };
  useEffect(() => { load(); }, []);
  const resolve = async (id, status) => {
    try {
      await api.post(`/admin/disputes/${id}/resolve`, { status, resolution: resolution[id] || "" });
      toast.success(`Marked ${status}`); load();
    } catch (err) { toast.error(err.response?.data?.detail || "Failed"); }
  };
  return (
    <Shell title="Disputes Queue" kicker="Operations · Mediation">
      {items.length === 0 ? (
        <div className="helix-card p-12 text-center text-[#9CA3AF]">No disputes at this time.</div>
      ) : (
        <div className="space-y-4">
          {items.map((d) => (
            <div key={d.id} className="helix-card p-6" data-testid={`dispute-${d.id}`}>
              <div className="flex justify-between items-start flex-wrap gap-3">
                <div>
                  <div className="helix-h3">{d.reason}</div>
                  <div className="text-[12px] text-[#9CA3AF] mt-1">Order <span className="font-mono text-[#C9922A]">{d.order_id}</span> · {formatDateTime(d.created_at)}</div>
                  <p className="mt-3 text-[14px]">{d.description}</p>
                </div>
                <StatusPill status={d.status}/>
              </div>
              <div className="mt-4 flex gap-2 flex-wrap">
                <input placeholder="Resolution note..." className="helix-input flex-1 min-w-[200px]" value={resolution[d.id] || ""} onChange={(e)=>setResolution({...resolution, [d.id]: e.target.value})}/>
                <button onClick={() => resolve(d.id, "resolved")} className="helix-btn-primary">Mark resolved</button>
                <button onClick={() => resolve(d.id, "rejected")} className="helix-btn-secondary">Reject</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </Shell>
  );
}
