import { useState, useEffect } from 'react';
import {
  BookOpen, Plus, Trash2, X, Search, Upload, Link as LinkIcon,
  FileText, ChevronDown, ChevronRight, CheckCircle, Clock, AlertCircle
} from 'lucide-react';
import { useAuth } from '../App';
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
  input:   'var(--theme-input, rgba(255,255,255,0.06))',
};

const DOC_TYPES = ['FAQ', 'Policy', 'Product Info', 'Custom'];

const statusConfig = {
  indexed: { icon: CheckCircle, color: '#10b981', label: 'Indexed' },
  pending: { icon: Clock, color: '#737373', label: 'Pending' },
  error:   { icon: AlertCircle, color: '#ef4444', label: 'Error' },
};

const Badge = ({ children, color }) => (
  <span style={{ display: 'inline-block', padding: '2px 10px', borderRadius: 20, fontSize: 11, fontWeight: 600, background: color || 'rgba(255,255,255,0.08)', color: T.text }}>
    {children}
  </span>
);

const Inp = ({ value, onChange, placeholder, type = 'text' }) => (
  <input type={type} value={value} onChange={onChange} placeholder={placeholder}
    style={{ width: '100%', boxSizing: 'border-box', padding: '9px 12px', background: T.input, border: `1.5px solid ${T.border}`, borderRadius: 8, color: T.text, fontSize: 13, outline: 'none' }} />
);

const Sel = ({ value, onChange, options }) => (
  <select value={value} onChange={onChange}
    style={{ width: '100%', boxSizing: 'border-box', padding: '9px 12px', background: T.input, border: `1.5px solid ${T.border}`, borderRadius: 8, color: T.text, fontSize: 13, outline: 'none', cursor: 'pointer' }}>
    {options.map(o => <option key={o} value={o}>{o}</option>)}
  </select>
);

const Fld = ({ label, children }) => (
  <div style={{ marginBottom: 14 }}>
    <p style={{ fontSize: 11, fontWeight: 600, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 6 }}>{label}</p>
    {children}
  </div>
);

