/**
 * Power-user / internal tools — surfaced in Settings → Engine room
 * (previously expanded in sidebar “Engine Room”.)
 */
import {
  Sparkles, Bot, BookOpen, Library, Radio, MessageSquare, ShoppingBag, Users,
  FileOutput, FileText, LayoutGrid, HelpCircle, Key, Keyboard,
  CreditCard, ScrollText, BarChart3, Zap, ShieldCheck, Code, Monitor,
  PlayCircle, Coins, Store,
} from 'lucide-react';

export const ENGINE_ROOM_ITEMS = [
  { label: 'Skills', icon: Sparkles, href: '/app/skills' },
  { label: 'Marketplace', icon: Store, href: '/app/skills/marketplace' },
  { label: 'Studio', icon: Bot, href: '/app/studio', beta: true },
  { label: 'Knowledge', icon: BookOpen, href: '/app/knowledge', beta: true },
  { label: 'Channels', icon: Radio, href: '/app/channels', beta: true },
  { label: 'Sessions', icon: MessageSquare, href: '/app/sessions', beta: true },
  { label: 'Commerce', icon: ShoppingBag, href: '/app/commerce', beta: true },
  { label: 'Members', icon: Users, href: '/app/members', beta: true },
  { label: 'Credit Center', icon: Coins, href: '/app/tokens' },
  { label: 'Exports', icon: FileOutput, href: '/app/exports' },
  { label: 'Docs / Slides / Sheets', icon: FileText, href: '/app/generate' },
  { label: 'Patterns', icon: Library, href: '/app/patterns' },
  { label: 'Templates', icon: LayoutGrid, href: '/app/templates' },
  { label: 'Prompt Library', icon: BookOpen, href: '/app/prompts' },
  { label: 'Learn', icon: HelpCircle, href: '/app/learn' },
  { label: 'Env', icon: Key, href: '/app/env' },
  { label: 'Shortcuts', icon: Keyboard, href: '/app/shortcuts' },
  { label: 'Benchmarks', icon: BarChart3, href: '/benchmarks' },
  { label: 'Add Payments', icon: CreditCard, href: '/app/payments-wizard' },
  { label: 'Audit Log', icon: ScrollText, href: '/app/audit-log' },
  { label: 'Model Manager', icon: BarChart3, href: '/app/models' },
  { label: 'Fine-Tuning', icon: Zap, href: '/app/fine-tuning', beta: true },
  { label: 'Safety Dashboard', icon: ShieldCheck, href: '/app/safety', beta: true },
  { label: 'Runs', icon: BarChart3, href: '/app/monitoring' },
  { label: 'Auto-Runner', icon: PlayCircle, href: '/app/workspace' },
  { label: 'VibeCode', icon: Code, href: '/app/vibecode', beta: true },
  { label: 'IDE', icon: Monitor, href: '/app/ide', beta: true },
];
