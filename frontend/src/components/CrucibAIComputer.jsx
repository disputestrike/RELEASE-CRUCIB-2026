import React, { useState, useEffect } from 'react';
import { X, Maximize2, Minimize2, ChevronLeft, ChevronRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { SandpackProvider, SandpackPreview } from '@codesandbox/sandpack-react';
import SandpackErrorBoundary from './SandpackErrorBoundary';
import './SandpackErrorBoundary.css';

/**
 * CrucibAI Computer — Inline thumbnail + modal
 * - Thumbnail (160x100) appears in conversation below progress bar during build
 * - Click opens large modal with live sandbox view, activity status, URL bar, playback scrubber
 * - White / light grey only — no dark backgrounds
 */
const CrucibAIComputer = ({
  files = {},
  isActive = false,
  thinking = '',
  activityText = '',
  tokensUsed = 0,
  tokensTotal = 50000,
  currentStep = 0,
  totalSteps = 7,
  hasBuild = false, // true when versions.length > 0 or build completed
  onAutoFix,
  onError,
}) => {
  const [modalOpen, setModalOpen] = useState(false);
  const [isCompact, setIsCompact] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [scrubberPosition, setScrubberPosition] = useState(100);

  const showThumbnail = isActive || hasBuild;
  const previewUrl = 'http://localhost:3000';
  const scrubPct = isActive ? 100 : scrubberPosition;

  useEffect(() => {
    if (isActive) setScrubberPosition(100);
  }, [isActive]);

  const handleScrubberChange = (e) => {
    if (isActive) return;
    setScrubberPosition(Number(e.target.value));
  };

  const hasFiles = files && typeof files === 'object' && Object.keys(files).length > 0;

  if (!showThumbnail) return null;

  return (
    <>
      {/* Inline thumbnail — 160x100, light theme, below progress bar */}
      <div
        className="flex-shrink-0 w-[160px] h-[100px] rounded-lg border border-gray-200 bg-white overflow-hidden cursor-pointer hover:border-gray-400 transition-colors"
        onClick={() => setModalOpen(true)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && setModalOpen(true)}
        aria-label="Open CrucibAI Computer"
      >
        {hasFiles ? (
          <div className="w-full h-full overflow-hidden [&_.sp-preview-container]:!min-h-0">
            <SandpackProvider
              template="react"
              files={files}
              theme="light"
              options={{ externalResources: ['https://cdn.tailwindcss.com'] }}
            >
              <SandpackPreview
                showNavigator={false}
                showRefreshButton={false}
                style={{ height: 100, minHeight: 100 }}
              />
            </SandpackProvider>
          </div>
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-gray-50 text-gray-400 text-xs">
            {isActive ? 'Building...' : 'Preview'}
          </div>
        )}
      </div>

      {/* Modal overlay + content */}
      <AnimatePresence>
        {modalOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[300] flex items-center justify-center p-4 bg-gray-400/15"
            onClick={() => setModalOpen(false)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              onClick={(e) => e.stopPropagation()}
              className={`bg-white border border-gray-200 rounded-xl shadow-xl flex flex-col overflow-hidden ${
                isFullscreen ? 'fixed inset-4' : isCompact ? 'w-[400px] max-h-[70vh]' : 'w-[700px] max-h-[90vh]'
              }`}
            >
              {/* Title bar */}
              <div className="flex-shrink-0 flex items-center justify-between px-4 py-2.5 border-b border-gray-200 bg-[#FAFAF8]">
                <span className="font-semibold text-gray-900">CrucibAI Computer</span>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setIsFullscreen((v) => !v)}
                    className="p-2 rounded text-gray-500 hover:text-gray-900 hover:bg-gray-200"
                    title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
                  >
                    <Maximize2 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setIsCompact((v) => !v)}
                    className="p-2 rounded text-gray-500 hover:text-gray-900 hover:bg-gray-200"
                    title={isCompact ? 'Expand' : 'Compact'}
                  >
                    <Minimize2 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setModalOpen(false)}
                    className="p-2 rounded text-gray-500 hover:text-gray-900 hover:bg-gray-200"
                    title="Close"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Activity status */}
              <div className="flex-shrink-0 px-4 py-1.5 text-xs text-gray-500 border-b border-gray-100">
                {activityText || thinking || (isActive ? 'Building your app...' : 'Preview ready')}
              </div>

              {/* URL bar */}
              <div className="flex-shrink-0 px-4 py-2 bg-gray-50 border-b border-gray-100">
                <div className="flex items-center gap-2 px-3 py-1.5 rounded bg-white border border-gray-200 text-xs text-gray-600 font-mono">
                  {previewUrl}
                </div>
              </div>

              {/* Live sandbox view */}
              <div className="flex-1 min-h-[240px] overflow-hidden bg-white">
                {hasFiles ? (
                  <SandpackProvider
                    template="react"
                    files={files}
                    theme="light"
                    options={{ externalResources: ['https://cdn.tailwindcss.com'] }}
                  >
                    <div className="w-full h-full relative">
                      <SandpackPreview
                        showNavigator={false}
                        showRefreshButton={true}
                        style={{ height: '100%', minHeight: 240 }}
                      />
                      <SandpackErrorBoundary
                        onAutoFix={onAutoFix || (async () => {})}
                        onError={onError || (() => {})}
                        maxRetries={2}
                        autoFixEnabled={false}
                      />
                    </div>
                  </SandpackProvider>
                ) : (
                  <div className="w-full h-full flex items-center justify-center bg-gray-50 text-gray-400 text-sm">
                    No preview yet
                  </div>
                )}
              </div>

              {/* Playback bar */}
              <div className="flex-shrink-0 flex items-center gap-2 px-4 py-3 border-t border-gray-200 bg-[#FAFAF8]">
                <button
                  onClick={() => !isActive && setScrubberPosition((p) => Math.max(0, p - 10))}
                  disabled={isActive}
                  className="p-1.5 rounded text-gray-500 hover:text-gray-900 hover:bg-gray-200 disabled:opacity-50"
                  title="Previous step"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  onClick={() => !isActive && setScrubberPosition((p) => Math.min(100, p + 10))}
                  disabled={isActive}
                  className="p-1.5 rounded text-gray-500 hover:text-gray-900 hover:bg-gray-200 disabled:opacity-50"
                  title="Next step"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={scrubPct}
                  onChange={handleScrubberChange}
                  disabled={isActive}
                  className="flex-1 h-2 bg-gray-200 rounded-full cursor-pointer disabled:cursor-not-allowed accent-gray-500"
                />
                <div className="flex items-center gap-1.5 text-xs text-gray-500">
                  <span
                    className={`w-2 h-2 rounded-full ${isActive ? 'animate-pulse bg-gray-800' : 'bg-gray-400'}`}
                  />
                  <span>{isActive ? 'live' : 'paused'}</span>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};

export default CrucibAIComputer;
