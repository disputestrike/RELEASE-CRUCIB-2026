/**
 * Performance Optimization Utilities for CrucibAI
 * Includes caching, lazy loading, code splitting, and monitoring
 */

import React from 'react';

// ==================== PERFORMANCE MONITORING ====================

/**
 * Measure component render time
 */
export const useRenderTime = (componentName) => {
  React.useEffect(() => {
    const startTime = performance.now();

    return () => {
      const endTime = performance.now();
      const renderTime = endTime - startTime;
      
      if (renderTime > 16) { // More than one frame (60fps)
        console.warn(`${componentName} took ${renderTime.toFixed(2)}ms to render`);
      }
    };
  }, [componentName]);
};

/**
 * Track Web Vitals
 */
export const trackWebVitals = (callback) => {
  // Largest Contentful Paint (LCP)
  const lcpObserver = new PerformanceObserver((list) => {
    const entries = list.getEntries();
    const lastEntry = entries[entries.length - 1];
    callback({
      metric: 'LCP',
      value: lastEntry.renderTime || lastEntry.loadTime,
      rating: lastEntry.renderTime || lastEntry.loadTime > 2500 ? 'poor' : 'good'
    });
  });

  try {
    lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] });
  } catch (e) {
    // LCP not supported
  }

  // First Input Delay (FID)
  const fidObserver = new PerformanceObserver((list) => {
    const entries = list.getEntries();
    entries.forEach((entry) => {
      callback({
        metric: 'FID',
        value: entry.processingDuration,
        rating: entry.processingDuration > 100 ? 'poor' : 'good'
      });
    });
  });

  try {
    fidObserver.observe({ entryTypes: ['first-input'] });
  } catch (e) {
    // FID not supported
  }

  // Cumulative Layout Shift (CLS)
  let clsValue = 0;
  const clsObserver = new PerformanceObserver((list) => {
    list.getEntries().forEach((entry) => {
      if (!entry.hadRecentInput) {
        clsValue += entry.value;
        callback({
          metric: 'CLS',
          value: clsValue,
          rating: clsValue > 0.1 ? 'poor' : 'good'
        });
      }
    });
  });

  try {
    clsObserver.observe({ entryTypes: ['layout-shift'] });
  } catch (e) {
    // CLS not supported
  }
};

/**
 * Measure API response time
 */
export const measureAPITime = async (url, options = {}) => {
  const startTime = performance.now();

  try {
    const response = await fetch(url, options);
    const endTime = performance.now();
    const duration = endTime - startTime;

    return {
      success: response.ok,
      status: response.status,
      duration,
      rating: duration > 1000 ? 'slow' : duration > 500 ? 'moderate' : 'fast'
    };
  } catch (error) {
    const endTime = performance.now();
    const duration = endTime - startTime;

    return {
      success: false,
      error: error.message,
      duration,
      rating: 'error'
    };
  }
};

// ==================== CACHING ====================

/**
 * Simple in-memory cache
 */
class MemoryCache {
  constructor(maxSize = 100, ttl = 3600000) { // 1 hour TTL
    this.cache = new Map();
    this.maxSize = maxSize;
    this.ttl = ttl;
  }

  set(key, value) {
    if (this.cache.size >= this.maxSize) {
      const firstKey = this.cache.keys().next().value;
      this.cache.delete(firstKey);
    }

    this.cache.set(key, {
      value,
      timestamp: Date.now()
    });
  }

  get(key) {
    const item = this.cache.get(key);

    if (!item) {
      return null;
    }

    // Check if expired
    if (Date.now() - item.timestamp > this.ttl) {
      this.cache.delete(key);
      return null;
    }

    return item.value;
  }

  clear() {
    this.cache.clear();
  }

  has(key) {
    return this.cache.has(key);
  }
}

export const apiCache = new MemoryCache();

/**
 * Cached fetch with automatic cache management
 */
export const cachedFetch = async (url, options = {}, _cacheTime = 3600000) => {
  const cacheKey = `${url}_${JSON.stringify(options)}`;

  // Check cache
  const cached = apiCache.get(cacheKey);
  if (cached) {
    return cached;
  }

  // Fetch and cache
  try {
    const response = await fetch(url, options);
    const data = await response.json();

    if (response.ok) {
      apiCache.set(cacheKey, data);
    }

    return data;
  } catch (error) {
    console.error('Fetch error:', error);
    throw error;
  }
};

/**
 * LocalStorage cache with expiration
 */
export const useLocalStorageCache = (key, fetcher, ttl = 3600000) => {
  const [data, setData] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    const fetchData = async () => {
      try {
        // Check localStorage
        const cached = localStorage.getItem(key);
        if (cached) {
          const { value, timestamp } = JSON.parse(cached);
          if (Date.now() - timestamp < ttl) {
            setData(value);
            setLoading(false);
            return;
          }
        }

        // Fetch new data
        const result = await fetcher();
        localStorage.setItem(key, JSON.stringify({
          value: result,
          timestamp: Date.now()
        }));

        setData(result);
        setError(null);
      } catch (err) {
        setError(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [key, fetcher, ttl]);

  return { data, loading, error };
};

// ==================== LAZY LOADING ====================

/**
 * Lazy load images with Intersection Observer
 */
export const useLazyImage = (ref) => {
  const [isLoaded, setIsLoaded] = React.useState(false);

  React.useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setIsLoaded(true);
        observer.unobserve(entry.target);
      }
    }, {
      rootMargin: '50px'
    });

    const node = ref.current;
    if (node) {
      observer.observe(node);
    }

    return () => {
      if (node) {
        observer.unobserve(node);
      }
    };
  }, [ref]);

  return isLoaded;
};

