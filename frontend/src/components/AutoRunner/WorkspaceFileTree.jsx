/**
 * Vertical file tree built only from API path list (flat → nested); not from Sandpack/editor memory.
 */
import React, { useMemo, useEffect, useState, useCallback } from 'react';
import { ChevronRight, ChevronDown, File, Folder } from 'lucide-react';
import { normalizeWorkspacePath, pathsToNestedTree } from '../../workspace/workspaceFileUtils';
import './WorkspaceFileTree.css';

function sortChildEntries(map) {
  return [...map.entries()].sort(([a, na], [b, nb]) => {
    const da = na.isFile ? 1 : 0;
    const db = nb.isFile ? 1 : 0;
    if (da !== db) return da - db;
    return a.localeCompare(b);
  });
}

function TreeRows({ node, depth, prefix, expanded, onToggle, selectedPath, onSelectPath }) {
  const rows = [];
  const entries = sortChildEntries(node.children);
  for (const [name, child] of entries) {
    const fullPath = prefix ? `${prefix}/${name}` : name;
    const isFolder = !child.isFile || child.children.size > 0;
    const isOpen = expanded.has(fullPath);
    const isSelected = selectedPath === fullPath;

    if (isFolder) {
      rows.push(
        <div
          key={fullPath}
          className={`wft-row wft-row--folder ${isSelected ? 'wft-row--selected' : ''}`}
          style={{ paddingLeft: 4 + depth * 12 }}
          onClick={(e) => {
            e.stopPropagation();
            onToggle(fullPath);
            if (child.isFile && child.children.size === 0) onSelectPath(fullPath);
          }}
        >
          <button
            type="button"
            className="wft-chev"
            aria-label={isOpen ? 'Collapse' : 'Expand'}
            onClick={(e) => {
              e.stopPropagation();
              onToggle(fullPath);
            }}
          >
            {isOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          </button>
          <Folder size={12} style={{ opacity: 0.75, flexShrink: 0 }} />
          <span className="wft-label">{name}</span>
        </div>,
      );
      if (isOpen) {
        rows.push(...TreeRows({ node: child, depth: depth + 1, prefix: fullPath, expanded, onToggle, selectedPath, onSelectPath }));
      }
    } else {
      rows.push(
        <div
          key={fullPath}
          role="treeitem"
          className={`wft-row ${isSelected ? 'wft-row--selected' : ''}`}
          style={{ paddingLeft: 4 + depth * 12 }}
          onClick={() => onSelectPath(fullPath)}
        >
          <span className="wft-spacer" />
          <File size={12} style={{ opacity: 0.65, flexShrink: 0 }} />
          <span className="wft-label">{name}</span>
        </div>,
      );
    }
  }
  return rows;
}

export default function WorkspaceFileTree({
  paths = [],
  selectedPath = '',
  onSelectPath,
  /** Increment to expand ancestors of `selectedPath` */
  revealTick = 0,
  loading = false,
}) {
  const tree = useMemo(() => pathsToNestedTree(paths), [paths]);
  const [expanded, setExpanded] = useState(() => new Set());

  const ensureExpandedTo = useCallback(
    (posixPath) => {
      const n = normalizeWorkspacePath(posixPath);
      if (!n) return;
      const parts = n.split('/').filter(Boolean);
      setExpanded((prev) => {
        const next = new Set(prev);
        let acc = '';
        for (let i = 0; i < parts.length - 1; i += 1) {
          acc = acc ? `${acc}/${parts[i]}` : parts[i];
          next.add(acc);
        }
        return next;
      });
    },
    [],
  );

  useEffect(() => {
    if (revealTick && selectedPath) ensureExpandedTo(selectedPath);
  }, [revealTick, selectedPath, ensureExpandedTo]);

  const onToggle = useCallback((fullPath) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(fullPath)) next.delete(fullPath);
      else next.add(fullPath);
      return next;
    });
  }, []);

  const handleSelectPath = useCallback(
    (p) => {
      onSelectPath?.(normalizeWorkspacePath(p));
    },
    [onSelectPath],
  );

  const normSelected = normalizeWorkspacePath(selectedPath);

  return (
    <div className="wft-wrap">
      <div className="wft-header">Workspace</div>
      {loading ? <div className="wft-loading">Loading tree…</div> : null}
      {!loading && (!paths || paths.length === 0) ? (
        <div className="wft-empty">No files listed yet. Run a job or sync.</div>
      ) : null}
      <div className="wft-scroll" role="tree">
        {!loading && paths?.length > 0
          ? TreeRows({
              node: tree,
              depth: 0,
              prefix: '',
              expanded,
              onToggle,
              selectedPath: normSelected,
              onSelectPath: handleSelectPath,
            })
          : null}
      </div>
    </div>
  );
}
