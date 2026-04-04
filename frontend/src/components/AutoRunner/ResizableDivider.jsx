/**
 * ResizableDivider — draggable vertical pane divider.
 * Props: onResize(delta), onDoubleClick
 */
import React, { useCallback, useRef } from 'react';
import './ResizableDivider.css';

export default function ResizableDivider({ onResize, onDoubleClick }) {
  const dragging = useRef(false);
  const startX = useRef(0);

  const onMouseMove = useCallback((e) => {
    if (!dragging.current) return;
    const delta = startX.current - e.clientX;
    startX.current = e.clientX;
    onResize(delta);
  }, [onResize]);

  const onMouseUp = useCallback(() => {
    dragging.current = false;
    document.removeEventListener('mousemove', onMouseMove);
    document.removeEventListener('mouseup', onMouseUp);
  }, [onMouseMove]);

  const onMouseDown = useCallback((e) => {
    dragging.current = true;
    startX.current = e.clientX;
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
    e.preventDefault();
  }, [onMouseMove, onMouseUp]);

  return (
    <div
      className="resizable-divider"
      onMouseDown={onMouseDown}
      onDoubleClick={onDoubleClick}
      title="Drag to resize · Double-click to reset"
    />
  );
}
