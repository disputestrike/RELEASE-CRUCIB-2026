/**
 * CommandCenter — Voice + text + attachments + suggestions + history
 * Wired to CrucibAI real backend. White ChatGPT-style theme.
 */
import React, { useState, useRef, useEffect } from 'react';

const SUGGESTIONS = [
  'Build a SaaS dashboard with auth and PayPal',
  'Create a project management tool with team collaboration',
  'Build an e-commerce store with product catalog and checkout',
  'Create a CRM with lead pipeline and automation',
  'Build a mobile app with Expo and React Native',
  'Create an admin dashboard with analytics',
];

export default function CommandCenter({ onSubmit, isRunning = false, placeholder, toolCarousel }) {
  const [input, setInput] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [attachments, setAttachments] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const [recentPrompts, setRecentPrompts] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const recognitionRef = useRef(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    try {
      const saved = localStorage.getItem('crucibai_recent_prompts');
      if (saved) setRecentPrompts(JSON.parse(saved));
    } catch {}
  }, []);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px';
    }
  }, [input]);

  const toggleVoice = () => {
    const SpeechRecognition = window.webkitSpeechRecognition || window.SpeechRecognition;
    if (!SpeechRecognition) {
      alert('Voice input not supported in this browser. Try Chrome.');
      return;
    }
    if (isRecording) {
      recognitionRef.current?.stop();
      setIsRecording(false);
      return;
    }
    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;
    recognition.lang = 'en-US';
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.onresult = (e) => {
      const transcript = e.results[0][0].transcript;
      setInput(prev => prev + (prev ? ' ' : '') + transcript);
      setIsRecording(false);
    };
    recognition.onerror = () => setIsRecording(false);
    recognition.onend = () => setIsRecording(false);
    recognition.start();
    setIsRecording(true);
  };

  const handleFileAttach = (e) => {
    const files = Array.from(e.target.files || []);
    files.forEach(file => {
      const reader = new FileReader();
      reader.onload = (ev) => {
        setAttachments(prev => [...prev, {
          type: file.type.startsWith('image/') ? 'image' : 'text',
          content: ev.target?.result,
          filename: file.name,
        }]);
      };
      if (file.type.startsWith('image/')) reader.readAsDataURL(file);
      else reader.readAsText(file);
    });
    e.target.value = '';
  };

  const handleSubmit = () => {
    const trimmed = input.trim();
    if (!trimmed && attachments.length === 0) return;
    if (trimmed) {
      const updated = [trimmed, ...recentPrompts.filter(p => p !== trimmed)].slice(0, 10);
      setRecentPrompts(updated);
      try { localStorage.setItem('crucibai_recent_prompts', JSON.stringify(updated)); } catch {}
    }
    onSubmit({ text: trimmed, attachments });
    setInput('');
    setAttachments([]);
    setShowSuggestions(false);
    setShowHistory(false);
  };

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(); }
    if (e.key === 'Escape') { setShowSuggestions(false); setShowHistory(false); }
  };

  const defaultPlaceholder = isRunning
    ? "Tell CrucibAI the next change - e.g. add PayPal, dark mode, or stricter tests."
    : "Describe what you want to build…";

  return (
    <div style={{ borderTop:'1px solid #e5e7eb', background:'#fff', padding:'12px 16px 16px' }}>

      {toolCarousel}

      {/* Suggestions chips — show when focused and empty */}
      {showSuggestions && !input && !isRunning && (
        <div style={{ display:'flex', gap:6, flexWrap:'wrap', marginBottom:10 }}>
          {SUGGESTIONS.slice(0,4).map(s => (
            <button key={s} onClick={() => { setInput(s); setShowSuggestions(false); }}
              style={{ fontSize:11, padding:'4px 10px', background:'#f9fafb',
                border:'1px solid #e5e7eb', borderRadius:20, color:'#374151',
                cursor:'pointer', whiteSpace:'nowrap' }}>
              ✦ {s.slice(0, 40)}{s.length > 40 ? '…' : ''}
            </button>
          ))}
        </div>
      )}

      {/* Attachments */}
      {attachments.length > 0 && (
        <div style={{ display:'flex', gap:8, marginBottom:10, flexWrap:'wrap' }}>
          {attachments.map((att, i) => (
            <div key={i} style={{ display:'flex', alignItems:'center', gap:6,
              padding:'4px 10px', background:'#f3f4f6', borderRadius:20,
              fontSize:12, color:'#374151' }}>
              <span>{att.type === 'image' ? '🖼' : '📄'}</span>
              <span>{att.filename || 'file'}</span>
              <button onClick={() => setAttachments(prev => prev.filter((_,j) => j !== i))}
                style={{ background:'none', border:'none', color:'#9ca3af',
                  cursor:'pointer', fontSize:14, lineHeight:1 }}>×</button>
            </div>
          ))}
        </div>
      )}

      {/* Main input box */}
      <div style={{ background:'#f9fafb', border:'1px solid #e5e7eb', borderRadius:12,
        overflow:'hidden', boxShadow:'0 1px 3px rgba(0,0,0,0.06)' }}>
        <textarea
          ref={textareaRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          onFocus={() => setShowSuggestions(true)}
          placeholder={
            placeholder ||
            (isRunning
              ? defaultPlaceholder
              : "Describe the app, automation, or repair CrucibAI should build.")
          }
          rows={1}
          style={{ width:'100%', padding:'12px 16px 4px', border:'none', outline:'none',
            background:'transparent', fontSize:14, resize:'none', lineHeight:1.5,
            color:'#111827', fontFamily:'inherit', minHeight:44, maxHeight:200,
            boxSizing:'border-box' }} />

        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between',
          padding:'6px 10px 10px' }}>
          <div style={{ display:'flex', gap:4 }}>
            {/* Attach file */}
            <button onClick={() => fileInputRef.current?.click()}
              title="Attach file or screenshot"
              style={{ width:32, height:32, borderRadius:8, border:'none',
                background:'transparent', color:'#9ca3af', cursor:'pointer',
                display:'flex', alignItems:'center', justifyContent:'center', fontSize:16 }}>
              📎
            </button>
            <input ref={fileInputRef} type="file" accept="image/*,.txt,.js,.jsx,.ts,.tsx,.py,.json,.zip"
              multiple onChange={handleFileAttach} style={{ display:'none' }} />

            {/* Voice */}
            <button onClick={toggleVoice} title={isRecording ? 'Stop recording' : 'Voice input'}
              style={{ width:32, height:32, borderRadius:8, border:'none',
                background: isRecording ? '#fee2e2' : 'transparent',
                color: isRecording ? '#dc2626' : '#9ca3af',
                cursor:'pointer', display:'flex', alignItems:'center',
                justifyContent:'center', fontSize:16,
                animation: isRecording ? 'pulse 1s infinite' : 'none' }}>
              🎤
            </button>

            {/* History */}
            {recentPrompts.length > 0 && (
              <button onClick={() => setShowHistory(h => !h)} title="Recent prompts"
                style={{ width:32, height:32, borderRadius:8, border:'none',
                  background:'transparent', color:'#9ca3af', cursor:'pointer',
                  display:'flex', alignItems:'center', justifyContent:'center', fontSize:16 }}>
                🕐
              </button>
            )}
          </div>

          {/* Send */}
          <button onClick={handleSubmit}
            disabled={!input.trim() && attachments.length === 0}
            style={{ width:34, height:34, borderRadius:'50%',
              background: (input.trim() || attachments.length > 0) ? '#10b981' : '#e5e7eb',
              border:'none', cursor: (input.trim() || attachments.length > 0) ? 'pointer' : 'not-allowed',
              display:'flex', alignItems:'center', justifyContent:'center',
              color: (input.trim() || attachments.length > 0) ? '#fff' : '#9ca3af',
              fontSize:16, transition:'all 0.15s' }}>
            {isRunning ? '↗' : '↑'}
          </button>
        </div>
      </div>

      {/* History dropdown */}
      {showHistory && recentPrompts.length > 0 && (
        <div style={{ marginTop:8, background:'#fff', border:'1px solid #e5e7eb',
          borderRadius:8, overflow:'hidden', boxShadow:'0 4px 12px rgba(0,0,0,0.1)' }}>
          <div style={{ padding:'6px 12px', fontSize:11, color:'#9ca3af',
            fontWeight:600, textTransform:'uppercase', letterSpacing:'0.06em',
            borderBottom:'1px solid #f3f4f6' }}>
            Recent builds
          </div>
          {recentPrompts.map((p, i) => (
            <button key={i} onClick={() => { setInput(p); setShowHistory(false); }}
              style={{ width:'100%', textAlign:'left', padding:'8px 12px',
                background:'none', border:'none', fontSize:13, color:'#374151',
                cursor:'pointer', borderBottom: i < recentPrompts.length-1 ? '1px solid #f9fafb' : 'none',
                whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis' }}>
              {p}
            </button>
          ))}
        </div>
      )}

      <style>{`@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.5} }`}</style>
    </div>
  );
}
