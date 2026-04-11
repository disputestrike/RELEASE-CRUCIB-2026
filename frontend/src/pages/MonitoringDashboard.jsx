import { useState, useEffect } from "react";
import axios from "axios";
import { API } from "../App";
import { logApiError } from "../utils/apiError";

export default function MonitoringDashboard() {
  const [events, setEvents] = useState([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    let cancelled = false;
    axios
      .get(`${API}/monitoring/events`, { params: { limit: 50 } })
      .then((r) => {
        if (!cancelled) setEvents(r.data.events || []);
        if (!cancelled && r.data.message) setMessage(r.data.message);
      })
      .catch((e) => {
        logApiError("MonitoringDashboard events", e);
        if (!cancelled) setMessage(e?.response?.data?.detail || e?.message || "Failed to load events");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  const sendTestEvent = () => {
    setSending(true);
    axios
      .post(`${API}/monitoring/events/track`, {
        event_type: "feature_usage",
        user_id: "proof-test",
        metadata: { source: "MonitoringDashboard", test: true },
        success: true,
      })
      .then(() => {
        setMessage("Event tracked. Refresh to see it.");
        return axios.get(`${API}/monitoring/events`, { params: { limit: 50 } });
      })
      .then((r) => setEvents(r.data.events || []))
      .catch((e) => {
        logApiError("MonitoringDashboard track", e);
        setMessage(e?.response?.data?.detail || e?.message || "Track failed");
      })
      .finally(() => setSending(false));
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-xl font-semibold text-[#1A1A1A] mb-2">Monitoring (PostgreSQL proof)</h1>
      <p className="text-sm text-[#666] mb-4">
        Events are stored in PostgreSQL when <code className="bg-gray-100 px-1">DATABASE_URL</code> is set.
      </p>
      {message && (
        <p className="text-sm text-neutral-800 bg-neutral-100 border border-neutral-200 rounded p-2 mb-4">{message}</p>
      )}
      <button
        type="button"
        onClick={sendTestEvent}
        disabled={sending}
        className="mb-4 px-4 py-2 bg-[#1A1A1A] text-white rounded hover:bg-[#333] disabled:opacity-50 text-sm"
      >
        {sending ? "Sending…" : "Send test event"}
      </button>
      {loading ? (
        <p className="text-[#666]">Loading events…</p>
      ) : events.length === 0 ? (
        <p className="text-[#666]">No events yet. Click &quot;Send test event&quot; to add one (requires Postgres).</p>
      ) : (
        <ul className="space-y-2 border border-gray-200 rounded-lg divide-y divide-gray-100 overflow-hidden">
          {events.map((ev) => (
            <li key={ev.event_id} className="p-3 bg-white text-sm">
              <span className="font-medium text-[#1A1A1A]">{ev.event_type}</span>
              <span className="text-[#666] ml-2">user: {ev.user_id}</span>
              <span className="text-[#666] ml-2">{ev.timestamp ? new Date(ev.timestamp).toLocaleString() : ""}</span>
              {ev.metadata && Object.keys(ev.metadata).length > 0 && (
                <pre className="mt-1 text-xs text-[#666] overflow-x-auto">{JSON.stringify(ev.metadata)}</pre>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
