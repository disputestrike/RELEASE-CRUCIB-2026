import { useState, useEffect } from 'react';
import {
  ShoppingBag, Plus, X, DollarSign, Package, ShoppingCart,
  TrendingUp, ExternalLink, CreditCard, Repeat
} from 'lucide-react';
import { useAuth, API } from '../App';
import axios from 'axios';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';

const T = {
  bg:      'var(--theme-bg)',
  surface: 'var(--theme-surface)',
  border:  'rgba(255,255,255,0.12)',
  text:    'var(--theme-text)',
  muted:   'var(--theme-muted)',
  accent:  '#E05A25',
  success: '#10b981',
  danger:  '#ef4444',
  info:    '#3b82f6',
  warn:    '#f59e0b',
  input:   'var(--theme-input, rgba(255,255,255,0.06))',
};

const CURRENCIES = ['USD', 'EUR', 'GBP'];
const PRODUCT_TYPES = ['one_time', 'subscription'];

const orderStatusColors = {
  paid: T.success, pending: T.warn, failed: T.danger, refunded: T.muted
};

const Badge = ({ children, color }) => (
  <span style={{ display: 'inline-block', padding: '2px 9px', borderRadius: 20, fontSize: 11, fontWeight: 600, background: `${color || T.muted}22`, color: color || T.muted }}>
    {children}
  </span>
);

