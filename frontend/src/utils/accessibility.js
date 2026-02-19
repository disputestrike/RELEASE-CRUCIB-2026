/**
 * Accessibility Utilities for CrucibAI
 * Provides helpers for WCAG 2.1 Level AA compliance
 */

// ==================== KEYBOARD NAVIGATION ====================

/**
 * Handle keyboard navigation for interactive elements
 * Supports Enter and Space key activation
 */
export const handleKeyDown = (callback, allowedKeys = ['Enter', ' ']) => {
  return (event) => {
    if (allowedKeys.includes(event.key)) {
      event.preventDefault();
      callback(event);
    }
  };
};

/**
 * Create keyboard-accessible button handler
 */
export const createAccessibleButton = (onClick) => {
  return {
    onClick,
    onKeyDown: handleKeyDown(onClick),
    role: 'button',
    tabIndex: 0
  };
};

/**
 * Trap focus within a modal or dialog
 */
export const useFocusTrap = (ref) => {
  React.useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key !== 'Tab') return;

      const focusableElements = ref.current?.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );

      if (!focusableElements || focusableElements.length === 0) return;

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      if (event.shiftKey) {
        if (document.activeElement === firstElement) {
          event.preventDefault();
          lastElement.focus();
        }
      } else {
        if (document.activeElement === lastElement) {
          event.preventDefault();
          firstElement.focus();
        }
      }
    };

    ref.current?.addEventListener('keydown', handleKeyDown);
    return () => ref.current?.removeEventListener('keydown', handleKeyDown);
  }, [ref]);
};

// ==================== ARIA LABELS ====================

/**
 * Generate ARIA label for icon-only buttons
 */
export const getIconButtonAriaLabel = (icon, action) => {
  const iconNames = {
    'menu': 'Open menu',
    'close': 'Close',
    'search': 'Search',
    'settings': 'Settings',
    'user': 'User profile',
    'logout': 'Logout',
    'delete': 'Delete',
    'edit': 'Edit',
    'save': 'Save',
    'cancel': 'Cancel',
    'download': 'Download',
    'upload': 'Upload',
    'share': 'Share',
    'copy': 'Copy',
    'refresh': 'Refresh',
    'back': 'Go back',
    'next': 'Go to next',
    'previous': 'Go to previous'
  };

  return iconNames[icon] || action || 'Button';
};

/**
 * Create ARIA attributes for form fields
 */
export const createFormFieldAriaAttrs = (fieldName, isRequired, hasError, errorMessage) => {
  return {
    'aria-label': fieldName,
    'aria-required': isRequired,
    'aria-invalid': hasError,
    'aria-describedby': hasError ? `${fieldName}-error` : undefined
  };
};

// ==================== SCREEN READER ANNOUNCEMENTS ====================

/**
 * Announce message to screen readers
 */
export const announceToScreenReader = (message, priority = 'polite') => {
  const announcement = document.createElement('div');
  announcement.setAttribute('role', 'status');
  announcement.setAttribute('aria-live', priority);
  announcement.setAttribute('aria-atomic', 'true');
  announcement.className = 'sr-only'; // Visually hidden but accessible
  announcement.textContent = message;

  document.body.appendChild(announcement);

  // Remove after announcement
  setTimeout(() => {
    announcement.remove();
  }, 1000);
};

/**
 * Announce form submission status
 */
export const announceFormStatus = (success, message) => {
  const status = success ? 'Success' : 'Error';
  announceToScreenReader(`${status}: ${message}`, 'assertive');
};

// ==================== COLOR CONTRAST ====================

/**
 * Check if color contrast meets WCAG AA standards
 * Returns luminance ratio
 */
export const getContrastRatio = (color1, color2) => {
  const getLuminance = (color) => {
    // Convert hex to RGB
    const hex = color.replace('#', '');
    const r = parseInt(hex.substr(0, 2), 16) / 255;
    const g = parseInt(hex.substr(2, 2), 16) / 255;
    const b = parseInt(hex.substr(4, 2), 16) / 255;

    // Calculate relative luminance
    const luminance = (value) => {
      return value <= 0.03928
        ? value / 12.92
        : Math.pow((value + 0.055) / 1.055, 2.4);
    };

    return 0.2126 * luminance(r) + 0.7152 * luminance(g) + 0.0722 * luminance(b);
  };

  const lum1 = getLuminance(color1);
  const lum2 = getLuminance(color2);
  const lighter = Math.max(lum1, lum2);
  const darker = Math.min(lum1, lum2);

  return (lighter + 0.05) / (darker + 0.05);
};

/**
 * Check if contrast ratio meets WCAG standards
 */
export const meetsWCAGStandard = (ratio, level = 'AA', size = 'normal') => {
  // Normal text: AA = 4.5:1, AAA = 7:1
  // Large text (18pt+): AA = 3:1, AAA = 4.5:1
  const standards = {
    AA: { normal: 4.5, large: 3 },
    AAA: { normal: 7, large: 4.5 }
  };

  const standard = standards[level][size];
  return ratio >= standard;
};

// ==================== TEXT ALTERNATIVES ====================

