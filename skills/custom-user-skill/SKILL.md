---
name: custom-user-skill
description: Template for users to create their own custom skills. Use when a user wants to add a custom skill, define a new capability, or create a specialized building pattern that CrucibAI should learn and apply. This is the user-extensible skill framework — supports any domain, any build pattern, any specialized workflow.
metadata:
  version: '1.0'
  category: custom
  icon: ✨
  color: '#a855f7'
---

# Custom Skill Template

## Purpose

This is the base template for user-defined skills. When a user creates a custom skill, CrucibAI applies it automatically whenever a matching request comes in.

## How User Skills Work

1. **User defines the skill** — gives it a name, description (trigger phrases), and instructions
2. **CrucibAI saves it** — stored in the user's skill library, linked to their account
3. **Auto-applied** — when a future request matches the skill's trigger phrases, CrucibAI loads and applies the instructions
4. **Editable** — users can update, deactivate, or delete their skills at any time

## Skill Template Structure

When creating a custom skill, provide:

**Name** — Short, descriptive (e.g., "brand-voice-enforcer", "company-stack-builder")

**Description / Trigger** — When should this skill activate? Include specific trigger phrases.
Example: "Use when the user asks to build anything for Acme Corp, or mentions our stack (React + Supabase + Railway). Always use our design system."

**Instructions** — What should CrucibAI do differently?
- Technology preferences (always use X, never use Y)
- Design system rules (colors, fonts, component patterns)
- Business context (company name, industry, target users)
- Code style preferences (tabs vs spaces, naming conventions)
- Output format preferences

**Examples** — Optional: sample input → expected output pairs

## Example Custom Skills

### Company Tech Stack Skill
```
Name: my-company-stack
Trigger: Any build request for our company
Instructions:
- Always use: Next.js 14, Supabase, Tailwind CSS, TypeScript, Vercel
- Never use: Create React App, MongoDB, styled-components
- Design system: primary color #FF6B6B, font Inter, border-radius 8px
- Auth: always use Supabase Auth, not custom JWT
- Database: use Supabase client, not raw SQL
```

### Brand Voice Skill
```
Name: startup-brand-voice
Trigger: Writing copy, landing pages, or any user-facing text
Instructions:
- Tone: confident but approachable, avoid corporate jargon
- We are "you" not "one", "we" not "the company"
- Headlines: action-oriented, present tense
- Avoid: "leverage", "utilize", "synergy", "holistic"
- Always include: social proof, specific numbers over vague claims
```

### Domain-Specific Skill
```
Name: healthcare-builder
Trigger: Building anything for healthcare, medical, or patient management
Instructions:
- Always include HIPAA compliance notices
- Patient data fields must be PHI-aware (mask in logs)
- Include access audit logging for all data reads
- Use healthcare-appropriate terminology
- Include data retention policy in README
```

## How CrucibAI Applies Custom Skills

When a user request matches a skill's trigger:
1. Load the skill instructions into the agent's system context
2. Apply any technology constraints (override default choices)
3. Apply any style/tone/content rules
4. Use any custom examples as reference
5. Note which skill was applied in the build output

## Instructions for This Template

When a user asks to create a custom skill:
1. Ask for: skill name, when it should trigger, what it should change about the build output
2. Write the SKILL.md following the structure above
3. Save it to the user's skill library
4. Confirm: "Skill '[name]' saved. CrucibAI will apply it automatically when [trigger description]."
5. Offer to test it: "Want to try a build with this skill active now?"
