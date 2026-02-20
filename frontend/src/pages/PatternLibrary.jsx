import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  Library, Search, Lock, CreditCard, Code, Database,
  Globe, Shield, Zap, Copy, Check, TrendingUp
} from 'lucide-react';
import { useAuth, API } from '../App';
import axios from 'axios';

const PatternLibrary = () => {
  const { token } = useAuth();
  const [patterns, setPatterns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [copiedId, setCopiedId] = useState(null);

  useEffect(() => {
    const fetchPatterns = async () => {
      try {
        const res = await axios.get(`${API}/patterns`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setPatterns(res.data.patterns);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchPatterns();
  }, [token]);

  const categories = [
    { id: 'all', name: 'All', icon: Library },
    { id: 'auth', name: 'Authentication', icon: Lock },
    { id: 'payments', name: 'Payments', icon: CreditCard },
    { id: 'backend', name: 'Backend', icon: Code },
    { id: 'frontend', name: 'Frontend', icon: Globe },
    { id: 'storage', name: 'Storage', icon: Database },
    { id: 'communications', name: 'Communications', icon: Zap },
    { id: 'realtime', name: 'Real-time', icon: TrendingUp }
  ];

  const getCategoryIcon = (category) => {
    const cat = categories.find(c => c.id === category);
    return cat?.icon || Library;
  };

  const filteredPatterns = patterns.filter(p => {
    const matchesSearch = p.name.toLowerCase().includes(search.toLowerCase());
    const matchesCategory = selectedCategory === 'all' || p.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const handleCopy = (id) => {
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-12 h-12 border-2 border-orange-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="space-y-8" data-testid="pattern-library">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold mb-2">Pattern Library</h1>
        <p className="text-[#666666]">Reusable patterns to accelerate your projects. Each pattern saves tokens and time.</p>
      </div>

      {/* Search & Filters */}
      <div className="flex flex-col md:flex-row gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-12 pr-4 py-3 bg-white/5 border border-white/10 rounded-lg focus:border-orange-500 outline-none transition"
            placeholder="Search patterns..."
            data-testid="pattern-search"
          />
        </div>
      </div>

      {/* Categories */}
      <div className="flex flex-wrap gap-2">
        {categories.map(cat => (
          <button
            key={cat.id}
            onClick={() => setSelectedCategory(cat.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition ${
              selectedCategory === cat.id
                ? 'bg-orange-500/20 text-orange-400 border border-orange-500/50'
                : 'bg-white/5 text-[#666666] border border-white/10 hover:border-white/20'
            }`}
            data-testid={`category-${cat.id}`}
          >
            <cat.icon className="w-4 h-4" />
            {cat.name}
          </button>
        ))}
      </div>

      {/* Stats */}
      <div className="grid md:grid-cols-3 gap-4">
        {[
          { label: 'Total Patterns', value: patterns.length, icon: Library },
          { label: 'Total Usage', value: patterns.reduce((acc, p) => acc + p.usage_count, 0).toLocaleString(), icon: TrendingUp },
          { label: 'Tokens Saved', value: `${(patterns.reduce((acc, p) => acc + p.tokens_saved * p.usage_count, 0) / 1000000).toFixed(1)}M`, icon: Zap }
        ].map((stat, i) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className="p-4 bg-[#0a0a0a] rounded-xl border border-white/10"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-orange-500/10 rounded-lg flex items-center justify-center">
                <stat.icon className="w-5 h-5 text-orange-400" />
              </div>
              <div>
                <p className="text-2xl font-bold">{stat.value}</p>
                <p className="text-sm text-gray-500">{stat.label}</p>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Patterns Grid */}
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredPatterns.map((pattern, i) => {
          const CategoryIcon = getCategoryIcon(pattern.category);
          return (
            <motion.div
              key={pattern.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="p-6 bg-[#0a0a0a] rounded-xl border border-white/10 hover:border-orange-500/30 transition-all group"
              data-testid={`pattern-${pattern.id}`}
            >
              <div className="flex items-start justify-between mb-4">
                <div className="w-12 h-12 bg-orange-500/10 rounded-lg flex items-center justify-center group-hover:bg-orange-500/20 transition">
                  <CategoryIcon className="w-6 h-6 text-orange-400" />
                </div>
                <button
                  onClick={() => handleCopy(pattern.id)}
                  className="p-2 hover:bg-white/10 rounded-lg transition"
                  title="Copy pattern ID"
                >
                  {copiedId === pattern.id ? (
                    <Check className="w-4 h-4 text-green-400" />
                  ) : (
                    <Copy className="w-4 h-4 text-gray-500" />
                  )}
                </button>
              </div>
              
              <h3 className="text-lg font-semibold mb-2">{pattern.name}</h3>
              <p className="text-sm text-gray-500 capitalize mb-4">{pattern.category}</p>
              
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-1 text-gray-500">
                  <TrendingUp className="w-4 h-4" />
                  {pattern.usage_count.toLocaleString()} uses
                </div>
                <div className="flex items-center gap-1 text-green-400">
                  <Zap className="w-4 h-4" />
                  Saves {(pattern.tokens_saved / 1000).toFixed(0)}K tokens
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>

      {filteredPatterns.length === 0 && (
        <div className="text-center py-12">
          <Library className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <p className="text-[#666666]">No patterns found matching your criteria.</p>
        </div>
      )}
    </div>
  );
};

export default PatternLibrary;