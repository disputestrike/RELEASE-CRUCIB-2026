/**
 * useAutoScroll - Smart auto-scroll behavior for execution thread
 * 
 * Auto-scrolls to bottom when new events arrive, but only if user
 * is already near the bottom. Respects manual scroll.
 */

import { useRef, useCallback, useEffect, useState } from 'react';

interface UseAutoScrollOptions {
  threshold?: number; // pixels from bottom to trigger auto-scroll
}

export function useAutoScroll<T extends HTMLElement>(
  options: UseAutoScrollOptions = {}
) {
  const { threshold = 100 } = options;
  const containerRef = useRef<T>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);
  const lastScrollTop = useRef(0);

  // Check if scroll is near bottom
  const checkScrollPosition = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;

    const { scrollTop, scrollHeight, clientHeight } = container;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
    const atBottom = distanceFromBottom < threshold;

    setIsAtBottom(atBottom);
    
    // Auto-enable if user scrolls to bottom
    if (atBottom && !shouldAutoScroll) {
      setShouldAutoScroll(true);
    }
    
    lastScrollTop.current = scrollTop;
  }, [threshold, shouldAutoScroll]);

  // Handle scroll event
  const handleScroll = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;

    const { scrollTop, scrollHeight, clientHeight } = container;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
    const atBottom = distanceFromBottom < threshold;

    // If user scrolls up manually, disable auto-scroll
    if (scrollTop < lastScrollTop.current && !atBottom) {
      setShouldAutoScroll(false);
    }
    
    // If user scrolls to bottom, re-enable auto-scroll
    if (atBottom) {
      setShouldAutoScroll(true);
    }

    lastScrollTop.current = scrollTop;
    setIsAtBottom(atBottom);
  }, [threshold]);

  // Scroll to bottom
  const scrollToBottom = useCallback((behavior: ScrollBehavior = 'smooth') => {
    const container = containerRef.current;
    if (!container) return;

    container.scrollTo({
      top: container.scrollHeight,
      behavior,
    });
  }, []);

  // Auto-scroll effect
  useEffect(() => {
    if (shouldAutoScroll && isAtBottom) {
      scrollToBottom('smooth');
    }
  }, [shouldAutoScroll, isAtBottom, scrollToBottom]);

  return {
    containerRef,
    isAtBottom,
    shouldAutoScroll,
    scrollToBottom,
    handleScroll,
    checkScrollPosition,
    enableAutoScroll: () => setShouldAutoScroll(true),
    disableAutoScroll: () => setShouldAutoScroll(false),
  };
}
