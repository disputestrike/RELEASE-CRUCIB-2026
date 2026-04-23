import { useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  Plus,
  FolderOpen,
  Upload,
  FileCode,
  FileText,
  File,
  X,
} from 'lucide-react';

export default function FileTree({
  files,
  activeFile,
  onSelectFile,
  onAddFile,
  onAddFolder,
  onOpenFolder,
  onDeleteFile,
}) {
  const [expandedFolders, setExpandedFolders] = useState({});

  const getFileIcon = (name) => {
    if (/\.(jsx?|tsx?)$/.test(name)) return <FileCode className="w-3.5 h-3.5 text-yellow-500 flex-shrink-0" />;
    if (/\.css$/.test(name)) return <FileText className="w-3.5 h-3.5 text-pink-500 flex-shrink-0" />;
    if (/\.html$/.test(name)) return <FileText className="w-3.5 h-3.5 flex-shrink-0" style={{ color: 'var(--theme-accent)' }} />;
    if (/\.json$/.test(name)) return <FileText className="w-3.5 h-3.5 text-yellow-600 flex-shrink-0" />;
    if (/\.(py|c|cpp|h)$/.test(name)) return <FileCode className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />;
    if (/\.(md|txt)$/.test(name)) return <FileText className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />;
    return <File className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />;
  };

  const tree = {};
  Object.keys(files).sort().forEach((path) => {
    const clean = path.replace(/^\//, '');
    const parts = clean.split('/');
    if (parts.length === 1) {
      tree[path] = null;
    } else {
      const folder = `/${parts[0]}`;
      if (!tree[folder]) tree[folder] = [];
      tree[folder].push(path);
    }
  });

  const toggleFolder = (folder) => {
    setExpandedFolders((prev) => ({ ...prev, [folder]: prev[folder] === false ? true : false }));
  };

  const isExpanded = (folder) => expandedFolders[folder] !== false;

  return (
    <div className="text-sm flex flex-col h-full">
      <div className="flex items-center justify-between px-2 py-1.5 border-b border-gray-200 bg-[#FAF9F7] flex-shrink-0">
        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Explorer</span>
        <div className="flex items-center gap-0.5">
          {onAddFile && (
            <button type="button" onClick={onAddFile} className="p-1 text-gray-400 hover:text-gray-700 rounded" title="New file">
              <Plus className="w-3.5 h-3.5" />
            </button>
          )}
          {onAddFolder && (
            <button type="button" onClick={onAddFolder} className="p-1 text-gray-400 hover:text-gray-700 rounded" title="New folder">
              <FolderOpen className="w-3.5 h-3.5" />
            </button>
          )}
          {onOpenFolder && (
            <button type="button" onClick={onOpenFolder} className="p-1 text-gray-400 hover:text-gray-700 rounded" title="Open local folder">
              <Upload className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      <div className="overflow-y-auto flex-1 py-1">
        {Object.entries(tree).map(([key, children]) => {
          if (children === null) {
            const name = key.replace(/^\//, '');
            return (
              <div key={key} className="group flex items-center">
                <button
                  type="button"
                  onClick={() => onSelectFile(key)}
                  className={`flex-1 flex items-center gap-2 px-3 py-1 text-left text-xs transition truncate ${
                    activeFile === key ? 'bg-blue-50 text-blue-800 font-medium' : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  {getFileIcon(name)}
                  <span className="truncate">{name}</span>
                </button>
                {onDeleteFile && (
                  <button type="button" onClick={() => onDeleteFile(key)} className="opacity-0 group-hover:opacity-100 pr-2 text-gray-400 hover:text-red-500 transition" title="Delete file">
                    <X className="w-3 h-3" />
                  </button>
                )}
              </div>
            );
          }
          const folderName = key.replace(/^\//, '');
          const expanded = isExpanded(key);
          return (
            <div key={key}>
              <button
                type="button"
                onClick={() => toggleFolder(key)}
                className="w-full flex items-center gap-1.5 px-2 py-1 text-left text-xs text-gray-500 hover:bg-gray-100 font-medium"
              >
                {expanded ? <ChevronDown className="w-3 h-3 flex-shrink-0" /> : <ChevronRight className="w-3 h-3 flex-shrink-0" />}
                <FolderOpen className="w-3.5 h-3.5 text-yellow-500 flex-shrink-0" />
                <span>{folderName}</span>
              </button>
              {expanded && children.map((path) => {
                const name = path.split('/').pop();
                return (
                  <div key={path} className="group flex items-center">
                    <button
                      type="button"
                      onClick={() => onSelectFile(path)}
                      className={`flex-1 flex items-center gap-2 pl-7 pr-2 py-1 text-left text-xs transition truncate ${
                        activeFile === path ? 'bg-blue-50 text-blue-800 font-medium' : 'text-gray-600 hover:bg-gray-100'
                      }`}
                    >
                      {getFileIcon(name)}
                      <span className="truncate">{name}</span>
                    </button>
                    {onDeleteFile && (
                      <button type="button" onClick={() => onDeleteFile(path)} className="opacity-0 group-hover:opacity-100 pr-2 text-gray-400 hover:text-red-500 transition" title="Delete file">
                        <X className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>
    </div>
  );
}
