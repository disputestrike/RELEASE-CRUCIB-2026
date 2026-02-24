import { useState, useEffect } from "react";
import axios from "axios";
import { API } from "../App";
import { logApiError } from "../utils/apiError";

export default function EcosystemIntegration() {
  const [config, setConfig] = useState(null);
  const [extensionCode, setExtensionCode] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios
      .get(`${API}/ecosystem/vscode/config`)
      .then((r) => setConfig(r.data))
      .catch((e) => logApiError("EcosystemIntegration", e))
      .finally(() => setLoading(false));
  }, []);

  const fetchExtensionCode = () => {
    axios
      .get(`${API}/ecosystem/vscode/extension-code`)
      .then((r) => setExtensionCode(r.data.code))
      .catch((e) => {
        logApiError("EcosystemIntegration extension-code", e);
        setExtensionCode("");
      });
  };

  return (
    <div className="p-6 max-w-2xl">
      <h2 className="text-lg font-medium text-[#1A1A1A] mb-2">Ecosystem</h2>
      <p className="text-sm text-[#666] mb-4">VS Code extension and remote dev. Use CrucibAI from your IDE.</p>
      {loading && <p className="text-sm text-[#666]">Loading…</p>}
      {!loading && config && (
        <div className="border border-gray-200 rounded bg-white p-4 space-y-3">
          <p className="text-sm text-[#1A1A1A]">
            <span className="font-medium">Extension ID:</span> {config.extension_id}
          </p>
          <p className="text-sm text-[#1A1A1A]">
            <span className="font-medium">Version:</span> {config.version}
          </p>
          {config.config && Object.keys(config.config).length > 0 && (
            <div>
              <p className="text-sm font-medium text-[#1A1A1A] mb-1">Config</p>
              <pre className="p-2 bg-gray-100 text-[#1A1A1A] rounded text-xs overflow-auto">{JSON.stringify(config.config, null, 2)}</pre>
            </div>
          )}
          <button type="button" onClick={fetchExtensionCode} className="px-3 py-2 border border-gray-200 text-[#1A1A1A] rounded text-sm">
            Get extension code
          </button>
          {extensionCode !== null && <pre className="p-2 bg-gray-100 text-[#1A1A1A] rounded text-xs overflow-auto max-h-32">{extensionCode}</pre>}
          <p className="text-xs text-[#666]">Install from VS Code marketplace or sideload when the extension is published.</p>
        </div>
      )}
      {!loading && !config && <p className="text-sm text-[#666]">Could not load ecosystem config.</p>}
    </div>
  );
}
