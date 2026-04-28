/**
 * VibeCoding.jsx
 * Manus-style vibe coding for natural language development
 * Supports: voice input, natural language prompts, vibe analysis, style suggestions
 */

import React, { useState, useRef } from 'react';
import { Mic, MicOff, Sparkles, Zap, Palette, Volume2, Send, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';
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
      formData.append('audio', blob, 'audio.webm');

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
      const response = await axios.post(`${API}/vibecoding/analyze`, {
        text: text,
      });

    setVibeAnalysis(response.data.vibe);
    setSuggestions(response.data.vibe?.suggestions || []);
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
    <div className="space-y-4 p-6 bg-white rounded-lg border border-gray-200">
      {/* Vibe Coding Header */}
      <div className="flex items-center gap-2 mb-4">
        <Sparkles className="text-gray-500" size={20} />
        <h3 className="text-lg font-semibold text-gray-900">Vibe Coding</h3>
        <span className="text-xs text-gray-500 ml-auto">Voice-first natural language</span>
      </div>

      {/* Input Area */}
      <div className="space-y-3">
        {/* Text Input */}
        <div className="relative">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Describe what you want to build... (or use voice)"
            className="w-full bg-gray-50 border border-gray-200 rounded-lg p-4 text-gray-900 placeholder-gray-500 resize-none focus:outline-none focus:ring-2 focus:ring-gray-500 min-h-24"
          />

          {/* Voice Button */}
          <button
            onClick={isRecording ? stopRecording : startRecording}
            disabled={isLoading}
            className={`absolute bottom-3 right-3 p-2 rounded-lg transition-all ${
              isRecording
                ? 'bg-gray-100 text-red-500 animate-pulse'
                : 'bg-gray-100 hover:bg-gray-200 text-gray-600'
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
            className="p-3 bg-gray-50 rounded-lg border border-gray-200"
          >
            <div className="text-xs text-gray-500 mb-1">Transcribed:</div>
            <div className="text-sm text-gray-700">{transcript}</div>
          </motion.div>
        )}

        {/* Vibe Analysis */}
        {vibeAnalysis && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-4 bg-gray-50 border border-gray-200 rounded-lg"
          >
            <div className="flex items-center gap-2 mb-3">
              <Palette size={16} className="text-gray-600" />
              <span className="font-medium text-gray-900">Vibe Analysis</span>
            </div>

            <div className="space-y-2 text-sm text-gray-600">
              <div>
                <span className="text-gray-500">Style:</span>
                <span className="ml-2 text-gray-900 font-medium">{vibeAnalysis.style}</span>
              </div>
              <div>
                <span className="text-gray-500">Complexity:</span>
                <span className="ml-2 text-gray-900 font-medium">{vibeAnalysis.complexity}</span>
              </div>
              <div>
                <span className="text-gray-500">Tone:</span>
                <span className="ml-2 text-gray-900 font-medium">{vibeAnalysis.tone}</span>
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
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Zap size={14} className="text-gray-400" />
              <span>AI Suggestions</span>
            </div>
            <div className="space-y-2">
              {suggestions.map((suggestion, idx) => (
                <button
                  key={idx}
                  onClick={() => applySuggestion(suggestion)}
                  className="w-full text-left p-3 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-lg transition-colors text-sm text-gray-700"
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
        className="w-full bg-gray-900 hover:bg-black text-white font-medium py-3 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
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
          className="p-4 bg-slate-800 hover:bg-slate-700 border border-slate-600 rounded-lg transition-all text-center space-y-2 hover:border-gray-500"
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
        className="w-full bg-gray-600 hover:bg-gray-700 text-[#1A1A1A] text-sm font-medium py-2 rounded-lg transition-colors"
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
