import { Link } from 'react-router-dom';
import PublicNav from '../components/PublicNav';

export default function Security() {
  return (
    <div className="min-h-screen bg-[#FAFAF8] text-[#1A1A1A]">
      <PublicNav />
      <div className="max-w-3xl mx-auto px-6 py-10">
        <h1 className="text-3xl font-bold text-[#1A1A1A] mb-2">Security &amp; Trust</h1>
        <p className="text-sm text-[#666666] mb-6">How we keep the platform and your code safe.</p>

        <div className="p-6 rounded-xl border border-indigo-200 bg-indigo-50 mb-10">
          <p className="text-indigo-900 font-medium">We prove builds before we call them ready.</p>
          <p className="text-[#666666] text-sm mt-2">The current full systems release gate includes tenant-isolation checks, late-stage pipeline crash tests, provider readiness tests, automation bridge tests, Railway smoke, a live golden path, public trust preflight, and a 50-prompt repeatability benchmark.</p>
        </div>

        <div className="space-y-6 text-[#1A1A1A] leading-relaxed">
          <p>CrucibAI is built with security in mind. This page summarizes how we protect the platform and how we help you secure what you build.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">Platform security</h2>
          <ul className="list-disc pl-6 space-y-2 text-[#333]">
            <li><strong className="text-[#1A1A1A]">Authentication:</strong> Passwords hashed with bcrypt; JWT for sessions; optional MFA (TOTP). We never return passwords or hashes in API responses.</li>
            <li><strong className="text-[#1A1A1A]">Secrets:</strong> API keys and webhook secrets are stored securely. We do not expose webhook secrets in list endpoints. Stripe webhooks are verified by signature.</li>
            <li><strong className="text-[#1A1A1A]">Rate limiting:</strong> Requests are rate-limited per user and IP to prevent abuse.</li>
            <li><strong className="text-[#1A1A1A]">Security headers:</strong> We send headers such as X-Content-Type-Options, X-Frame-Options, HSTS, Content-Security-Policy, and Referrer-Policy to reduce XSS and related risks.</li>
            <li><strong className="text-[#1A1A1A]">HTTPS:</strong> Use HTTPS in production; we send Strict-Transport-Security so browsers enforce TLS.</li>
            <li><strong className="text-[#1A1A1A]">Database:</strong> PostgreSQL is the primary system of record; MongoDB references are treated as documentation drift.</li>
            <li><strong className="text-[#1A1A1A]">Terminal:</strong> Terminal access is project-scoped, command-audited, and launch-gated. Broad public host-shell exposure remains blocked until sandbox boundaries are complete.</li>
            <li><strong className="text-[#1A1A1A]">Generated-code sandbox:</strong> Generated code uses the sandbox executor with timeout, output, file-size, memory, CPU, and process limits before public terminal exposure is considered.</li>
            <li><strong className="text-[#1A1A1A]">Community templates:</strong> Launch templates are curated and moderation-gated before public listing.</li>
            <li><strong className="text-[#1A1A1A]">Payments:</strong> We use Stripe for payments. Card data is handled by Stripe; we do not store full card numbers.</li>
          </ul>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">Your code and projects</h2>
          <p>When you build with us or bring existing code:</p>
          <ul className="list-disc pl-6 space-y-2 text-[#333]">
            <li><strong className="text-[#1A1A1A]">Security scan:</strong> In the Workspace you can run a <strong className="text-[#1A1A1A]">Security scan</strong> on your code. We return a short checklist (e.g. no secrets in client code, auth on API) so you can fix issues before deploy.</li>
            <li><strong className="text-[#1A1A1A]">Accessibility check:</strong> Run an <strong className="text-[#1A1A1A]">Accessibility check</strong> for labels, contrast, keyboard, and ARIA. Use it for code you build here or code you import.</li>
            <li><strong className="text-[#1A1A1A]">Validate-and-fix:</strong> Use <strong className="text-[#1A1A1A]">Validate-and-fix</strong> to catch syntax and common errors and get suggested fixes.</li>
          </ul>
          <p className="text-[#333] text-sm">We do not scan or modify your code without you triggering these actions. You own your code and data.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">Public generated apps</h2>
          <p>Completed generated apps can be served from a public CrucibAI URL at <code>/published/&lbrace;job_id&rbrace;/</code> once build proof has produced a previewable bundle. External provider adapters remain separate deploy work.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">Fraud and abuse prevention</h2>
          <p>We block disposable email addresses at signup and cap referral rewards to reduce abuse. Credits are enforced so usage is tied to your account and plan.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">Reporting a security issue</h2>
          <p>If you believe you have found a security vulnerability in CrucibAI, please report it to us responsibly. Do not disclose it publicly before we have had a chance to address it. Contact: <a href="mailto:security@crucibai.com" className="text-[#1A1A1A] hover:text-[#333] underline">security@crucibai.com</a> (or the contact listed in your Terms/Privacy). We will acknowledge and work with you to resolve the issue.</p>

          <p className="mt-8 text-[#666666] text-sm">
            For privacy and data handling, see our <Link to="/privacy" className="text-[#1A1A1A] hover:text-[#333] underline">Privacy Policy</Link>. For terms of use, see our <Link to="/terms" className="text-[#1A1A1A] hover:text-[#333] underline">Terms of Use</Link>.
          </p>
        </div>
      </div>
    </div>
  );
}
