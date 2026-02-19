/**
 * EverythingSupport.jsx
 * Comprehensive support for everything: code, docs, slides, sheets, exports
 * Not just code generation - full project support
 */

import React, { useState } from 'react';
import {
  FileCode, FileText, Presentation, Sheet3, Download, Github,
  Zap, CheckCircle, AlertCircle, Loader2, Copy, Eye
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';

/**
 * Everything Support Menu Component
 */
export const EverythingSupportMenu = ({ onSelect }) => {
  const options = [
    {
      id: 'code',
      name: 'Code',
      icon: FileCode,
      description: 'Generate full-stack code',
      color: 'from-blue-600 to-blue-700',
      examples: ['React components', 'API endpoints', 'Database schemas'],
    },
    {
      id: 'docs',
      name: 'Documentation',
      icon: FileText,
      description: 'Auto-generate docs',
      color: 'from-green-600 to-green-700',
      examples: ['README', 'API docs', 'User guides'],
    },
    {
      id: 'slides',
      name: 'Presentations',
      icon: Presentation,
      description: 'Create slide decks',
      color: 'from-purple-600 to-purple-700',
      examples: ['Pitch decks', 'Tutorials', 'Reports'],
    },
    {
      id: 'sheets',
      name: 'Spreadsheets',
      icon: Sheet3,
      description: 'Generate data sheets',
      color: 'from-orange-600 to-orange-700',
      examples: ['Data tables', 'Analytics', 'Reports'],
    },
    {
      id: 'export',
      name: 'Export',
      icon: Download,
      description: 'Export projects',
      color: 'from-pink-600 to-pink-700',
      examples: ['ZIP archive', 'GitHub repo', 'Deploy'],
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
      {options.map((option) => {
        const Icon = option.icon;
        return (
          <motion.button
            key={option.id}
            onClick={() => onSelect(option.id)}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className={`relative overflow-hidden p-6 rounded-lg bg-gradient-to-br ${option.color} text-[#1A1A1A] transition-all hover:shadow-lg`}
          >
            {/* Background glow */}
            <div className="absolute inset-0 opacity-0 hover:opacity-20 bg-white transition-opacity" />

            {/* Content */}
            <div className="relative space-y-3">
              <Icon size={32} className="mb-2" />
              <h3 className="font-bold text-lg">{option.name}</h3>
              <p className="text-sm opacity-90">{option.description}</p>

              {/* Examples */}
              <div className="space-y-1 pt-2 border-t border-white/20">
                {option.examples.map((example, idx) => (
                  <div key={idx} className="text-xs opacity-75">• {example}</div>
                ))}
              </div>
            </div>
          </motion.button>
        );
      })}
    </div>
  );
};

/**
 * Code Generation Options
 */
export const CodeGenerationOptions = ({ onGenerate, isLoading }) => {
  const [selectedStack, setSelectedStack] = useState('fullstack');

  const stacks = [
    { id: 'frontend', name: 'Frontend Only', techs: ['React', 'Vue', 'Svelte'] },
    { id: 'backend', name: 'Backend Only', techs: ['Node.js', 'Python', 'Go'] },
    { id: 'fullstack', name: 'Full Stack', techs: ['React + Node', 'Next.js', 'Django'] },
    { id: 'mobile', name: 'Mobile', techs: ['React Native', 'Flutter', 'Swift'] },
  ];

  return (
    <div className="space-y-4 p-6 bg-slate-800 border border-slate-700 rounded-lg">
      <h3 className="font-semibold text-[#1A1A1A] flex items-center gap-2">
        <FileCode size={20} />
        Code Generation
      </h3>

      <div className="grid grid-cols-2 gap-3">
        {stacks.map(stack => (
          <button
            key={stack.id}
            onClick={() => setSelectedStack(stack.id)}
            className={`p-4 rounded-lg border-2 transition-all ${
              selectedStack === stack.id
                ? 'border-blue-500 bg-blue-500/10 text-blue-300'
                : 'border-slate-600 bg-slate-700/50 text-slate-300 hover:border-slate-500'
            }`}
          >
            <div className="font-medium text-sm">{stack.name}</div>
            <div className="text-xs mt-2 space-y-1">
              {stack.techs.map((tech, idx) => (
                <div key={idx} className="opacity-75">{tech}</div>
              ))}
            </div>
          </button>
        ))}
      </div>

      <button
        onClick={() => onGenerate('code', selectedStack)}
        disabled={isLoading}
        className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-[#1A1A1A] font-medium py-3 rounded-lg transition-colors flex items-center justify-center gap-2"
      >
        {isLoading ? (
          <>
            <Loader2 size={18} className="animate-spin" />
            Generating...
          </>
        ) : (
          <>
            <Zap size={18} />
            Generate Code
          </>
        )}
      </button>
    </div>
  );
};

/**
 * Documentation Generator
 */
export const DocumentationGenerator = ({ onGenerate, isLoading }) => {
  const [docType, setDocType] = useState('readme');

  const docTypes = [
    { id: 'readme', name: 'README', icon: '📖' },
    { id: 'api', name: 'API Docs', icon: '🔌' },
    { id: 'guide', name: 'User Guide', icon: '📚' },
    { id: 'contributing', name: 'Contributing', icon: '🤝' },
  ];

  return (
    <div className="space-y-4 p-6 bg-slate-800 border border-slate-700 rounded-lg">
      <h3 className="font-semibold text-[#1A1A1A] flex items-center gap-2">
        <FileText size={20} />
        Documentation
      </h3>

      <div className="grid grid-cols-2 gap-3">
        {docTypes.map(doc => (
          <button
            key={doc.id}
            onClick={() => setDocType(doc.id)}
            className={`p-4 rounded-lg border-2 transition-all text-center ${
              docType === doc.id
                ? 'border-green-500 bg-green-500/10'
                : 'border-slate-600 bg-slate-700/50 hover:border-slate-500'
            }`}
          >
            <div className="text-2xl mb-2">{doc.icon}</div>
            <div className="font-medium text-sm">{doc.name}</div>
          </button>
        ))}
      </div>

      <button
        onClick={() => onGenerate('docs', docType)}
        disabled={isLoading}
        className="w-full bg-green-600 hover:bg-green-700 disabled:opacity-50 text-[#1A1A1A] font-medium py-3 rounded-lg transition-colors flex items-center justify-center gap-2"
      >
        {isLoading ? (
          <>
            <Loader2 size={18} className="animate-spin" />
            Generating...
          </>
        ) : (
          <>
            <Zap size={18} />
            Generate Docs
          </>
        )}
      </button>
    </div>
  );
};

/**
 * Presentation Generator
 */
export const PresentationGenerator = ({ onGenerate, isLoading }) => {
  const [slideCount, setSlideCount] = useState(10);

  const presets = [
    { name: 'Pitch Deck', slides: 15 },
    { name: 'Tutorial', slides: 20 },
    { name: 'Report', slides: 10 },
    { name: 'Training', slides: 25 },
  ];

  return (
    <div className="space-y-4 p-6 bg-slate-800 border border-slate-700 rounded-lg">
      <h3 className="font-semibold text-[#1A1A1A] flex items-center gap-2">
        <Presentation size={20} />
        Presentations
      </h3>

      <div className="space-y-3">
        <div>
          <label className="text-sm text-slate-400 mb-2 block">Number of Slides</label>
          <input
            type="range"
            min="5"
            max="50"
            value={slideCount}
            onChange={(e) => setSlideCount(parseInt(e.target.value))}
            className="w-full"
          />
          <div className="text-sm text-slate-300 mt-1">{slideCount} slides</div>
        </div>

        <div className="grid grid-cols-2 gap-2">
          {presets.map(preset => (
            <button
              key={preset.name}
              onClick={() => setSlideCount(preset.slides)}
              className="p-2 text-sm bg-slate-700 hover:bg-slate-600 rounded transition-colors text-slate-300"
            >
              {preset.name} ({preset.slides})
            </button>
          ))}
        </div>
      </div>

      <button
        onClick={() => onGenerate('slides', slideCount)}
        disabled={isLoading}
        className="w-full bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-[#1A1A1A] font-medium py-3 rounded-lg transition-colors flex items-center justify-center gap-2"
      >
        {isLoading ? (
          <>
            <Loader2 size={18} className="animate-spin" />
            Generating...
          </>
        ) : (
          <>
            <Zap size={18} />
            Generate Slides
          </>
        )}
      </button>
    </div>
  );
};

/**
 * Export Options
 */
export const ExportOptions = ({ onExport, isLoading }) => {
  const exports = [
    {
      id: 'zip',
      name: 'ZIP Archive',
      icon: Download,
      description: 'Download as ZIP file',
      color: 'bg-blue-600 hover:bg-blue-700',
    },
    {
      id: 'github',
      name: 'GitHub',
      icon: Github,
      description: 'Push to GitHub repo',
      color: 'bg-gray-700 hover:bg-gray-800',
    },
    {
      id: 'deploy',
      name: 'Deploy',
      icon: Zap,
      description: 'Deploy to production',
      color: 'bg-green-600 hover:bg-green-700',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {exports.map(exp => {
        const Icon = exp.icon;
        return (
          <button
            key={exp.id}
            onClick={() => onExport(exp.id)}
            disabled={isLoading}
            className={`p-6 rounded-lg text-[#1A1A1A] font-medium transition-all ${exp.color} disabled:opacity-50 flex flex-col items-center gap-3`}
          >
            <Icon size={32} />
            <div>
              <div className="font-semibold">{exp.name}</div>
              <div className="text-sm opacity-75">{exp.description}</div>
            </div>
          </button>
        );
      })}
    </div>
  );
};

/**
 * Generation Status Component
 */
export const GenerationStatus = ({ status, progress = 0, message = '' }) => {
  const statusConfig = {
    idle: { icon: null, color: 'text-slate-400', bg: 'bg-slate-800' },
    generating: { icon: Loader2, color: 'text-blue-400', bg: 'bg-blue-900/20' },
    success: { icon: CheckCircle, color: 'text-green-400', bg: 'bg-green-900/20' },
    error: { icon: AlertCircle, color: 'text-red-400', bg: 'bg-red-900/20' },
  };

  const config = statusConfig[status] || statusConfig.idle;
  const Icon = config.icon;

  if (status === 'idle') return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`p-4 rounded-lg border border-slate-700 ${config.bg}`}
    >
      <div className="flex items-center gap-3">
        {Icon && (
          <Icon
            size={20}
            className={`${config.color} ${status === 'generating' ? 'animate-spin' : ''}`}
          />
        )}
        <div className="flex-1">
          <div className={`font-medium ${config.color}`}>
            {status === 'generating' && 'Generating...'}
            {status === 'success' && 'Generation complete!'}
            {status === 'error' && 'Generation failed'}
          </div>
          {message && <div className="text-sm text-slate-400">{message}</div>}
        </div>
      </div>

      {status === 'generating' && (
        <div className="mt-3 w-full bg-slate-700 rounded-full h-2 overflow-hidden">
          <motion.div
            className="h-full bg-gradient-to-r from-blue-500 to-blue-600"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>
      )}
    </motion.div>
  );
};

export default {
  EverythingSupportMenu,
  CodeGenerationOptions,
  DocumentationGenerator,
  PresentationGenerator,
  ExportOptions,
  GenerationStatus,
};
