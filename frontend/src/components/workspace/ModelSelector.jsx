import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, Check, Sparkles, Zap, Coffee, RefreshCw } from 'lucide-react';

/** LLM dropdown — Cursor-style, opens upward in chat */
export default function ModelSelector({ selectedModel, onSelectModel, variant = 'default' }) {
  const [isOpen, setIsOpen] = useState(false);
  const isChat = variant === 'chat';

  const models = [
    { id: 'auto', name: 'Auto', icon: Sparkles, desc: 'Best model for the task' },
    { id: 'gpt-4o', name: 'GPT-4o', icon: Zap, desc: 'OpenAI latest' },
    { id: 'claude', name: 'Claude 3.5', icon: Coffee, desc: 'Anthropic Sonnet' },
    { id: 'gemini', name: 'Gemini Flash', icon: RefreshCw, desc: 'Google fast model' },
  ];

  const selected = models.find((m) => m.id === selectedModel) || models[0];

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        data-testid="model-selector"
        className={`flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white text-gray-800 hover:bg-gray-50 transition ${
          isChat ? 'h-[42px] px-3 py-2 text-sm' : 'px-3 py-1.5 text-sm'
        }`}
      >
        <selected.icon className="w-4 h-4 shrink-0" />
        <span className="truncate max-w-[100px]">{selected.name}</span>
        <ChevronDown className={`w-3.5 h-3.5 shrink-0 transition ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      <AnimatePresence>
        {isOpen && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} aria-hidden />
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 6 }}
              className="absolute left-0 bottom-full mb-1.5 w-56 bg-white border border-gray-200 rounded-lg shadow-xl overflow-hidden z-50"
            >
              <div className="py-1">
                {models.map((model) => (
                  <button
                    key={model.id}
                    type="button"
                    onClick={() => { onSelectModel(model.id); setIsOpen(false); }}
                    data-testid={`model-option-${model.id}`}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 text-left text-sm transition ${
                      selectedModel === model.id ? 'bg-gray-100 text-gray-900' : 'text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    <model.icon className="w-4 h-4 shrink-0" />
                    <div className="min-w-0 flex-1">
                      <div className="font-medium">{model.name}</div>
                      <div className="text-xs text-gray-500 truncate">{model.desc}</div>
                    </div>
                    {selectedModel === model.id && <Check className="w-4 h-4 shrink-0 text-[#1A1A1A]" />}
                  </button>
                ))}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
