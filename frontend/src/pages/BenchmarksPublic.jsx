import { useEffect, useState } from 'react';

const SCORECARD_URL = '/public/benchmarks/scorecard';

const S = {
  page: { minHeight: '100vh', background: '#0d0e10', color: '#e0e0e0', fontFamily: 'system-ui, -apple-system, sans-serif', fontSize: '14px', padding: '0 0 48px' },
  header: { background: '#15161a', borderBottom: '1px solid #2a2b30', padding: '24px 32px 20px' },
  headerTitle: { margin: 0, fontSize: '22px', fontWeight: 700, color: '#e0e0e0' },
  headerSub: { marginTop: '6px', fontSize: '12px', color: '#888', fontFamily: 'monospace' },
  main: { padding: '32px', overflowX: 'auto' },
  table: { borderCollapse: 'collapse', width: '100%', minWidth: '640px', background: '#1e1f24', borderRadius: '8px', border: '1px solid #2a2b30' },
  th: { background: '#15161a', padding: '10px 16px', textAlign: 'center', fontSize: '12px', fontWeight: 700, color: '#6ab0f5', border: '1px solid #2a2b30', whiteSpace: 'nowrap' },
  thAxis: { background: '#15161a', padding: '10px 16px', textAlign: 'left', fontSize: '12px', fontWeight: 700, color: '#888', border: '1px solid #2a2b30' },
  tdCrucib: { padding: '9px 16px', textAlign: 'center', border: '1px solid #2a2b30', color: '#6ab0f5', fontWeight: 600, background: '#1a2840' },
  tdOther: { padding: '9px 16px', textAlign: 'center', border: '1px solid #2a2b30', color: '#c8c9d0', background: '#1e1f24' },
  tdAxis: { padding: '9px 16px', textAlign: 'left', border: '1px solid #2a2b30', color: '#888', fontFamily: 'monospace', fontSize: '12px', background: '#1a1b20' },
  note: { marginTop: '20px', fontSize: '12px', color: '#555', fontFamily: 'monospace' },
};

function fmtVal(val) {
  if (val === null || val === undefined) return '\u2014';
  if (typeof val === 'boolean') return val ? 'Yes' : 'No';
  if (Array.isArray(val)) return val.length > 0 ? val.join(', ') : '\u2014';
  return String(val);
}

export default function BenchmarksPublic() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetch(SCORECARD_URL)
      .then((r) => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then((d) => { if (!cancelled) setData(d); })
      .catch((e) => { if (!cancelled) setError(e.message); });
    return () => { cancelled = true; };
  }, []);

  if (error) return <div style={S.page}><div style={{ padding: '40px 32px', color: '#f5a623', fontFamily: 'monospace' }}>Failed to load scorecard: {error}</div></div>;
  if (!data) return <div style={S.page}><div style={{ padding: '40px 32px', color: '#888', fontFamily: 'monospace' }}>Loading scorecard...</div></div>;

  const { axes = [], competitors = [], scorecards = [], note } = data;

  return (
    <div style={S.page}>
      <div style={S.header}>
        <h1 style={S.headerTitle}>CrucibAI — Competitor Scorecard</h1>
        <div style={S.headerSub}>Independently reproducible — seed and raw data in proof/benchmarks/</div>
      </div>
      <div style={S.main}>
        <table style={S.table}>
          <thead>
            <tr>
              <th style={S.thAxis}>Axis</th>
              {competitors.map((c) => (
                <th key={c.id} style={c.id === 'crucibai' ? { ...S.th, color: '#6ab0f5' } : S.th}>{c.name}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {scorecards.map((row) => (
              <tr key={row.axis}>
                <td style={S.tdAxis}>{row.axis}</td>
                {competitors.map((c) => (
                  <td key={c.id} style={c.id === 'crucibai' ? S.tdCrucib : S.tdOther}>{fmtVal(row.values && row.values[c.id])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {note && <div style={S.note}>{note}</div>}
      </div>
    </div>
  );
}