const StatCard = ({ label, value, icon: Icon, color }) => (
  <div style={{ background: T.surface, borderRadius: 12, padding: '16px 20px', border: `1px solid ${T.border}`, flex: 1, minWidth: 0 }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
      <div style={{ width: 28, height: 28, borderRadius: 7, background: `${color || T.accent}22`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Icon size={14} style={{ color: color || T.accent }} />
      </div>
      <p style={{ fontSize: 11, fontWeight: 600, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.07em', margin: 0 }}>{label}</p>
    </div>
    <p style={{ fontSize: 22, fontWeight: 700, margin: 0, color: color || T.text }}>{value}</p>
  </div>
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

const mockRevenueData = [
  { date: 'Mar 29', revenue: 320 }, { date: 'Mar 30', revenue: 480 }, { date: 'Mar 31', revenue: 290 },
  { date: 'Apr 1', revenue: 640 }, { date: 'Apr 2', revenue: 520 }, { date: 'Apr 3', revenue: 780 },
  { date: 'Apr 4', revenue: 410 },
];

const emptyProduct = { name: '', description: '', price: '', currency: 'USD', type: 'one_time' };

export default function CommerceManagePage() {
  const { token } = useAuth();
  const headers = { Authorization: 'Bearer ' + token };

  const [activeTab, setActiveTab] = useState('products');
  const [products, setProducts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [stats, setStats] = useState({ revenue: 0, orders: 0, active_products: 0, mrr: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showNewProduct, setShowNewProduct] = useState(false);
  const [productForm, setProductForm] = useState(emptyProduct);
  const [saving, setSaving] = useState(false);
  const [creatingCheckout, setCreatingCheckout] = useState(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [prodRes, ordersRes, statsRes] = await Promise.allSettled([
        axios.get(`${API}/commerce/products`, { headers }),
        axios.get(`${API}/commerce/orders`, { headers }),
        axios.get(`${API}/commerce/stats`, { headers }),
      ]);
      if (prodRes.status === 'fulfilled') setProducts(prodRes.value.data?.products || prodRes.value.data || []);
      if (ordersRes.status === 'fulfilled') setOrders(ordersRes.value.data?.orders || ordersRes.value.data || []);
      if (statsRes.status === 'fulfilled') setStats(statsRes.value.data || {});
    } catch (e) {
      setError('Failed to load commerce data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const handleCreateProduct = async () => {
    if (!productForm.name.trim() || !productForm.price) return;
    setSaving(true);
    try {
      const res = await axios.post(`${API}/commerce/products`, {
        ...productForm, price: parseFloat(productForm.price)
      }, { headers });
      setProducts(prev => [...prev, res.data?.product || res.data]);
      setProductForm(emptyProduct);
      setShowNewProduct(false);
    } catch (e) {
      setError('Failed to create product.');
    } finally {
      setSaving(false);
    }
  };

  const handleCreateCheckout = async (productId) => {
    setCreatingCheckout(productId);
    try {
      const res = await axios.post(`${API}/commerce/checkout`, { product_id: productId }, { headers });
      const url = res.data?.url || res.data?.checkout_url;
      if (url) window.open(url, '_blank');
    } catch (e) {
      setError('Failed to create checkout.');
    } finally {
      setCreatingCheckout(null);
    }
  };

  const f = (key) => (e) => setProductForm(p => ({ ...p, [key]: e.target.value }));

  const formatCurrency = (amount, currency = 'USD') => {
    const sym = { USD: '$', EUR: '€', GBP: '£' }[currency] || '$';
    return `${sym}${(amount || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  return (
    <div style={{ minHeight: '100vh', background: T.bg, color: T.text }}>
      {/* Header */}
      <div style={{ padding: '28px 32px 0', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 40, height: 40, borderRadius: 10, background: 'rgba(16,185,129,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <ShoppingBag size={20} style={{ color: T.success }} />
          </div>
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Commerce</h1>
            <p style={{ fontSize: 13, color: T.muted, margin: 0 }}>Products, orders, and revenue</p>
          </div>
        </div>
        {activeTab === 'products' && (
          <button onClick={() => setShowNewProduct(v => !v)}
            style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '9px 18px', borderRadius: 10, background: T.accent, color: '#fff', fontWeight: 600, fontSize: 13, border: 'none', cursor: 'pointer' }}>
            <Plus size={15} /> New Product
          </button>
        )}
      </div>

      {error && (
        <div style={{ margin: '12px 32px', padding: '10px 14px', background: 'rgba(239,68,68,0.1)', border: `1px solid ${T.danger}`, borderRadius: 8, color: T.danger, fontSize: 13 }}>
          {error}
          <button onClick={() => setError('')} style={{ float: 'right', background: 'none', border: 'none', color: T.danger, cursor: 'pointer' }}><X size={14} /></button>
        </div>
      )}

      <div style={{ padding: '20px 32px' }}>
        {/* Stats */}
        <div style={{ display: 'flex', gap: 12, marginBottom: 24 }}>
          <StatCard label="Total Revenue" value={formatCurrency(stats.revenue)} icon={DollarSign} color={T.success} />
          <StatCard label="Total Orders" value={(stats.orders || orders.length).toLocaleString()} icon={ShoppingCart} color={T.info} />
          <StatCard label="Active Products" value={(stats.active_products || products.length).toLocaleString()} icon={Package} color={T.accent} />
          <StatCard label="MRR" value={formatCurrency(stats.mrr)} icon={Repeat} color={T.warn} />
        </div>

        {/* Revenue chart */}
        <div style={{ background: T.surface, borderRadius: 14, border: `1px solid ${T.border}`, padding: '20px 24px', marginBottom: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
            <TrendingUp size={16} style={{ color: T.success }} />
            <p style={{ fontSize: 13, fontWeight: 700, margin: 0 }}>Revenue (Last 7 Days)</p>
          </div>
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={mockRevenueData} margin={{ top: 0, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: T.muted }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: T.muted }} axisLine={false} tickLine={false} width={40} tickFormatter={v => `$${v}`} />
              <Tooltip contentStyle={{ background: '#1c1c1e', border: `1px solid ${T.border}`, borderRadius: 8, fontSize: 12 }} labelStyle={{ color: T.text }} />
              <Line type="monotone" dataKey="revenue" stroke={T.accent} strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', borderBottom: `1px solid ${T.border}`, marginBottom: 20, gap: 0 }}>
          {['products', 'orders'].map(tab => (
            <button key={tab} onClick={() => setActiveTab(tab)}
              style={{ padding: '8px 20px', background: 'transparent', border: 'none', fontWeight: 600, fontSize: 13, cursor: 'pointer', color: activeTab === tab ? T.accent : T.muted, borderBottom: `2px solid ${activeTab === tab ? T.accent : 'transparent'}`, textTransform: 'capitalize', transition: 'color 0.15s' }}>
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>

        {/* New product form */}
        {activeTab === 'products' && showNewProduct && (
          <div style={{ background: T.surface, borderRadius: 14, border: `1px solid ${T.border}`, padding: 24, marginBottom: 20 }}>
            <p style={{ fontSize: 15, fontWeight: 700, margin: '0 0 18px' }}>New Product</p>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
              <Fld label="Name *"><Inp value={productForm.name} onChange={f('name')} placeholder="e.g. Pro Plan" /></Fld>
              <Fld label="Price *"><Inp value={productForm.price} onChange={f('price')} type="number" placeholder="29.00" /></Fld>
              <Fld label="Currency"><Sel value={productForm.currency} onChange={f('currency')} options={CURRENCIES} /></Fld>
              <Fld label="Type"><Sel value={productForm.type} onChange={f('type')} options={PRODUCT_TYPES} /></Fld>
            </div>
            <Fld label="Description">
              <textarea value={productForm.description} onChange={f('description')} placeholder="What does this product include?" rows={2}
                style={{ width: '100%', boxSizing: 'border-box', padding: '9px 12px', background: T.input, border: `1.5px solid ${T.border}`, borderRadius: 8, color: T.text, fontSize: 13, outline: 'none', resize: 'none', fontFamily: 'inherit' }} />
            </Fld>
            <div style={{ display: 'flex', gap: 10 }}>
              <button onClick={() => setShowNewProduct(false)} style={{ padding: '9px 18px', borderRadius: 8, background: 'transparent', border: `1px solid ${T.border}`, color: T.muted, fontWeight: 600, fontSize: 13, cursor: 'pointer' }}>Cancel</button>
              <button onClick={handleCreateProduct} disabled={saving || !productForm.name.trim() || !productForm.price}
                style={{ padding: '9px 18px', borderRadius: 8, background: T.accent, color: '#fff', fontWeight: 600, fontSize: 13, border: 'none', cursor: 'pointer', opacity: (saving || !productForm.name.trim() || !productForm.price) ? 0.6 : 1 }}>
                {saving ? 'Creating...' : 'Create Product'}
              </button>
            </div>
          </div>
        )}

        {/* Products list */}
        {activeTab === 'products' && (
          loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {[1, 2, 3].map(i => <div key={i} style={{ background: T.surface, borderRadius: 10, height: 64, opacity: 0.4, border: `1px solid ${T.border}` }} />)}
            </div>
          ) : products.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px 0' }}>
              <Package size={40} style={{ color: T.muted, margin: '0 auto 12px', display: 'block' }} />
              <p style={{ fontSize: 14, color: T.muted }}>No products yet. Create your first product to start selling.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {products.map(product => (
                <div key={product.id} style={{ background: T.surface, borderRadius: 10, padding: '14px 16px', border: `1px solid ${T.border}`, display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{ width: 36, height: 36, borderRadius: 8, background: 'rgba(224,90,37,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                    <Package size={16} style={{ color: T.accent }} />
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <p style={{ fontSize: 14, fontWeight: 600, margin: 0 }}>{product.name}</p>
                      <Badge color={product.type === 'subscription' ? T.info : T.success}>
                        {product.type === 'subscription' ? <><Repeat size={10} style={{ marginRight: 2 }} />Sub</> : 'One-time'}
                      </Badge>
                    </div>
                    {product.description && <p style={{ fontSize: 12, color: T.muted, margin: '2px 0 0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{product.description}</p>}
                  </div>
                  <p style={{ fontSize: 16, fontWeight: 700, margin: 0, flexShrink: 0 }}>{formatCurrency(product.price, product.currency)}</p>
                  <button onClick={() => handleCreateCheckout(product.id)} disabled={creatingCheckout === product.id}
                    style={{ padding: '7px 14px', borderRadius: 8, background: T.accent, color: '#fff', fontWeight: 600, fontSize: 12, border: 'none', cursor: 'pointer', opacity: creatingCheckout === product.id ? 0.6 : 1, display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0 }}>
                    <CreditCard size={12} /> {creatingCheckout === product.id ? 'Opening...' : 'Checkout'}
                    <ExternalLink size={11} />
                  </button>
                </div>
              ))}
            </div>
          )
        )}

        {/* Orders list */}
        {activeTab === 'orders' && (
          loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {[1, 2, 3].map(i => <div key={i} style={{ background: T.surface, borderRadius: 10, height: 64, opacity: 0.4, border: `1px solid ${T.border}` }} />)}
            </div>
          ) : orders.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px 0' }}>
              <ShoppingCart size={40} style={{ color: T.muted, margin: '0 auto 12px', display: 'block' }} />
              <p style={{ fontSize: 14, color: T.muted }}>No orders yet.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {orders.map(order => (
                <div key={order.id} style={{ background: T.surface, borderRadius: 10, padding: '14px 16px', border: `1px solid ${T.border}`, display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <p style={{ fontSize: 13, fontWeight: 600, margin: 0, fontFamily: 'monospace' }}>#{order.id?.slice(-8) || order.order_id}</p>
                      <p style={{ fontSize: 13, color: T.muted, margin: 0 }}>{order.product_name || '—'}</p>
                      <Badge color={orderStatusColors[order.status]}>{order.status || 'pending'}</Badge>
                    </div>
                    <p style={{ fontSize: 11, color: T.muted, margin: '2px 0 0' }}>{order.created_at ? new Date(order.created_at).toLocaleDateString() : '—'}</p>
                  </div>
                  <p style={{ fontSize: 15, fontWeight: 700, margin: 0, flexShrink: 0 }}>{formatCurrency(order.amount, order.currency)}</p>
                </div>
              ))}
            </div>
          )
        )}
      </div>
    </div>
  );
}
