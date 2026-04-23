import { useState, useEffect } from 'react';
import {
  MessageSquare, User, X, Search, Archive, StopCircle,
  Clock, CheckCircle, Circle, ChevronRight, Filter
} from 'lucide-react';
import { useAuth } from '../authContext';
import { API_BASE as API } from '../apiBase';
import axios from 'axios';

const T = {
  bg:      'var(--theme-bg)',
  surface: 'var(--theme-surface)',
  border:  'rgba(255,255,255,0.12)',
  text:    'var(--theme-text)',
  muted:   'var(--theme-muted)',
  accent:  '#1A1A1A',
  success: '#10b981',
  danger:  '#ef4444',
  info:    '#3b82f6',
  warn:    '#737373',
  input:   'var(--theme-input, rgba(255,255,255,0.06))',
};

const FILTERS = ['All', 'Active', 'Ended', 'Archived'];

const channelColors = {
  web_widget: '#3b82f6', slack: '#4a154b', whatsapp: '#25D366',
  api_webhook: '#737373', api: '#737373', web: '#525252', unknown: T.muted,
};

const statusConfig = {
  active:   { color: T.success, label: 'Active', icon: Circle },
  ended:    { color: T.muted, label: 'Ended', icon: CheckCircle },
  archived: { color: T.warn, label: 'Archived', icon: Archive },
};

const Badge = ({ children, color }) => (
  <span style={{ display: 'inline-block', padding: '2px 9px', borderRadius: 20, fontSize: 11, fontWeight: 600, background: color ? `${color}22` : 'rgba(255,255,255,0.08)', color: color || T.text, whiteSpace: 'nowrap' }}>
    {children}
  </span>
);

