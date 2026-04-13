/**
 * Input Sanitization Utilities for CrucibAI
 * Prevents XSS attacks and malicious input
 */

// ==================== HTML SANITIZATION ====================

/**
 * Sanitize HTML string to prevent XSS
 * Removes dangerous tags and attributes
 */
export const sanitizeHTML = (html) => {
  if (!html || typeof html !== 'string') {
    return '';
  }

  const div = document.createElement('div');
  div.textContent = html;
  return div.innerHTML;
};

/**
 * Sanitize user input for display
 * Escapes HTML special characters
 */
export const escapeHTML = (text) => {
  if (!text || typeof text !== 'string') {
    return '';
  }

  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };

  return text.replace(/[&<>"']/g, (char) => map[char]);
};

/**
 * Sanitize URL to prevent javascript: and data: protocols
 */
export const sanitizeURL = (url) => {
  if (!url || typeof url !== 'string') {
    return '';
  }

  const trimmedURL = url.trim().toLowerCase();

  // Block dangerous protocols
  const dangerousProtocols = ['javascript:', 'data:', 'vbscript:', 'file:'];
  for (const protocol of dangerousProtocols) {
    if (trimmedURL.startsWith(protocol)) {
      return '';
    }
  }

  // Validate URL format
  try {
    new URL(url, window.location.origin);
    return url;
  } catch {
    return '';
  }
};

/**
 * Sanitize object/array recursively
 */
export const sanitizeObject = (obj) => {
  if (obj === null || obj === undefined) {
    return obj;
  }

  if (typeof obj === 'string') {
    return sanitizeHTML(obj);
  }

  if (Array.isArray(obj)) {
    return obj.map(item => sanitizeObject(item));
  }

  if (typeof obj === 'object') {
    const sanitized = {};
    for (const [key, value] of Object.entries(obj)) {
      sanitized[key] = sanitizeObject(value);
    }
    return sanitized;
  }

  return obj;
};

// ==================== INPUT VALIDATION ====================

/**
 * Validate email format
 */
export const validateEmail = (email) => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

/**
 * Validate password strength
 */
export const validatePassword = (password) => {
  const requirements = {
    minLength: password.length >= 8,
    hasUppercase: /[A-Z]/.test(password),
    hasLowercase: /[a-z]/.test(password),
    hasNumber: /\d/.test(password),
    hasSpecialChar: /[@$!%*?&]/.test(password)
  };

  const isStrong = Object.values(requirements).every(Boolean);

  return {
    isStrong,
    requirements,
    score: Object.values(requirements).filter(Boolean).length / 5
  };
};

/**
 * Validate URL format
 */
export const validateURL = (url) => {
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
};

/**
 * Validate phone number (basic)
 */
export const validatePhoneNumber = (phone) => {
  const phoneRegex = /^[-\d\s()+]{10,}$/;
  return phoneRegex.test(phone.replace(/\s/g, ''));
};

/**
 * Validate credit card (Luhn algorithm)
 */
export const validateCreditCard = (cardNumber) => {
  const digits = cardNumber.replace(/\D/g, '');

  if (digits.length < 13 || digits.length > 19) {
    return false;
  }

  let sum = 0;
  let isEven = false;

  for (let i = digits.length - 1; i >= 0; i--) {
    let digit = parseInt(digits[i], 10);

    if (isEven) {
      digit *= 2;
      if (digit > 9) {
        digit -= 9;
      }
    }

    sum += digit;
    isEven = !isEven;
  }

  return sum % 10 === 0;
};

// ==================== FILE VALIDATION ====================

/**
 * Validate file type
 */
export const validateFileType = (file, allowedTypes) => {
  if (!file || !allowedTypes) {
    return false;
  }

  return allowedTypes.includes(file.type);
};

/**
 * Validate file size
 */
export const validateFileSize = (file, maxSizeMB) => {
  if (!file) {
    return false;
  }

  const maxSizeBytes = maxSizeMB * 1024 * 1024;
  return file.size <= maxSizeBytes;
};

/**
 * Get safe filename
 */
export const getSafeFilename = (filename) => {
  if (!filename || typeof filename !== 'string') {
    return 'file';
  }

  // Remove path separators and dangerous characters
  return filename
    .replace(/[/\\]/g, '')
    .replace(/[^\w\s.-]/g, '')
    .replace(/\s+/g, '_')
    .substring(0, 255);
};

/**
 * Validate file upload
 */
export const validateFileUpload = (file, options = {}) => {
  const {
    maxSizeMB = 100,
    allowedTypes = [],
    allowedExtensions = []
  } = options;

  const errors = [];

  if (!file) {
    errors.push('No file selected');
    return { valid: false, errors };
  }

  // Check file size
  if (!validateFileSize(file, maxSizeMB)) {
    errors.push(`File size exceeds ${maxSizeMB}MB limit`);
  }

  // Check file type
  if (allowedTypes.length > 0 && !validateFileType(file, allowedTypes)) {
    errors.push(`File type not allowed. Allowed types: ${allowedTypes.join(', ')}`);
  }

  // Check file extension
  if (allowedExtensions.length > 0) {
    const extension = file.name.split('.').pop().toLowerCase();
    if (!allowedExtensions.includes(extension)) {
      errors.push(`File extension not allowed. Allowed: ${allowedExtensions.join(', ')}`);
    }
  }

  return {
    valid: errors.length === 0,
    errors
  };
};

// ==================== FORM SANITIZATION ====================

/**
 * Sanitize form data
 */
export const sanitizeFormData = (formData) => {
  const sanitized = {};

  for (const [key, value] of Object.entries(formData)) {
    if (typeof value === 'string') {
      sanitized[key] = sanitizeHTML(value).trim();
    } else if (Array.isArray(value)) {
      sanitized[key] = value.map(v => 
        typeof v === 'string' ? sanitizeHTML(v).trim() : v
      );
    } else if (typeof value === 'object' && value !== null) {
      sanitized[key] = sanitizeObject(value);
    } else {
      sanitized[key] = value;
    }
  }

  return sanitized;
};

/**
 * Validate form data against schema
 */
export const validateFormData = (formData, schema) => {
  const errors = {};

  for (const [field, rules] of Object.entries(schema)) {
    const value = formData[field];

    // Check required
    if (rules.required && (!value || value.toString().trim().length === 0)) {
      errors[field] = `${field} is required`;
      continue;
    }

    // Check min length
    if (rules.minLength && value?.length < rules.minLength) {
      errors[field] = `${field} must be at least ${rules.minLength} characters`;
      continue;
    }

    // Check max length
    if (rules.maxLength && value?.length > rules.maxLength) {
      errors[field] = `${field} must not exceed ${rules.maxLength} characters`;
      continue;
    }

    // Check pattern
    if (rules.pattern && !rules.pattern.test(value)) {
      errors[field] = rules.patternError || `${field} format is invalid`;
      continue;
    }

    // Check custom validator
    if (rules.validate) {
      const validationResult = rules.validate(value);
      if (!validationResult.valid) {
        errors[field] = validationResult.message;
      }
    }
  }

  return {
    valid: Object.keys(errors).length === 0,
    errors
  };
};

// ==================== API REQUEST SANITIZATION ====================

/**
 * Sanitize API request data
 */
export const sanitizeAPIRequest = (data) => {
  return sanitizeObject(data);
};

/**
 * Sanitize API response data
 */
export const sanitizeAPIResponse = (data) => {
  return sanitizeObject(data);
};

/**
 * Create safe API headers
 */
export const createSafeAPIHeaders = (customHeaders = {}) => {
  const headers = {
    'Content-Type': 'application/json',
    'X-Requested-With': 'XMLHttpRequest',
    ...customHeaders
  };

  // Remove any potentially dangerous headers
  delete headers['X-Frame-Options'];
  delete headers['Content-Security-Policy'];

  return headers;
};

// ==================== XSS PREVENTION ====================

/**
 * Check for XSS patterns
 */
export const checkForXSS = (input) => {
  if (!input || typeof input !== 'string') {
    return false;
  }

  const xssPatterns = [
    /<script[^>]*>.*?<\/script>/gi,
    /on\w+\s*=/gi,
    /javascript:/gi,
    /<iframe[^>]*>/gi,
    /<object[^>]*>/gi,
    /<embed[^>]*>/gi,
    /<img[^>]*onerror/gi,
    /<svg[^>]*onload/gi
  ];

  return xssPatterns.some(pattern => pattern.test(input));
};

/**
 * Sanitize if XSS detected
 */
export const sanitizeIfXSSDetected = (input) => {
  if (checkForXSS(input)) {
    return sanitizeHTML(input);
  }
  return input;
};

// ==================== CSRF PROTECTION ====================

/**
 * Get CSRF token from meta tag
 */
export const getCSRFToken = () => {
  const token = document.querySelector('meta[name="csrf-token"]');
  return token ? token.getAttribute('content') : null;
};

/**
 * Add CSRF token to request headers
 */
export const addCSRFToken = (headers = {}) => {
  const token = getCSRFToken();
  if (token) {
    headers['X-CSRF-Token'] = token;
  }
  return headers;
};

// ==================== CONTENT SECURITY POLICY ====================

/**
 * Check CSP violations
 */
export const checkCSPViolations = (callback) => {
  document.addEventListener('securitypolicyviolation', (event) => {
    console.warn('CSP Violation:', {
      violatedDirective: event.violatedDirective,
      blockedURI: event.blockedURI,
      sourceFile: event.sourceFile,
      lineNumber: event.lineNumber
    });

    if (callback) {
      callback(event);
    }
  });
};

export default {
  sanitizeHTML,
  escapeHTML,
  sanitizeURL,
  sanitizeObject,
  validateEmail,
  validatePassword,
  validateURL,
  validatePhoneNumber,
  validateCreditCard,
  validateFileType,
  validateFileSize,
  getSafeFilename,
  validateFileUpload,
  sanitizeFormData,
  validateFormData,
  sanitizeAPIRequest,
  sanitizeAPIResponse,
  createSafeAPIHeaders,
  checkForXSS,
  sanitizeIfXSSDetected,
  getCSRFToken,
  addCSRFToken,
  checkCSPViolations
};
