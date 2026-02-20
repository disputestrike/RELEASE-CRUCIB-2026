import React from 'react';
import '../styles/PremiumEffects.css';
import './PremiumCard.css';

/**
 * Premium Card Component
 * 
 * A high-quality card component with 3D effects,
 * smooth animations, and premium styling.
 * 
 * Props:
 * - title: Card title
 * - description: Card description
 * - icon: Icon component
 * - gradient: Whether to use gradient background
 * - elevated: Whether to show elevation effect
 * - onClick: Click handler
 * - children: Card content
 */

const PremiumCard = ({
  title,
  description,
  icon: Icon,
  gradient = false,
  elevated = true,
  onClick,
  children,
  className = ''
}) => {
  return (
    <div
      className={`premium-card ${elevated ? 'card-elevated' : ''} ${gradient ? 'gradient-orange' : ''} ${className}`}
      onClick={onClick}
      role="article"
    >
      {Icon && (
        <div className="premium-card-icon">
          <Icon size={24} />
        </div>
      )}

      {title && (
        <h3 className="premium-card-title">{title}</h3>
      )}

      {description && (
        <p className="premium-card-description">{description}</p>
      )}

      {children && (
        <div className="premium-card-content">
          {children}
        </div>
      )}
    </div>
  );
};

export default PremiumCard;