/**
 * Lazy load component
 */
export const lazyLoadComponent = (importFunc) => {
  return React.lazy(() => importFunc());
};

/**
 * Prefetch resources
 */
export const prefetchResource = (url, type = 'script') => {
  const link = document.createElement('link');
  link.rel = 'prefetch';
  link.as = type;
  link.href = url;
  document.head.appendChild(link);
};

// ==================== DEBOUNCING & THROTTLING ====================

/**
 * Debounce function
 */
export const debounce = (func, delay) => {
  let timeoutId;

  return (...args) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => {
      func(...args);
    }, delay);
  };
};

/**
 * Throttle function
 */
export const throttle = (func, limit) => {
  let inThrottle;

  return (...args) => {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => {
        inThrottle = false;
      }, limit);
    }
  };
};

/**
 * useDebounce hook
 */
export const useDebounce = (value, delay) => {
  const [debouncedValue, setDebouncedValue] = React.useState(value);

  React.useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => clearTimeout(handler);
  }, [value, delay]);

  return debouncedValue;
};

/**
 * useThrottle hook
 */
export const useThrottle = (value, limit) => {
  const [throttledValue, setThrottledValue] = React.useState(value);
  const lastRan = React.useRef(Date.now());

  React.useEffect(() => {
    const handler = setTimeout(() => {
      if (Date.now() - lastRan.current >= limit) {
        setThrottledValue(value);
        lastRan.current = Date.now();
      }
    }, limit - (Date.now() - lastRan.current));

    return () => clearTimeout(handler);
  }, [value, limit]);

  return throttledValue;
};

// ==================== BUNDLE OPTIMIZATION ====================

/**
 * Analyze bundle size
 */
export const analyzeBundleSize = () => {
  if (window.__BUNDLE_STATS__) {
    return window.__BUNDLE_STATS__;
  }

  return {
    warning: 'Bundle stats not available. Run build with --analyze flag.'
  };
};

/**
 * Code splitting helper
 */
export const splitCode = (importFunc) => {
  return React.lazy(() => importFunc());
};

// ==================== MEMORY OPTIMIZATION ====================

/**
 * Clean up memory leaks
 */
export const useCleanup = (cleanup) => {
  React.useEffect(() => {
    return cleanup;
  }, [cleanup]);
};

/**
 * Memoize expensive computations
 */
export const useMemoizedValue = (value, dependencies) => {
  // Caller passes the dependency list (not always a literal); mirrors useMemo contract.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  return React.useMemo(() => value, dependencies);
};

/**
 * Memoize callbacks
 */
export const useMemoizedCallback = (callback, dependencies) => {
  // eslint-disable-next-line react-hooks/exhaustive-deps
  return React.useCallback(callback, dependencies);
};

// ==================== REQUEST OPTIMIZATION ====================

/**
 * Batch API requests
 */
export const batchRequests = async (requests) => {
  return Promise.all(requests);
};

/**
 * Queue requests to prevent overload
 */
class RequestQueue {
  constructor(maxConcurrent = 3) {
    this.queue = [];
    this.running = 0;
    this.maxConcurrent = maxConcurrent;
  }

  async add(request) {
    return new Promise((resolve, reject) => {
      this.queue.push({ request, resolve, reject });
      this.process();
    });
  }

  async process() {
    if (this.running >= this.maxConcurrent || this.queue.length === 0) {
      return;
    }

    this.running++;
    const { request, resolve, reject } = this.queue.shift();

    try {
      const result = await request();
      resolve(result);
    } catch (error) {
      reject(error);
    } finally {
      this.running--;
      this.process();
    }
  }
}

export const requestQueue = new RequestQueue();

// ==================== RENDERING OPTIMIZATION ====================

/**
 * Virtual scrolling for large lists
 */
export const VirtualList = React.memo(({
  items,
  itemHeight,
  containerHeight,
  renderItem
}) => {
  const [scrollTop, setScrollTop] = React.useState(0);

  const startIndex = Math.floor(scrollTop / itemHeight);
  const endIndex = Math.ceil((scrollTop + containerHeight) / itemHeight);
  const visibleItems = items.slice(startIndex, endIndex);

  return (
    <div
      style={{ height: containerHeight, overflow: 'auto' }}
      onScroll={(e) => setScrollTop(e.target.scrollTop)}
    >
      <div style={{ height: items.length * itemHeight, position: 'relative' }}>
        {visibleItems.map((item, index) => (
          <div
            key={startIndex + index}
            style={{
              position: 'absolute',
              top: (startIndex + index) * itemHeight,
              height: itemHeight,
              width: '100%'
            }}
          >
            {renderItem(item, startIndex + index)}
          </div>
        ))}
      </div>
    </div>
  );
});

VirtualList.displayName = 'VirtualList';

/**
 * Prevent unnecessary re-renders
 */
export const usePrevious = (value) => {
  const ref = React.useRef();

  React.useEffect(() => {
    ref.current = value;
  }, [value]);

  return ref.current;
};

export default {
  useRenderTime,
  trackWebVitals,
  measureAPITime,
  MemoryCache,
  apiCache,
  cachedFetch,
  useLocalStorageCache,
  useLazyImage,
  lazyLoadComponent,
  prefetchResource,
  debounce,
  throttle,
  useDebounce,
  useThrottle,
  analyzeBundleSize,
  splitCode,
  useCleanup,
  useMemoizedValue,
  useMemoizedCallback,
  batchRequests,
  requestQueue,
  VirtualList,
  usePrevious
};
