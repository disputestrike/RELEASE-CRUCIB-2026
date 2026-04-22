// WS-I: in-browser preview using @webcontainer/api
// Feature-gated via localStorage.webcontainer_preview === '1'.
// Requires the backend to serve COOP/COEP headers when
// FEATURE_WEBCONTAINER_COOP=1 (see backend/server.py middleware).

import React, { useEffect, useRef, useState } from "react";

export function isWebContainerEnabled() {
  if (typeof window === "undefined") return false;
  try {
    return window.localStorage.getItem("webcontainer_preview") === "1";
  } catch (_) {
    return false;
  }
}

// files shape: { "package.json": { file: { contents: "..." } }, ... }
export default function LivePreview({ files = {}, command = "npm run dev" }) {
  const iframeRef = useRef(null);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);
  const [wcUrl, setWcUrl] = useState(null);
  const bootedRef = useRef(false);

  useEffect(() => {
    if (!isWebContainerEnabled()) return;
    if (bootedRef.current) return;
    bootedRef.current = true;

    (async () => {
      try {
        if (!window.crossOriginIsolated) {
          throw new Error(
            "Page is not cross-origin isolated. Enable FEATURE_WEBCONTAINER_COOP on the backend.",
          );
        }
        setStatus("loading api");
        const api = await import("@webcontainer/api");
        setStatus("booting");
        const wc = await api.WebContainer.boot();
        if (Object.keys(files).length) {
          setStatus("mounting");
          await wc.mount(files);
        }
        setStatus("installing");
        const install = await wc.spawn("npm", ["install"]);
        await install.exit;
        setStatus("starting");
        const [cmd, ...args] = command.split(" ");
        const proc = await wc.spawn(cmd, args);
        wc.on("server-ready", (port, url) => {
          setWcUrl(url);
          setStatus("ready");
        });
        proc.output.pipeTo(
          new WritableStream({
            write(chunk) {
              // eslint-disable-next-line no-console
              console.debug("[webcontainer]", chunk);
            },
          }),
        );
      } catch (e) {
        setError(String(e));
        setStatus("error");
      }
    })();
  }, [files, command]);

  if (!isWebContainerEnabled()) {
    return (
      <div style={{ padding: 16, opacity: 0.6 }}>
        Live preview disabled. Enable via localStorage.webcontainer_preview = '1'.
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", gap: 6 }}>
      <div style={{ fontSize: 12, opacity: 0.7 }}>
        Status: {status} {wcUrl ? `· ${wcUrl}` : ""}
      </div>
      {error && (
        <div style={{ background: "#2a1818", color: "#f99", padding: 8, borderRadius: 4 }}>
          {error}
        </div>
      )}
      <iframe
        ref={iframeRef}
        src={wcUrl || "about:blank"}
        title="Live Preview"
        style={{ flex: 1, border: 0, background: "#fff", minHeight: 300 }}
        sandbox="allow-scripts allow-same-origin allow-forms"
      />
    </div>
  );
}
