/**
 * AdvancedIDEUX.jsx
 * Advanced IDE UX features for CrucibAI
 * Includes: Command Palette, Minimap, AI Autocomplete, Inline Errors, Breadcrumb Navigation
 */

import React, { useState, useEffect, useRef } from 'react';
import { Command, Search, ChevronRight, AlertCircle, Lightbulb, Zap } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

/**
 * Command Palette Component
 * Cmd+K to open, search for commands
 */
export const CommandPalette = ({ commands = [], onCommandSelect }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef(null);

  // Keyboard shortcut
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen(!isOpen);
        setSearch('');
        setSelectedIndex(0);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  const filteredCommands = commands.filter(cmd =>
    cmd.name.toLowerCase().includes(search.toLowerCase()) ||
    cmd.description.toLowerCase().includes(search.toLowerCase())
  );

  const handleSelect = (command) => {
    onCommandSelect(command);
    setIsOpen(false);
    setSearch('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(Math.min(selectedIndex + 1, filteredCommands.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(Math.max(selectedIndex - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filteredCommands[selectedIndex]) {
        handleSelect(filteredCommands[selectedIndex]);
      }
    } else if (e.key === 'Escape') {
      setIsOpen(false);
    }
  };

  return (
    <>
      {/* Command Palette Trigger */}
      <button
        onClick={() => setIsOpen(true)}
        className="flex items-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-gray-200 bg-gray-800/50 hover:bg-gray-800 rounded-lg transition-colors"
        title="Cmd+K"
      >
        <Search size={16} />
        <span className="hidden sm:inline">Search commands...</span>
        <kbd className="hidden sm:inline ml-auto text-xs px-2 py-1 bg-gray-700 rounded">⌘K</kbd>
      </button>

      {/* Command Palette Modal */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-gray-900/50 z-50 flex items-start justify-center pt-20"
            onClick={() => setIsOpen(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="w-full max-w-2xl bg-gray-900 border border-gray-700 rounded-lg shadow-xl"
              onClick={e => e.stopPropagation()}
            >
              {/* Search Input */}
              <div className="border-b border-gray-700 p-4">
                <input
                  ref={inputRef}
                  type="text"
                  placeholder="Search commands..."
                  value={search}
                  onChange={e => {
                    setSearch(e.target.value);
                    setSelectedIndex(0);
                  }}
                  onKeyDown={handleKeyDown}
                  className="w-full bg-transparent text-[#1A1A1A] placeholder-slate-500 outline-none text-lg"
                />
              </div>

              {/* Commands List */}
              <div className="max-h-96 overflow-y-auto">
                {filteredCommands.length > 0 ? (
                  filteredCommands.map((command, idx) => (
                    <button
                      key={command.id}
                      onClick={() => handleSelect(command)}
                      className={`w-full px-4 py-3 text-left flex items-center justify-between transition-colors ${
                        idx === selectedIndex
                          ? 'bg-black text-[#1A1A1A]'
                          : 'hover:bg-gray-800 text-gray-300'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        {command.icon && <span>{command.icon}</span>}
                        <div>
                          <div className="font-medium">{command.name}</div>
                          <div className="text-xs opacity-70">{command.description}</div>
                        </div>
                      </div>
                      {command.shortcut && (
                        <kbd className="text-xs px-2 py-1 bg-gray-700 rounded opacity-50">
                          {command.shortcut}
                        </kbd>
                      )}
                    </button>
                  ))
                ) : (
                  <div className="px-4 py-8 text-center text-gray-400">
                    No commands found
                  </div>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};

/**
 * Breadcrumb Navigation Component
 */
export const BreadcrumbNav = ({ path = [] }) => {
  return (
    <div className="flex items-center gap-1 text-sm text-gray-400 px-4 py-2 border-b border-gray-700">
      {path.map((item, idx) => (
        <React.Fragment key={idx}>
          {idx > 0 && <ChevronRight size={16} className="text-gray-600" />}
          <button className="hover:text-gray-200 transition-colors">
            {item}
          </button>
        </React.Fragment>
      ))}
    </div>
  );
};

/**
 * Minimap Component
 * Shows overview of code file
 */
export const Minimap = ({ content = '', currentScroll = 0, totalHeight = 100 }) => {
  const lines = content.split('\n').slice(0, 50); // Show first 50 lines
  const scrollPercent = (currentScroll / totalHeight) * 100;

  return (
    <div className="w-12 bg-gray-900 border-l border-gray-700 overflow-hidden relative group">
      {/* Code preview */}
      <div className="text-xs text-gray-600 font-mono p-1 space-y-0.5">
        {lines.map((line, idx) => (
          <div key={idx} className="h-1 bg-gray-700/30 rounded opacity-50 group-hover:opacity-100 transition-opacity">
            {line.substring(0, 8)}
          </div>
        ))}
      </div>

      {/* Scroll indicator */}
      <div
        className="absolute left-0 right-0 h-8 bg-gray-200/20 border-y border-gray-300 transition-all"
        style={{ top: `${scrollPercent}%` }}
      />
    </div>
  );
};

/**
 * AI Autocomplete Component
 */
export const AIAutocomplete = ({ suggestions = [], onSelect, visible = false }) => {
  const [selectedIdx, setSelectedIdx] = useState(0);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (!visible) return;

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIdx(Math.min(selectedIdx + 1, suggestions.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIdx(Math.max(selectedIdx - 1, 0));
      } else if (e.key === 'Tab' || e.key === 'Enter') {
        e.preventDefault();
        if (suggestions[selectedIdx]) {
          onSelect(suggestions[selectedIdx]);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [visible, selectedIdx, suggestions, onSelect]);

  if (!visible || suggestions.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      className="absolute bg-gray-800 border border-gray-700 rounded-lg shadow-lg z-40 max-w-sm"
    >
      {suggestions.map((suggestion, idx) => (
        <button
          key={idx}
          onClick={() => onSelect(suggestion)}
          className={`w-full px-4 py-2 text-left text-sm transition-colors flex items-center gap-2 ${
            idx === selectedIdx
              ? 'bg-black text-[#1A1A1A]'
              : 'hover:bg-gray-700 text-gray-300'
          }`}
        >
          <Lightbulb size={14} />
          <div>
            <div className="font-medium">{suggestion.label}</div>
            <div className="text-xs opacity-70">{suggestion.description}</div>
          </div>
        </button>
      ))}
    </motion.div>
  );
};

/**
 * Inline Errors Component
 */
export const InlineErrors = ({ errors = [] }) => {
  if (errors.length === 0) return null;

  return (
    <div className="space-y-2 p-4 bg-gray-900/20 border border-gray-700/50 rounded-lg">
      {errors.map((error, idx) => (
        <div key={idx} className="flex items-start gap-3 text-sm">
          <AlertCircle size={16} className="text-gray-500 flex-shrink-0 mt-0.5" />
          <div>
            <div className="font-medium text-gray-400">{error.message}</div>
            <div className="text-xs text-gray-300/70">Line {error.line}: {error.code}</div>
          </div>
        </div>
      ))}
    </div>
  );
};

/**
 * AI Suggestions Component
 */
export const AISuggestions = ({ suggestions = [] }) => {
  if (suggestions.length === 0) return null;

  return (
    <div className="space-y-2 p-4 bg-black/20 border border-#000000/50 rounded-lg">
      {suggestions.map((suggestion, idx) => (
        <div key={idx} className="flex items-start gap-3 text-sm">
          <Zap size={16} className="text-[#1A1A1A] flex-shrink-0 mt-0.5" />
          <div>
            <div className="font-medium text-#d0d0d0">{suggestion.title}</div>
            <div className="text-xs text-#d0d0d0/70">{suggestion.description}</div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default {
  CommandPalette,
  BreadcrumbNav,
  Minimap,
  AIAutocomplete,
  InlineErrors,
  AISuggestions,
};
