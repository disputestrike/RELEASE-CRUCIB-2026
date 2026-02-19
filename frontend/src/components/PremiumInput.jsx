import React, { useState } from 'react';
import '../styles/PremiumEffects.css';
import './PremiumInput.css';

/**
 * Premium Input Component
 * 
 * A high-quality input component with smooth animations,
 * floating labels, and premium styling.
 * 
 * Props:
 * - label: Input label
 * - placeholder: Input placeholder
 * - type: Input type
 * - value: Input value
 * - onChange: Change handler
 * - error: Error message
 * - success: Success state
 * - icon: Icon component
 * - disabled: Disable input
 */

const PremiumInput = ({
  label,
  placeholder,
  type = 'text',
  value,
  onChange,
  error,
  success,
  icon: Icon,
  disabled = false,
  className = '',
  ...props
}) => {
  const [focused, setFocused] = useState(false);

  const inputClasses = `
    premium-input
    ${focused ? 'focused' : ''}
    ${error ? 'error' : ''}
    ${success ? 'success' : ''}
    ${Icon ? 'with-icon' : ''}
    ${className}
  `.trim();

  return (
    <div className="premium-input-wrapper">
      {label && (
        <label className={`premium-input-label ${focused || value ? 'active' : ''}`}>
          {label}
        </label>
      )}

      <div className="premium-input-container">
        {Icon && (
          <div className="premium-input-icon">
            <Icon size={18} />
          </div>
        )}

        <input
          className={inputClasses}
          type={type}
          placeholder={placeholder}
          value={value}
          onChange={onChange}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          disabled={disabled}
          {...props}
        />
      </div>

      {error && (
        <span className="premium-input-error">{error}</span>
      )}

      {success && (
        <span className="premium-input-success">✓ Looks good!</span>
      )}
    </div>
  );
};

export default PremiumInput;
