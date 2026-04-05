import React, { useState } from 'react';
import { Link } from 'react-router-dom';

/**
 * Logo — Your icon + "CrucibAI — Inevitable AI" (or name only when showTagline=false).
 * Uses your logo image from public/logo-icon.png when present; otherwise shows
 * an inline version of your icon (dark rounded square with 2×2 grid).
 */
const LOGO_ICON = '/logo-icon.png';

/** Your icon: dark rounded square with 2×2 grid of white squares (shows when image missing) */
function YourIconSvg({ size }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
      style={{ display: 'block', flexShrink: 0 }}
    >
      <rect width="32" height="32" rx="8" fill="#2D2D2D" />
      <rect x="4" y="4" width="10" height="10" rx="2" fill="white" opacity="0.95" />
      <rect x="18" y="4" width="10" height="10" rx="2" fill="white" opacity="0.95" />
      <rect x="4" y="18" width="10" height="10" rx="2" fill="white" opacity="0.95" />
      <rect x="18" y="18" width="10" height="10" rx="2" fill="white" opacity="0.95" />
    </svg>
  );
}

export function Logo({
  variant: _variant = 'full',
  dark = false,
  height = 32,
  href,
  className = '',
  alt = 'CrucibAI logo',
  showTagline = true,
}) {
  const [iconError, setIconError] = useState(false);

  const textColor = dark ? '#fff' : '#1A1A1A';
  const mutedColor = dark ? 'rgba(255,255,255,0.8)' : '#6B7280';

  const contentInner = (
    <>
      {!iconError ? (
        <img
          src={LOGO_ICON}
          alt=""
          aria-hidden
          width={height}
          height={height}
          style={{
            width: `${height}px`,
            height: `${height}px`,
            objectFit: 'contain',
            flexShrink: 0,
            display: 'block',
          }}
          onError={() => setIconError(true)}
        />
      ) : (
        <YourIconSvg size={height} />
      )}
      <span style={{ display: 'inline-flex', alignItems: 'baseline', gap: 4, flexWrap: 'nowrap' }}>
        <span
          style={{
            fontSize: Math.round(height * 0.5),
            fontWeight: 700,
            letterSpacing: '-0.02em',
            color: textColor,
          }}
        >
          CrucibAI
        </span>
        {showTagline && (
          <span
            style={{
              fontSize: Math.round(height * 0.4),
              fontWeight: 400,
              color: mutedColor,
            }}
          >
            — Inevitable AI
          </span>
        )}
      </span>
    </>
  );

  const wrapperStyle = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 10,
    minHeight: height,
  };

  const content = href != null ? (
    <Link
      to={href === '/dashboard' ? '/app' : href}
      className={className}
      style={wrapperStyle}
      aria-label={alt}
    >
      {contentInner}
    </Link>
  ) : (
    <span className={className} style={wrapperStyle}>
      {contentInner}
    </span>
  );

  return content;
}

export default Logo;
