function cleanUrl(value) {
  const s = String(value || '').trim();
  return s || null;
}

function latestProofDeployPayload(proof) {
  const deployProof = Array.isArray(proof?.bundle?.deploy) ? proof.bundle.deploy.filter(Boolean) : [];
  if (!deployProof.length) return {};
  const latest = deployProof[deployProof.length - 1];
  return latest?.payload && typeof latest.payload === 'object' ? latest.payload : {};
}

export function realPreviewUrlForJob(job) {
  return (
    cleanUrl(job?.dev_server_url) ||
    cleanUrl(job?.preview_url) ||
    cleanUrl(job?.published_url) ||
    cleanUrl(job?.deploy_url)
  );
}

export function realDeployUrlForCompletion({ job, proof, deployResult } = {}) {
  const deployPayload = latestProofDeployPayload(proof);
  return (
    cleanUrl(deployResult?.deploy_url) ||
    cleanUrl(deployResult?.url) ||
    cleanUrl(deployPayload.url) ||
    cleanUrl(deployPayload.deploy_url) ||
    cleanUrl(job?.deploy_url) ||
    null
  );
}

export function compactUrlLabel(url, max = 48) {
  const s = String(url || '').replace(/^https?:\/\//, '');
  return s.slice(0, max);
}
