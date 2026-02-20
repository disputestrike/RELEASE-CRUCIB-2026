/**
 * Displays code quality score from orchestration v2 (quality_score on project).
 * Shows overall 0-100 and breakdown (frontend, backend, database, tests).
 */
export default function QualityScore({ score }) {
  if (!score) return null;
  const overall = score.overall_score ?? 0;
  const verdict = score.verdict ?? "needs_work";
  const breakdown = score.breakdown ?? {};

  const getColor = (s) => {
    if (s >= 80) return "bg-gray-500";
    if (s >= 60) return "bg-gray-700";
    return "bg-gray-500";
  };

  return (
    <div className="p-4 rounded-lg bg-gray-900 border border-gray-700">
      <div className="flex items-center gap-3">
        <div className={`w-14 h-14 rounded-full flex items-center justify-center text-[#1A1A1A] font-bold text-lg ${getColor(overall)}`}>
          {Math.round(overall)}
        </div>
        <div>
          <h3 className="text-lg font-semibold capitalize">{verdict.replace("_", " ")}</h3>
          <div className="text-sm text-gray-400 grid grid-cols-2 gap-x-4 gap-y-0.5 mt-1">
            {breakdown.frontend != null && <span>Frontend: {breakdown.frontend.score?.toFixed(1) ?? 0}/100</span>}
            {breakdown.backend != null && <span>Backend: {breakdown.backend.score?.toFixed(1) ?? 0}/100</span>}
            {breakdown.database != null && <span>Database: {breakdown.database.score?.toFixed(1) ?? 0}/100</span>}
            {breakdown.tests != null && <span>Tests: {breakdown.tests.score?.toFixed(1) ?? 0}/100</span>}
          </div>
        </div>
      </div>
    </div>
  );
}
