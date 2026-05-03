import React, { useState } from 'react';
import { Wand2, Plus, Check } from 'lucide-react';
import { saveCustomSkill, getAllSkills } from '../lib/skills';

export default function SkillDrafting({ onSkillSaved }) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [triggers, setTriggers] = useState('');
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    if (!name.trim()) return;
    const skill = saveCustomSkill({
      name: name.trim(),
      description: description.trim(),
      trigger: triggers.split(',').map(t => t.trim().toLowerCase()).filter(Boolean),
    });
    setSaved(true);
    onSkillSaved?.(skill);
    setTimeout(() => { setSaved(false); setName(''); setDescription(''); setTriggers(''); }, 1500);
  };

  return (
    <div className="border border-zinc-200 rounded-xl p-4 bg-white">
      <div className="flex items-center gap-2 mb-3">
        <Wand2 size={14} className="text-purple-600" />
        <span className="text-sm font-semibold text-zinc-800">Create custom skill</span>
      </div>
      <div className="space-y-2">
        <input value={name} onChange={e => setName(e.target.value)}
          placeholder="Skill name (e.g. Add PayPal)"
          className="w-full px-3 py-2 border border-zinc-200 rounded-lg text-sm outline-none focus:border-emerald-400" />
        <input value={description} onChange={e => setDescription(e.target.value)}
          placeholder="Description"
          className="w-full px-3 py-2 border border-zinc-200 rounded-lg text-sm outline-none focus:border-emerald-400" />
        <input value={triggers} onChange={e => setTriggers(e.target.value)}
          placeholder="Trigger keywords, comma-separated (e.g. PayPal, billing, payment)"
          className="w-full px-3 py-2 border border-zinc-200 rounded-lg text-sm outline-none focus:border-emerald-400" />
        <button onClick={handleSave} disabled={!name.trim()}
          className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg text-sm
            hover:bg-purple-700 disabled:opacity-50 transition">
          {saved ? <Check size={14} /> : <Plus size={14} />}
          {saved ? 'Saved!' : 'Save Skill'}
        </button>
      </div>
    </div>
  );
}
