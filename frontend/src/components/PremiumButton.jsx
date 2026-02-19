import React from 'react';
import '../styles/PremiumEffects.css';
import './PremiumButton.css';

/**
 * Premium Button Component
 * 
 * A high-quality button component with smooth animations,
 * multiple variants, and premium styling.
 * 
 * Props:
 * - variant: 'primary' | 'secondary' | 'outline' | 'ghost'
 * - size: 'sm' | 'md' | 'lg'
 * - icon: Icon component
 * - loading: Show loading state
 * - disabled: Disable button
 * - onClick: Click handler
 * - children: Button text
 */

const PremiumButton = ({
  variant = 'primary',
  size = 'md',
  icon: Icon,
  loading = false,
  disabled = false,
  onClick,
  children,
  className = '',
  ...props
}) => {
  const buttonClasses = `
    premium-button
    premium-button-${variant}
    premium-button-${size}
    ${loading ? 'loading' : ''}
    ${disabled ? 'disabled' : ''}
    ${className}
  `.trim();

  return (
    <button
      className={buttonClasses}
      onClick={onClick}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <span className="button-loader"></span>
      ) : Icon ? (
        <>
          <Icon size={16} />
          {children && <span>{children}</span>}
        </>
      ) : (
        children
      )}
    </button>
  );
};

export default PremiumButton;