const StatCard = ({ label, value, color }) => (
  <div style={{ background: T.surface, borderRadius: 12, padding: '16px 20px', border: `1px solid ${T.border}`, flex: 1, minWidth: 0 }}>
    <p style={{ fontSize: 11, fontWeight: 600, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.07em', margin: '0 0 6px' }}>{label}</p>
    <p style={{ fontSize: 24, fontWeight: 700, margin: 0, color: color || T.text }}>{value}</p>
  </div>
);

const formatDuration = (seconds) => {
  if (!seconds) return '—';
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
};

const formatTime = (ts) => {
  if (!ts) return '—';
  return new Date(ts).toLocaleString();
};

export default function SessionsPage() {
  const { token } = useAuth();
  const headers = { Authorization: 'Bearer ' + token };

  const [sessions, setSessions] = useState([]);
  const [stats, setStats] = useState({ total: 0, active: 0, ended_today: 0, avg_duration: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filterTab, setFilterTab] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSession, setSelectedSession] = useState(null);
  const [transcript, setTranscript] = useState([]);
  const [transcriptLoading, setTranscriptLoading] = useState(false);
  const [actioning, setActioning] = useState(null);

  const fetchSessions = async () => {
    try {
      setLoading(true);
      const params = filterTab !== 'All' ? `?status=${filterTab.toLowerCase()}` : '';
      const [sessRes, statsRes] = await Promise.allSettled([
        axios.get(`${API}/sessions${params}`, { headers }),
        axios.get(`${API}/sessions/stats`, { headers }),
      ]);
      if (sessRes.status === 'fulfilled') setSessions(sessRes.value.data?.sessions || sessRes.value.data || []);
      if (statsRes.status === 'fulfilled') setStats(statsRes.value.data || {});
    } catch (e) {
      setError('Failed to load sessions.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchSessions(); }, [filterTab]);

  const openSession = async (session) => {
    setSelectedSession(session);
    setTranscriptLoading(true);
    try {
      const res = await axios.get(`${API}/sessions/${session.id}/messages`, { headers });
      setTranscript(res.data?.messages || res.data || []);
    } catch (e) {
      setTranscript([]);
    } finally {
      setTranscriptLoading(false);
    }
  };

  const handleArchive = async (id) => {
    setActioning(id + '_archive');
    try {
      await axios.post(`${API}/sessions/${id}/archive`, {}, { headers });
      setSessions(prev => prev.map(s => s.id === id ? { ...s, status: 'archived' } : s));
      if (selectedSession?.id === id) setSelectedSession(s => ({ ...s, status: 'archived' }));
    } catch (e) {
      setError('Failed to archive session.');
    } finally {
      setActioning(null);
    }
  };

  const handleEnd = async (id) => {
    setActioning(id + '_end');
    try {
      await axios.post(`${API}/sessions/${id}/end`, {}, { headers });
      setSessions(prev => prev.map(s => s.id === id ? { ...s, status: 'ended' } : s));
      if (selectedSession?.id === id) setSelectedSession(s => ({ ...s, status: 'ended' }));
    } catch (e) {
      setError('Failed to end session.');
    } finally {
      setActioning(null);
    }
  };

  const filtered = sessions.filter(s => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (s.user_id || '').toLowerCase().includes(q) || (s.user_identifier || '').toLowerCase().includes(q);
  });

  return (
    <div style={{ minHeight: '100vh', background: T.bg, color: T.text, display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{ padding: '28px 32px 0', display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{ width: 40, height: 40, borderRadius: 10, background: 'rgba(16,185,129,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <MessageSquare size={20} style={{ color: T.success }} />
        </div>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Sessions</h1>
          <p style={{ fontSize: 13, color: T.muted, margin: 0 }}>Live and historical AI conversations</p>
        </div>
      </div>

      {error && (
        <div style={{ margin: '12px 32px', padding: '10px 14px', background: 'rgba(239,68,68,0.1)', border: `1px solid ${T.danger}`, borderRadius: 8, color: T.danger, fontSize: 13 }}>
          {error}
          <button onClick={() => setError('')} style={{ float: 'right', background: 'none', border: 'none', color: T.danger, cursor: 'pointer' }}><X size={14} /></button>
        </div>
      )}

      <div style={{ padding: '20px 32px', flex: 1 }}>
        {/* Stats */}
        <div style={{ display: 'flex', gap: 12, marginBottom: 24 }}>
          <StatCard label="Total Sessions" value={(stats.total ?? sessions.length).toLocaleString()} />
          <StatCard label="Active Now" value={stats.active ?? sessions.filter(s => s.status === 'active').length} color={T.success} />
          <StatCard label="Ended Today" value={stats.ended_today ?? 0} />
          <StatCard label="Avg Duration" value={formatDuration(stats.avg_duration)} />
        </div>

        {/* Filters + Search */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', border: `1px solid ${T.border}`, borderRadius: 8, overflow: 'hidden' }}>
            {FILTERS.map(f => (
              <button key={f} onClick={() => setFilterTab(f)}
                style={{ padding: '7px 14px', background: filterTab === f ? T.accent : 'transparent', color: filterTab === f ? '#fff' : T.muted, fontWeight: 600, fontSize: 12, border: 'none', cursor: 'pointer', borderRight: f !== 'Archived' ? `1px solid ${T.border}` : 'none' }}>
                {f}
              </button>
            ))}
          </div>
          <div style={{ position: 'relative', flex: 1, minWidth: 180 }}>
            <Search size={13} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: T.muted, pointerEvents: 'none' }} />
            <input value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="Search by user..."
              style={{ width: '100%', boxSizing: 'border-box', padding: '8px 10px 8px 30px', background: T.surface, border: `1px solid ${T.border}`, borderRadius: 8, color: T.text, fontSize: 13, outline: 'none' }} />
          </div>
        </div>

        {/* Main content: list + transcript */}
        <div style={{ display: 'flex', gap: 16, height: 'calc(100vh - 340px)', minHeight: 300 }}>
          {/* Session list */}
          <div style={{ flex: selectedSession ? '0 0 45%' : 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <div key={i} style={{ background: T.surface, borderRadius: 10, height: 72, opacity: 0.4, border: `1px solid ${T.border}` }} />
              ))
            ) : filtered.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '60px 0' }}>
                <MessageSquare size={40} style={{ color: T.muted, margin: '0 auto 12px', display: 'block' }} />
                <p style={{ fontSize: 14, color: T.muted }}>No sessions found.</p>
              </div>
            ) : (
              filtered.map(session => {
                const sc = statusConfig[session.status] || statusConfig.ended;
                const isSelected = selectedSession?.id === session.id;
                return (
                  <div key={session.id}
                    onClick={() => openSession(session)}
                    style={{ background: isSelected ? 'rgba(224,90,37,0.1)' : T.surface, borderRadius: 10, padding: '12px 14px', border: `1.5px solid ${isSelected ? T.accent : T.border}`, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 10, transition: 'border-color 0.15s' }}>
                    <div style={{ width: 34, height: 34, borderRadius: 8, background: `${channelColors[session.channel] || T.muted}20`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                      <User size={16} style={{ color: channelColors[session.channel] || T.muted }} />
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
                        <p style={{ fontSize: 13, fontWeight: 600, margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {session.user_identifier || session.user_id || 'Anonymous'}
                        </p>
                        <Badge color={channelColors[session.channel]}>{session.channel || 'web'}</Badge>
                        <Badge color={sc.color}>{sc.label}</Badge>
                      </div>
                      <p style={{ fontSize: 11, color: T.muted, margin: 0, display: 'flex', gap: 10 }}>
                        <span>{session.message_count ?? 0} msgs</span>
                        <span>{formatDuration(session.duration)}</span>
                        <span>{formatTime(session.started_at)}</span>
                      </p>
                    </div>
                    <ChevronRight size={14} style={{ color: T.muted, flexShrink: 0 }} />
                  </div>
                );
              })
            )}
          </div>

          {/* Transcript slide-out */}
          {selectedSession && (
            <div style={{ flex: 1, background: T.surface, borderRadius: 14, border: `1px solid ${T.border}`, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <div style={{ padding: '14px 16px', borderBottom: `1px solid ${T.border}`, display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ flex: 1 }}>
                  <p style={{ fontSize: 14, fontWeight: 700, margin: 0 }}>{selectedSession.user_identifier || selectedSession.user_id || 'Anonymous'}</p>
                  <p style={{ fontSize: 11, color: T.muted, margin: 0 }}>Started {formatTime(selectedSession.started_at)}</p>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  {selectedSession.status === 'active' && (
                    <>
                      <button onClick={() => handleArchive(selectedSession.id)} disabled={actioning === selectedSession.id + '_archive'}
                        style={{ padding: '6px 12px', borderRadius: 7, background: 'rgba(245,158,11,0.1)', border: `1px solid ${T.warn}`, color: T.warn, fontSize: 12, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
                        <Archive size={11} /> Archive
                      </button>
                      <button onClick={() => handleEnd(selectedSession.id)} disabled={actioning === selectedSession.id + '_end'}
                        style={{ padding: '6px 12px', borderRadius: 7, background: 'rgba(239,68,68,0.1)', border: `1px solid ${T.danger}`, color: T.danger, fontSize: 12, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
                        <StopCircle size={11} /> End
                      </button>
                    </>
                  )}
                  <button onClick={() => setSelectedSession(null)}
                    style={{ padding: '6px 8px', borderRadius: 7, background: 'transparent', border: `1px solid ${T.border}`, color: T.muted, cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
                    <X size={14} />
                  </button>
                </div>
              </div>
              <div style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
                {transcriptLoading ? (
                  <div style={{ textAlign: 'center', padding: '40px 0', color: T.muted, fontSize: 13 }}>Loading transcript...</div>
                ) : transcript.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '40px 0', color: T.muted, fontSize: 13 }}>No messages yet.</div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {transcript.map((msg, i) => {
                      const isUser = msg.role === 'user';
                      return (
                        <div key={i} style={{ display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start' }}>
                          <div style={{ maxWidth: '80%', padding: '10px 14px', borderRadius: isUser ? '12px 12px 2px 12px' : '12px 12px 12px 2px', background: isUser ? T.accent : 'rgba(255,255,255,0.06)', fontSize: 13, lineHeight: 1.5 }}>
                            <p style={{ margin: 0, color: isUser ? '#fff' : T.text }}>{msg.content || msg.text}</p>
                            {msg.created_at && (
                              <p style={{ fontSize: 10, margin: '4px 0 0', color: isUser ? 'rgba(255,255,255,0.6)' : T.muted }}>
                                {new Date(msg.created_at).toLocaleTimeString()}
                              </p>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
