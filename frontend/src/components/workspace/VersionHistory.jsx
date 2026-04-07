import { Undo2 } from 'lucide-react';

export default function VersionHistory({ versions, onRestore, currentVersion }) {
  return (
    <div className="p-3 space-y-2 overflow-y-auto h-full">
      <div className="text-xs text-gray-500 uppercase tracking-wider mb-3">Version History</div>
      {versions.length === 0 ? (
        <div className="text-sm text-gray-500">No versions yet</div>
      ) : (
        versions.map((version, i) => (
          <div
            key={version.id}
            className={`p-3 rounded-lg cursor-pointer transition ${
              currentVersion === version.id ? 'bg-gray-200 border border-gray-300' : 'bg-gray-50 hover:bg-gray-100 border border-transparent'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium text-gray-800">v{versions.length - i}</span>
              <span className="text-xs text-gray-500">{version.time}</span>
            </div>
            <p className="text-xs text-gray-600 mb-2 line-clamp-2">{version.prompt}</p>
            {currentVersion !== version.id && (
              <button
                type="button"
                onClick={() => onRestore(version)}
                className="flex items-center gap-1 text-xs text-gray-800 hover:text-gray-900"
              >
                <Undo2 className="w-3 h-3" />
                Restore
              </button>
            )}
          </div>
        ))
      )}
    </div>
  );
}