export default function KnowledgePage() {
  const { token } = useAuth();
  const headers = { Authorization: 'Bearer ' + token };

  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [uploadMode, setUploadMode] = useState('document'); // 'document' | 'url'
  const [showForm, setShowForm] = useState(false);
  const [docForm, setDocForm] = useState({ title: '', content: '', type: 'FAQ' });
  const [urlForm, setUrlForm] = useState({ url: '', title: '' });
  const [saving, setSaving] = useState(false);
  const [expandedId, setExpandedId] = useState(null);
  const [chunks, setChunks] = useState({});
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [searching, setSearching] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(null);

  const fetchSources = async () => {
    try {
      setLoading(true);
      const res = await axios.get(`${API}/knowledge/sources`, { headers });
      setSources(res.data?.sources || res.data || []);
    } catch (e) {
      setError('Failed to load knowledge sources.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchSources(); }, []);

  const handleDocSubmit = async () => {
    if (!docForm.title.trim() || !docForm.content.trim()) return;
    setSaving(true);
    try {
      await axios.post(`${API}/knowledge/ingest`, { ...docForm, source_type: 'document' }, { headers });
      setDocForm({ title: '', content: '', type: 'FAQ' });
      setShowForm(false);
      fetchSources();
    } catch (e) {
      setError('Failed to upload document.');
    } finally {
      setSaving(false);
    }
  };

  const handleUrlSubmit = async () => {
    if (!urlForm.url.trim()) return;
    setSaving(true);
    try {
      await axios.post(`${API}/knowledge/ingest`, { ...urlForm, source_type: 'url' }, { headers });
      setUrlForm({ url: '', title: '' });
      setShowForm(false);
      fetchSources();
    } catch (e) {
      setError('Failed to add URL.');
    } finally {
      setSaving(false);
    }
  };

  const handleExpand = async (id) => {
    if (expandedId === id) { setExpandedId(null); return; }
    setExpandedId(id);
    if (!chunks[id]) {
      try {
        const res = await axios.get(`${API}/knowledge/sources/${id}/chunks`, { headers });
        setChunks(prev => ({ ...prev, [id]: res.data?.chunks || [] }));
      } catch (e) {
        setChunks(prev => ({ ...prev, [id]: [] }));
      }
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const res = await axios.post(`${API}/knowledge/search`, { query: searchQuery }, { headers });
      setSearchResults(res.data?.results || []);
    } catch (e) {
      setError('Search failed.');
    } finally {
      setSearching(false);
    }
  };

  const handleDelete = async (id) => {
    try {
      await axios.delete(`${API}/knowledge/sources/${id}`, { headers });
      setSources(prev => prev.filter(s => s.id !== id));
      setDeleteConfirm(null);
    } catch (e) {
      setError('Failed to delete source.');
    }
  };

  const typeColors = { FAQ: '#404040', Policy: '#525252', 'Product Info': '#737373', Custom: '#A3A3A3', url: '#1A1A1A' };

  return (
    <div style={{ minHeight: '100vh', background: T.bg, color: T.text }}>
      {/* Header */}
      <div style={{ padding: '28px 32px 0', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 40, height: 40, borderRadius: 10, background: 'rgba(59,130,246,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <BookOpen size={20} style={{ color: '#3b82f6' }} />
          </div>
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Knowledge Base</h1>
            <p style={{ fontSize: 13, color: T.muted, margin: 0 }}>Manage RAG documents for your AI</p>
          </div>
        </div>
        <button
          onClick={() => setShowForm(v => !v)}
          style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '9px 18px', borderRadius: 10, background: T.accent, color: '#fff', fontWeight: 600, fontSize: 13, border: 'none', cursor: 'pointer' }}
        >
          <Plus size={15} /> Add Knowledge
        </button>
      </div>

      {error && (
        <div style={{ margin: '16px 32px', padding: '10px 14px', background: 'rgba(239,68,68,0.1)', border: `1px solid ${T.danger}`, borderRadius: 8, color: T.danger, fontSize: 13 }}>
          {error}
          <button onClick={() => setError('')} style={{ float: 'right', background: 'none', border: 'none', color: T.danger, cursor: 'pointer' }}><X size={14} /></button>
        </div>
      )}

      <div style={{ padding: '24px 32px' }}>
        {/* Add Form */}
        {showForm && (
          <div style={{ background: T.surface, borderRadius: 14, border: `1px solid ${T.border}`, padding: 24, marginBottom: 24 }}>
            <div style={{ display: 'flex', gap: 0, marginBottom: 20, border: `1px solid ${T.border}`, borderRadius: 8, overflow: 'hidden' }}>
              {[{ id: 'document', label: 'Upload Document', icon: Upload }, { id: 'url', label: 'Add URL', icon: LinkIcon }].map(({ id, label, icon: Icon }) => (
                <button key={id} onClick={() => setUploadMode(id)}
                  style={{ flex: 1, padding: '9px 0', background: uploadMode === id ? T.accent : 'transparent', color: uploadMode === id ? '#fff' : T.muted, fontWeight: 600, fontSize: 13, border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                  <Icon size={14} /> {label}
                </button>
              ))}
            </div>
            {uploadMode === 'document' ? (
              <>
                <Fld label="Title *"><Inp value={docForm.title} onChange={e => setDocForm(p => ({ ...p, title: e.target.value }))} placeholder="e.g. Product FAQ v1" /></Fld>
                <Fld label="Type"><Sel value={docForm.type} onChange={e => setDocForm(p => ({ ...p, type: e.target.value }))} options={DOC_TYPES} /></Fld>
                <Fld label="Content *">
                  <textarea value={docForm.content} onChange={e => setDocForm(p => ({ ...p, content: e.target.value }))} placeholder="Paste your document content here..." rows={6}
                    style={{ width: '100%', boxSizing: 'border-box', padding: '9px 12px', background: T.input, border: `1.5px solid ${T.border}`, borderRadius: 8, color: T.text, fontSize: 13, outline: 'none', resize: 'vertical', fontFamily: 'inherit', lineHeight: 1.5 }} />
                </Fld>
                <div style={{ display: 'flex', gap: 10 }}>
                  <button onClick={() => setShowForm(false)} style={{ padding: '9px 18px', borderRadius: 8, background: 'transparent', border: `1px solid ${T.border}`, color: T.muted, fontWeight: 600, fontSize: 13, cursor: 'pointer' }}>Cancel</button>
                  <button onClick={handleDocSubmit} disabled={saving || !docForm.title.trim() || !docForm.content.trim()}
                    style={{ padding: '9px 18px', borderRadius: 8, background: T.accent, color: '#fff', fontWeight: 600, fontSize: 13, border: 'none', cursor: 'pointer', opacity: (saving || !docForm.title.trim() || !docForm.content.trim()) ? 0.6 : 1 }}>
                    {saving ? 'Uploading...' : 'Upload Document'}
                  </button>
                </div>
              </>
            ) : (
              <>
                <Fld label="URL *"><Inp value={urlForm.url} onChange={e => setUrlForm(p => ({ ...p, url: e.target.value }))} placeholder="https://example.com/docs/faq" /></Fld>
                <Fld label="Title"><Inp value={urlForm.title} onChange={e => setUrlForm(p => ({ ...p, title: e.target.value }))} placeholder="Optional display name" /></Fld>
                <div style={{ display: 'flex', gap: 10 }}>
                  <button onClick={() => setShowForm(false)} style={{ padding: '9px 18px', borderRadius: 8, background: 'transparent', border: `1px solid ${T.border}`, color: T.muted, fontWeight: 600, fontSize: 13, cursor: 'pointer' }}>Cancel</button>
                  <button onClick={handleUrlSubmit} disabled={saving || !urlForm.url.trim()}
                    style={{ padding: '9px 18px', borderRadius: 8, background: T.accent, color: '#fff', fontWeight: 600, fontSize: 13, border: 'none', cursor: 'pointer', opacity: (saving || !urlForm.url.trim()) ? 0.6 : 1 }}>
                    {saving ? 'Adding...' : 'Add URL'}
                  </button>
                </div>
              </>
            )}
          </div>
        )}

        {/* Search */}
        <div style={{ display: 'flex', gap: 10, marginBottom: 24 }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: T.muted, pointerEvents: 'none' }} />
            <input value={searchQuery} onChange={e => setSearchQuery(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleSearch()} placeholder="Search knowledge base..."
              style={{ width: '100%', boxSizing: 'border-box', padding: '9px 12px 9px 34px', background: T.surface, border: `1.5px solid ${T.border}`, borderRadius: 8, color: T.text, fontSize: 13, outline: 'none' }} />
          </div>
          <button onClick={handleSearch} disabled={searching || !searchQuery.trim()}
            style={{ padding: '9px 18px', borderRadius: 8, background: T.surface, border: `1px solid ${T.border}`, color: T.text, fontWeight: 600, fontSize: 13, cursor: 'pointer', opacity: (searching || !searchQuery.trim()) ? 0.6 : 1 }}>
            {searching ? 'Searching...' : 'Search'}
          </button>
          {searchResults && (
            <button onClick={() => { setSearchResults(null); setSearchQuery(''); }}
              style={{ padding: '9px 12px', borderRadius: 8, background: 'transparent', border: `1px solid ${T.border}`, color: T.muted, cursor: 'pointer' }}>
              <X size={14} />
            </button>
          )}
        </div>

        {/* Search Results */}
        {searchResults && (
          <div style={{ marginBottom: 24 }}>
            <p style={{ fontSize: 13, fontWeight: 600, color: T.muted, marginBottom: 12 }}>Search Results ({searchResults.length})</p>
            {searchResults.length === 0 ? (
              <div style={{ padding: '20px', textAlign: 'center', color: T.muted, fontSize: 13 }}>No results found.</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {searchResults.map((r, i) => (
                  <div key={i} style={{ background: T.surface, borderRadius: 10, padding: 14, border: `1px solid ${T.border}` }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                      <p style={{ fontSize: 13, fontWeight: 600, margin: 0 }}>{r.title || r.source_title || 'Result'}</p>
                      {r.score && <span style={{ fontSize: 11, color: T.muted }}>Score: {(r.score * 100).toFixed(0)}%</span>}
                    </div>
                    <p style={{ fontSize: 12, color: T.muted, margin: 0, lineHeight: 1.5 }}>{r.content || r.text || ''}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Sources List */}
        {loading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {[1, 2, 3].map(i => <div key={i} style={{ background: T.surface, borderRadius: 12, height: 64, opacity: 0.4, border: `1px solid ${T.border}` }} />)}
          </div>
        ) : sources.length === 0 && !showForm ? (
          <div style={{ textAlign: 'center', padding: '80px 0' }}>
            <BookOpen size={48} style={{ color: T.muted, margin: '0 auto 16px', display: 'block' }} />
            <p style={{ fontSize: 16, fontWeight: 600, color: T.muted, marginBottom: 8 }}>No knowledge sources yet</p>
            <p style={{ fontSize: 13, color: T.muted, marginBottom: 20 }}>Add documents or URLs to power your AI with relevant context.</p>
            <button onClick={() => setShowForm(true)} style={{ padding: '10px 20px', borderRadius: 10, background: T.accent, color: '#fff', fontWeight: 600, fontSize: 13, border: 'none', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              <Plus size={14} /> Add Knowledge
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {sources.map(source => {
              const status = statusConfig[source.status] || statusConfig.pending;
              const StatusIcon = status.icon;
              const isExpanded = expandedId === source.id;
              const sourceChunks = chunks[source.id] || [];
              return (
                <div key={source.id} style={{ background: T.surface, borderRadius: 12, border: `1px solid ${T.border}`, overflow: 'hidden' }}>
                  <div style={{ padding: '14px 16px', display: 'flex', alignItems: 'center', gap: 12 }}>
                    <FileText size={16} style={{ color: typeColors[source.type] || T.muted, flexShrink: 0 }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                        <p style={{ fontSize: 14, fontWeight: 600, margin: 0 }}>{source.title}</p>
                        <Badge color={`${typeColors[source.type] || T.muted}22`}>{source.type || 'Document'}</Badge>
                        <span style={{ display: 'flex', alignItems: 'center', gap: 3, fontSize: 11, color: status.color }}>
                          <StatusIcon size={11} /> {status.label}
                        </span>
                      </div>
                      <p style={{ fontSize: 11, color: T.muted, margin: '2px 0 0' }}>
                        {source.document_count || source.chunk_count || 0} chunks · {source.created_at ? new Date(source.created_at).toLocaleDateString() : 'Recently added'}
                      </p>
                    </div>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexShrink: 0 }}>
                      <button onClick={() => handleExpand(source.id)}
                        style={{ padding: '5px 10px', borderRadius: 6, background: 'rgba(255,255,255,0.06)', border: `1px solid ${T.border}`, color: T.muted, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontSize: 12 }}>
                        {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />} Preview
                      </button>
                      <button onClick={() => setDeleteConfirm(source.id)}
                        style={{ padding: '5px 8px', borderRadius: 6, background: 'rgba(239,68,68,0.08)', border: `1px solid rgba(239,68,68,0.2)`, color: T.danger, cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </div>
                  {isExpanded && (
                    <div style={{ borderTop: `1px solid ${T.border}`, padding: '12px 16px', background: 'rgba(0,0,0,0.2)' }}>
                      {sourceChunks.length === 0 ? (
                        <p style={{ fontSize: 12, color: T.muted, margin: 0 }}>No chunks available for preview.</p>
                      ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                          {sourceChunks.slice(0, 5).map((chunk, i) => (
                            <div key={i} style={{ padding: '8px 10px', background: T.input, borderRadius: 6, fontSize: 12, color: T.muted, lineHeight: 1.5 }}>
                              <span style={{ color: T.accent, fontWeight: 600, marginRight: 6 }}>#{i + 1}</span>
                              {chunk.content || chunk.text || JSON.stringify(chunk)}
                            </div>
                          ))}
                          {sourceChunks.length > 5 && (
                            <p style={{ fontSize: 11, color: T.muted, margin: 0 }}>+{sourceChunks.length - 5} more chunks</p>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Delete confirmation */}
      {deleteConfirm && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 60, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.6)' }}>
          <div style={{ background: T.surface, borderRadius: 16, padding: 28, width: 360, border: `1px solid ${T.border}` }}>
            <p style={{ fontSize: 16, fontWeight: 700, margin: '0 0 8px' }}>Delete Knowledge Source?</p>
            <p style={{ fontSize: 13, color: T.muted, margin: '0 0 20px' }}>All chunks and embeddings will be removed. This cannot be undone.</p>
            <div style={{ display: 'flex', gap: 10 }}>
              <button onClick={() => setDeleteConfirm(null)} style={{ flex: 1, padding: '9px 0', borderRadius: 8, background: 'transparent', border: `1px solid ${T.border}`, color: T.muted, fontWeight: 600, fontSize: 13, cursor: 'pointer' }}>Cancel</button>
              <button onClick={() => handleDelete(deleteConfirm)} style={{ flex: 1, padding: '9px 0', borderRadius: 8, background: T.danger, color: '#fff', fontWeight: 600, fontSize: 13, border: 'none', cursor: 'pointer' }}>Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