/**
 * Validate image alt text
 */
export const validateAltText = (altText) => {
  if (!altText || altText.trim().length === 0) {
    return { valid: false, message: 'Alt text is required' };
  }

  if (altText.toLowerCase().includes('image of') || altText.toLowerCase().includes('picture of')) {
    return { valid: false, message: 'Alt text should not include "image of" or "picture of"' };
  }

  if (altText.length > 125) {
    return { valid: false, message: 'Alt text should be concise (max 125 characters)' };
  }

  return { valid: true, message: 'Alt text is valid' };
};

/**
 * Generate descriptive alt text template
 */
export const getAltTextTemplate = (imageType) => {
  const templates = {
    logo: 'Company logo',
    icon: 'Icon representing [description]',
    chart: 'Chart showing [data description]',
    photo: 'Photo of [subject]',
    screenshot: 'Screenshot showing [content]',
    diagram: 'Diagram illustrating [concept]',
    button: 'Button to [action]'
  };

  return templates[imageType] || 'Image';
};

// ==================== FOCUS MANAGEMENT ====================

/**
 * Move focus to element
 */
export const focusElement = (element) => {
  if (element) {
    element.focus();
    // Ensure element is visible
    element.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
};

/**
 * Get first focusable element in container
 */
export const getFirstFocusableElement = (container) => {
  const focusableElements = container?.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  return focusableElements?.[0];
};

/**
 * Skip to main content link
 */
export const SkipToMainLink = () => {
  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only focus:absolute focus:top-0 focus:left-0 focus:bg-blue-600 focus:text-[#1A1A1A] focus:p-2 focus:z-50"
    >
      Skip to main content
    </a>
  );
};

// ==================== SEMANTIC HTML ====================

/**
 * Ensure semantic HTML structure
 */
export const semanticHTMLChecklist = {
  useNav: 'Use <nav> for navigation',
  useMain: 'Use <main> for main content',
  useArticle: 'Use <article> for independent content',
  useSection: 'Use <section> for thematic grouping',
  useAside: 'Use <aside> for supplementary content',
  useHeader: 'Use <header> for introductory content',
  useFooter: 'Use <footer> for footer content',
  useHeadings: 'Use proper heading hierarchy (h1-h6)',
  useLists: 'Use <ul>, <ol>, <dl> for lists',
  useLabels: 'Use <label> for form fields'
};

// ==================== FORM ACCESSIBILITY ====================

/**
 * Create accessible form field wrapper
 */
export const AccessibleFormField = ({
  label,
  id,
  error,
  required,
  children,
  hint
}) => {
  return (
    <div className="mb-4">
      <label
        htmlFor={id}
        className="block text-sm font-medium text-gray-700 mb-1"
      >
        {label}
        {required && <span className="text-red-600 ml-1" aria-label="required">*</span>}
      </label>

      {hint && (
        <p id={`${id}-hint`} className="text-xs text-gray-600 mb-2">
          {hint}
        </p>
      )}

      {children}

      {error && (
        <p
          id={`${id}-error`}
          className="text-xs text-red-600 mt-1"
          role="alert"
        >
          {error}
        </p>
      )}
    </div>
  );
};

// ==================== TESTING UTILITIES ====================

/**
 * Check page for accessibility issues
 */
export const checkAccessibility = () => {
  const issues = [];

  // Check for images without alt text
  document.querySelectorAll('img').forEach((img) => {
    if (!img.alt || img.alt.trim().length === 0) {
      issues.push(`Image missing alt text: ${img.src}`);
    }
  });

  // Check for buttons without accessible names
  document.querySelectorAll('button').forEach((btn) => {
    const hasText = btn.textContent?.trim().length > 0;
    const hasAriaLabel = btn.getAttribute('aria-label');
    const hasTitle = btn.getAttribute('title');

    if (!hasText && !hasAriaLabel && !hasTitle) {
      issues.push('Button missing accessible name');
    }
  });

  // Check for form fields without labels
  document.querySelectorAll('input, textarea, select').forEach((field) => {
    const id = field.id;
    const label = id ? document.querySelector(`label[for="${id}"]`) : null;
    const ariaLabel = field.getAttribute('aria-label');

    if (!label && !ariaLabel) {
      issues.push(`Form field missing label: ${field.name || field.id}`);
    }
  });

  // Check heading hierarchy
  const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
  let lastLevel = 0;
  headings.forEach((heading) => {
    const level = parseInt(heading.tagName[1]);
    if (level - lastLevel > 1) {
      issues.push(`Heading hierarchy skipped: ${heading.tagName}`);
    }
    lastLevel = level;
  });

  return issues;
};

export default {
  handleKeyDown,
  createAccessibleButton,
  useFocusTrap,
  getIconButtonAriaLabel,
  createFormFieldAriaAttrs,
  announceToScreenReader,
  announceFormStatus,
  getContrastRatio,
  meetsWCAGStandard,
  validateAltText,
  getAltTextTemplate,
  focusElement,
  getFirstFocusableElement,
  SkipToMainLink,
  AccessibleFormField,
  checkAccessibility
};
