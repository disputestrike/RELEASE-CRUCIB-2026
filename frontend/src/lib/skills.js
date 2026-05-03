/**
 * Skills layer — reusable named capabilities
 * Skills can be triggered by name from the workflow panel
 */
const BUILTIN_SKILLS = [
  { id: 'auth-setup', name: 'Auth Setup', description: 'JWT + OAuth2 authentication', trigger: ['auth','login','signup'] },
  { id: 'database-migrate', name: 'Database Migration', description: 'Schema + migration scripts', trigger: ['database','db','schema','migrate'] },
  { id: 'api-routes', name: 'API Routes', description: 'REST endpoints with validation', trigger: ['api','routes','endpoints'] },
  { id: 'frontend-ui', name: 'Frontend UI', description: 'React components + styling', trigger: ['ui','components','frontend','design'] },
  { id: 'deploy-app', name: 'Deploy App', description: 'Railway/Vercel deployment', trigger: ['deploy','ship','launch','production'] },
  { id: 'security-review', name: 'Security Review', description: 'AgentShield security scan', trigger: ['security','scan','vulnerability'] },
  { id: 'test-suite', name: 'Test Suite', description: 'Unit + integration tests', trigger: ['test','tests','testing','coverage'] },
  { id: 'paypal-payments', name: 'PayPal Payments', description: 'Payment integration', trigger: ['paypal','payment','billing','checkout'] },
];

let _customSkills = [];

export function loadSkills() {
  try {
    const saved = localStorage.getItem('crucibai_custom_skills');
    if (saved) _customSkills = JSON.parse(saved);
  } catch {}
}

export function getAllSkills() {
  return [...BUILTIN_SKILLS, ..._customSkills];
}

export function saveCustomSkill(skill) {
  const id = skill.id || `custom_${Date.now()}`;
  const newSkill = { ...skill, id, custom: true };
  _customSkills = _customSkills.filter(s => s.id !== id).concat(newSkill);
  try { localStorage.setItem('crucibai_custom_skills', JSON.stringify(_customSkills)); } catch {}
  return newSkill;
}

export function matchSkillToPrompt(prompt) {
  const lower = prompt.toLowerCase();
  return getAllSkills().filter(s =>
    s.trigger?.some(t => lower.includes(t)));
}

export function getSkillById(id) {
  return getAllSkills().find(s => s.id === id) || null;
}
