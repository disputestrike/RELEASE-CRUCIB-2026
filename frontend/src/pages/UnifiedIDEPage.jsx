import { useState } from "react";
import { Terminal, GitBranch, Bug, Code, Activity, FileCode, Sparkles, Puzzle } from "lucide-react";
import IDETerminal from "../components/IDETerminal";
import IDEGit from "../components/IDEGit";
import VibeCodePage from "./VibeCodePage";
import IDEDebugger from "../components/IDEDebugger";
import IDELinter from "../components/IDELinter";
import IDEProfiler from "../components/IDEProfiler";
import AIFeaturesPanel from "../components/AIFeaturesPanel";
import EcosystemIntegration from "../components/EcosystemIntegration";

const TABS = [
  { id: "terminal", label: "Terminal", icon: Terminal },
  { id: "git", label: "Git", icon: GitBranch },
  { id: "vibecode", label: "VibeCode", icon: Code },
  { id: "debug", label: "Debug", icon: Bug },
  { id: "lint", label: "Lint", icon: FileCode },
  { id: "profiler", label: "Profiler", icon: Activity },
  { id: "ai", label: "AI Features", icon: Sparkles },
  { id: "ecosystem", label: "Ecosystem", icon: Puzzle },
];

export default function UnifiedIDEPage() {
  const [active, setActive] = useState("vibecode");

  return (
    <div className="flex flex-col h-full">
      <div className="flex border-b border-gray-200 bg-white overflow-x-auto">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setActive(t.id)}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition ${
              active === t.id ? "border-[#1A1A1A] text-[#1A1A1A]" : "border-transparent text-[#666] hover:text-[#1A1A1A]"
            }`}
          >
            <t.icon className="w-4 h-4" />
            {t.label}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-auto bg-[#FAFAF8]">
        {active === "terminal" && <IDETerminal />}
        {active === "git" && <IDEGit />}
        {active === "vibecode" && <VibeCodePage />}
        {active === "debug" && <IDEDebugger />}
        {active === "lint" && <IDELinter />}
        {active === "profiler" && <IDEProfiler />}
        {active === "ai" && <AIFeaturesPanel />}
        {active === "ecosystem" && <EcosystemIntegration />}
      </div>
    </div>
  );
}
