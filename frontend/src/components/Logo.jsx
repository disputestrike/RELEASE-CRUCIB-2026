import React, { useState } from 'react';
import { Link } from 'react-router-dom';

/**
 * Logo — approved brand mark + "CrucibAI — Inevitable AI" (or name only when
 * showTagline=false). Uses the shared SVG in public so the same mark appears on
 * landing, auth, dashboard, workspace surfaces, favicon, and install metadata.
 */
const LOGO_ICON = '/logo-approved.png';

export function Logo({
  variant: _variant = 'full',
  /**
   * Force light ink on a fixed dark background (hero strip, etc.).
   * Default: follow `data-theme` via `.logo-wordmark` / `.logo-tagline` in index.css.
   */
  dark = false,
  height = 32,
  href,
  className = '',
  alt = 'CrucibAI logo',
  showTagline = true,
  /** When false, show mark only (no "CrucibAI" wordmark). Tagline is hidden regardless of `showTagline`. */
  showWordmark = true,
  /** Optional class on the "CrucibAI" wordmark (e.g. sidebar typography). */
  nameClassName = '',
}) {
  const [iconError, setIconError] = useState(false);

  const wordmarkClass = ['logo-wordmark', dark ? 'logo-wordmark--force-light' : '', nameClassName].filter(Boolean).join(' ');
  const taglineClass = ['logo-tagline', dark ? 'logo-tagline--force-light' : ''].filter(Boolean).join(' ');

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
        <span style={{ width: `${height}px`, height: `${height}px`, display: 'inline-block', flexShrink: 0 }} aria-hidden />
      )}
      {showWordmark && (
        <span style={{ display: 'inline-flex', alignItems: 'baseline', gap: 4, flexWrap: 'nowrap' }}>
          <span
            className={wordmarkClass}
            style={{
              fontSize: Math.round(height * 0.5),
              fontWeight: 700,
              letterSpacing: '-0.02em',
            }}
          >
            CrucibAI
          </span>
          {showTagline && (
            <span
              className={taglineClass}
              style={{
                fontSize: Math.round(height * 0.4),
                fontWeight: 400,
              }}
            >
              — Inevitable AI
            </span>
          )}
        </span>
      )}
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
