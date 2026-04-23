/**
 * ResizableDivider — draggable vertical pane divider.
 * Props: onResize(delta), onDoubleClick, invertDelta (true = drag right grows left pane)
 */
import React, { useCallback, useRef } from 'react';
import './ResizableDivider.css';

export default function ResizableDivider({ onResize, onDoubleClick, invertDelta = false }) {
  const dragging = useRef(false);
  const startX = useRef(0);

  const endDrag = useCallback(() => {
    if (!dragging.current) return;
    dragging.current = false;
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  }, []);

  const onPointerMove = useCallback(
    (e) => {
      if (!dragging.current) return;
      const raw = startX.current - e.clientX;
      const delta = invertDelta ? -raw : raw;
      startX.current = e.clientX;
      onResize(delta);
    },
    [onResize, invertDelta],
  );

  const onPointerDown = useCallback((e) => {
    if (e.button !== 0) return;
    e.preventDefault();
    dragging.current = true;
    startX.current = e.clientX;
    e.currentTarget.setPointerCapture(e.pointerId);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, []);

  const onPointerUp = useCallback(() => {
    endDrag();
  }, [endDrag]);

  return (
    <div
      className="resizable-divider"
      role="separator"
      aria-orientation="vertical"
      aria-label={invertDelta ? 'Resize navigation panel' : 'Resize side panel'}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
      onLostPointerCapture={onPointerUp}
      onDoubleClick={onDoubleClick}
      title="Drag to resize · Double-click to reset"
    />
  );
}
