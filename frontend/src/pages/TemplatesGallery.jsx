import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout, FileCode, Loader2 } from 'lucide-react';
import { useAuth } from '../authContext';
import { API_BASE as API } from '../apiBase';
import axios from 'axios';
import { logApiError } from '../utils/apiError';
import './TemplatesGallery.css';

export default function TemplatesGallery() {
  const navigate = useNavigate();
  const { token } = useAuth();
  const [templates, setTemplates] = useState([]);
  const [creatingId, setCreatingId] = useState(null);

  useEffect(() => {
    axios.get(`${API}/templates`, token ? { headers: { Authorization: `Bearer ${token}` } } : {})
      .then((r) => setTemplates(r.data.templates || []))
      .catch((e) => { logApiError('TemplatesGallery', e); setTemplates([]); });
  }, [token]);

  const createFromTemplate = (templateId) => {
    if (!token) {
      navigate('/app/workspace');
      return;
    }
    setCreatingId(templateId);
    axios.post(`${API}/templates/${templateId}/remix`, {}, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => {
        const files = r.data.files || {};
        const query = new URLSearchParams({ prompt: r.data.prompt || (r.data.template_id && templates.find(t => t.id === r.data.template_id)?.prompt) || '' });
        navigate(`/app/workspace?${query.toString()}`, { state: { initialFiles: files } });
      })
      .catch((e) => { logApiError('TemplatesGallery from-template', e); setCreatingId(null); })
      .finally(() => setCreatingId(null));
  };

  return (
    <div className="templates-gallery">
      <h1 className="templates-gallery__title">Templates</h1>
      <p className="templates-gallery__subtitle">Start from a template to build faster.</p>
      <div className="templates-gallery__grid">
        {templates.length === 0 && (
          <p className="templates-gallery__empty" style={{ gridColumn: '1 / -1' }}>
            No templates loaded. Check your connection or try again later.
          </p>
        )}
        {templates.map((t) => (
          <div key={t.id} className="templates-gallery__card">
            <div className="templates-gallery__card-head">
              <div className="templates-gallery__icon-wrap" aria-hidden>
                <FileCode className="w-5 h-5" strokeWidth={2} />
              </div>
              <div>
                <h2 className="templates-gallery__name">{t.name}</h2>
                <p className="templates-gallery__desc">{t.description}</p>
                {Array.isArray(t.tags) && t.tags.length > 0 && (
                  <p className="templates-gallery__meta">
                    {t.tags.join(' · ')} · {t.difficulty || 'starter'}
                  </p>
                )}
              </div>
            </div>
            <button
              type="button"
              onClick={() => createFromTemplate(t.id)}
              disabled={creatingId !== null}
              className="templates-gallery__cta"
            >
              {creatingId === t.id ? <Loader2 className="w-4 h-4 animate-spin" aria-hidden /> : <Layout className="w-4 h-4" aria-hidden />}
              Use template
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
