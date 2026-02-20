/**
 * VibeCoding.jsx
 * Manus-style vibe coding for natural language development
 * Supports: voice input, natural language prompts, vibe analysis, style suggestions
 */

import React, { useState, useRef, useEffect } from 'react';
import { Mic, MicOff, Sparkles, Zap, Palette, Volume2, Send, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';

/**
 * Vibe Coding Input Component
 */
export const VibeCodingInput = ({ onSubmit, isLoading = false, API }) => {
  const [input, setInput] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [vibeAnalysis, setVibeAnalysis] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);

  /**
   * Start voice recording
   */
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        chunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        await transcribeAudio(blob);
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (error) {
      console.error('Failed to start recording:', error);
    }
  };

  /**
   * Stop voice recording
   */
  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  /**
   * Transcribe audio
   */
  const transcribeAudio = async (blob) => {
    try {
      const formData = new FormData();
      formData.append('file', blob, 'audio.webm');

      const response = await axios.post(`${API}/voice/transcribe`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      const transcribedText = response.data.text || '';
      setTranscript(transcribedText);
      setInput(prev => prev + (prev ? ' ' : '') + transcribedText);

      // Auto-analyze vibe
      analyzeVibe(transcribedText);
    } catch (error) {
      console.error('Transcription failed:', error);
    }
  };

  /**
   * Analyze vibe of the prompt
   */
  const analyzeVibe = async (text) => {
    try {
      const response = await axios.post(`${API}/ai/analyze`, {
        content: text,
        type: 'vibe',
      });

      setVibeAnalysis(response.data.analysis);
      setSuggestions(response.data.suggestions || []);
    } catch (error) {
      console.error('Vibe analysis failed:', error);
    }
  };

  /**
   * Handle submit
   */
  const handleSubmit = () => {
    if (input.trim()) {
      onSubmit({
        prompt: input,
        vibe: vibeAnalysis,
        transcript,
      });
      setInput('');
      setTranscript('');
      setVibeAnalysis(null);
      setSuggestions([]);
    }
  };

  /**
   * Apply suggestion
   */
  const applySuggestion = (suggestion) => {
    setInput(suggestion.text);
    analyzeVibe(suggestion.text);
  };

  return (
    <div className="space-y-4 p-6 bg-gradient-to-br from-slate-900 to-slate-800 rounded-lg border border-slate-700">
      {/* Vibe Coding Header */}
      <div className="flex items-center gap-2 mb-4">
        <Sparkles className="text-[#1A1A1A]" size={20} />
        <h3 className="text-lg font-semibold text-[#1A1A1A]">Vibe Coding</h3>
        <span className="text-xs text-slate-400 ml-auto">Manus-style natural language</span>
      </div>

      {/* Input Area */}
      <div className="space-y-3">
        {/* Text Input */}
        <div className="relative">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Describe what you want to build... (or use voice)"
            className="w-full bg-slate-800 border border-slate-600 rounded-lg p-4 text-[#1A1A1A] placeholder-slate-500 resize-none focus:outline-none focus:ring-2 focus:ring-#f5f5f50 min-h-24"
          />

          {/* Voice Button */}
          <button
            onClick={isRecording ? stopRecording : startRecording}
            disabled={isLoading}
            className={`absolute bottom-3 right-3 p-2 rounded-lg transition-all ${
              isRecording
                ? 'bg-gray-500 text-[#1A1A1A]'
                : 'bg-gray-200 hover:bg-black text-[#1A1A1A]'
            } disabled:opacity-50`}
            title={isRecording ? 'Stop recording' : 'Start recording'}
          >
            {isRecording ? <MicOff size={18} /> : <Mic size={18} />}
          </button>
        </div>

        {/* Transcript Display */}
        {transcript && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-3 bg-slate-700/50 rounded-lg border border-slate-600"
          >
            <div className="text-xs text-slate-400 mb-1">Transcribed:</div>
            <div className="text-sm text-slate-200">{transcript}</div>
          </motion.div>
        )}

        {/* Vibe Analysis */}
        {vibeAnalysis && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-4 bg-black/30 border border-#000000/50 rounded-lg"
          >
            <div className="flex items-center gap-2 mb-3">
              <Palette size={16} className="text-[#1A1A1A]" />
              <span className="font-medium text-#d0d0d0">Vibe Analysis</span>
            </div>

            <div className="space-y-2 text-sm text-slate-300">
              <div>
                <span className="text-slate-400">Style:</span>
                <span className="ml-2 text-#d0d0d0 font-medium">{vibeAnalysis.style}</span>
              </div>
              <div>
                <span className="text-slate-400">Complexity:</span>
                <span className="ml-2 text-#d0d0d0 font-medium">{vibeAnalysis.complexity}</span>
              </div>
              <div>
                <span className="text-slate-400">Tone:</span>
                <span className="ml-2 text-#d0d0d0 font-medium">{vibeAnalysis.tone}</span>
              </div>
            </div>
          </motion.div>
        )}

        {/* Suggestions */}
        {suggestions.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-2"
          >
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <Zap size={14} />
              <span>AI Suggestions</span>
            </div>
            <div className="space-y-2">
              {suggestions.map((suggestion, idx) => (
                <button
                  key={idx}
                  onClick={() => applySuggestion(suggestion)}
                  className="w-full text-left p-3 bg-slate-700/50 hover:bg-slate-700 border border-slate-600 rounded-lg transition-colors text-sm text-slate-300 hover:text-[#1A1A1A]"
                >
                  {suggestion.text}
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </div>

      {/* Submit Button */}
      <button
        onClick={handleSubmit}
        disabled={!input.trim() || isLoading}
        className="w-full bg-gradient-to-r from-#000000 to-#000000 hover:from-#000000 hover:to-#000000 text-[#1A1A1A] font-medium py-3 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
      >
        {isLoading ? (
          <>
            <Loader2 size={18} className="animate-spin" />
            Building...
          </>
        ) : (
          <>
            <Send size={18} />
            Build with Vibe
          </>
        )}
      </button>
    </div>
  );
};

/**
 * Vibe Style Selector Component
 */
export const VibeStyleSelector = ({ onStyleSelect }) => {
  const styles = [
    { id: 'minimal', name: 'Minimal', emoji: '⚪', description: 'Clean and simple' },
    { id: 'bold', name: 'Bold', emoji: '🔥', description: 'Strong and impactful' },
    { id: 'playful', name: 'Playful', emoji: '🎨', description: 'Fun and creative' },
    { id: 'professional', name: 'Professional', emoji: '💼', description: 'Business-ready' },
    { id: 'experimental', name: 'Experimental', emoji: '🧪', description: 'Cutting-edge' },
    { id: 'retro', name: 'Retro', emoji: '📼', description: 'Vintage vibes' },
  ];

  return (
    <div className="grid grid-cols-3 gap-3">
      {styles.map(style => (
        <button
          key={style.id}
          onClick={() => onStyleSelect(style.id)}
          className="p-4 bg-slate-800 hover:bg-slate-700 border border-slate-600 rounded-lg transition-all text-center space-y-2 hover:border-gray-300"
        >
          <div className="text-2xl">{style.emoji}</div>
          <div className="font-medium text-[#1A1A1A] text-sm">{style.name}</div>
          <div className="text-xs text-slate-400">{style.description}</div>
        </button>
      ))}
    </div>
  );
};

/**
 * Vibe Preset Component
 */
export const VibePreset = ({ preset, onApply }) => {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="p-4 bg-slate-800 border border-slate-600 rounded-lg space-y-3"
    >
      <div className="flex items-center justify-between">
        <h4 className="font-medium text-[#1A1A1A]">{preset.name}</h4>
        <span className="text-2xl">{preset.emoji}</span>
      </div>

      <p className="text-sm text-slate-400">{preset.description}</p>

      <div className="flex items-center gap-2 text-xs text-slate-500">
        <Volume2 size={14} />
        <span>"{preset.example}"</span>
      </div>

      <button
        onClick={() => onApply(preset)}
        className="w-full bg-black hover:bg-black text-[#1A1A1A] text-sm font-medium py-2 rounded-lg transition-colors"
      >
        Use This Vibe
      </button>
    </motion.div>
  );
};

export default {
  VibeCodingInput,
  VibeStyleSelector,
  VibePreset,
};
