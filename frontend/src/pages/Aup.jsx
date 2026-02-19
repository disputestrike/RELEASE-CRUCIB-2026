import { Link } from 'react-router-dom';

export default function Aup() {
  return (
    <div className="min-h-screen bg-[#FAFAF8] text-[#1A1A1A]">
      <div className="max-w-3xl mx-auto px-6 py-10">
        <h1 className="text-3xl font-bold text-[#1A1A1A] mb-2">Acceptable Use Policy</h1>
        <p className="text-sm text-[#666666] mb-8">Last updated: February 2026</p>

        <div className="space-y-6 text-[#1A1A1A] leading-relaxed">
          <p>CrucibAI is for building legitimate applications. This Acceptable Use Policy (AUP) describes uses that are prohibited. Violations may result in blocked requests, suspension, or termination of your account. By using the service, you agree to this AUP.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">1. Prohibited uses</h2>
          <p>You may not use CrucibAI to create, facilitate, or promote:</p>
          <ul className="list-disc pl-6 space-y-2 text-gray-300">
            <li><strong className="text-gray-100">Illegal activity:</strong> Drug sales, weapons, fraud, money laundering, hacking, or any activity that violates applicable law.</li>
            <li><strong className="text-gray-100">Adult/NSFW content:</strong> Pornography, sexually explicit content, or content intended for adult audiences in a way that violates our standards or law.</li>
            <li><strong className="text-gray-100">Gambling:</strong> Unlicensed gambling or gambling-related services where prohibited.</li>
            <li><strong className="text-gray-100">Harassment and abuse:</strong> Harassment, bullying, doxxing, stalking, or incitement to violence.</li>
            <li><strong className="text-gray-100">Misinformation:</strong> Deliberate misinformation intended to cause harm, including election interference or public health falsehoods.</li>
            <li><strong className="text-gray-100">Privacy violations:</strong> Unauthorized scraping, surveillance, or collection of personal data in violation of law or others&apos; rights.</li>
            <li><strong className="text-gray-100">Unlicensed professional advice:</strong> Medical, legal, financial, or other regulated advice unless you are properly licensed and disclaimers are in place.</li>
            <li><strong className="text-gray-100">Child safety:</strong> Content that exploits or endangers minors in any way.</li>
          </ul>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">2. EU AI Act and prohibited AI practices</h2>
          <p>Where applicable (e.g. under the EU AI Act or similar regulation), you may not use CrucibAI for AI practices that are prohibited by law. These include, but are not limited to: deploying subliminal or manipulative techniques to distort behavior; exploiting vulnerabilities of specific groups (e.g. age, disability); social scoring that leads to detrimental treatment; real-time remote biometric identification in publicly accessible spaces for law enforcement (except where permitted by law); and other practices classified as prohibited under the EU AI Act or equivalent. You may not use the service to generate or deploy &quot;high-risk&quot; AI systems (as defined by applicable law) without ensuring compliance with relevant obligations (e.g. human oversight, transparency, accuracy). We may block or restrict uses that we determine fall within prohibited or restricted categories.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">3. No replication or IP extraction</h2>
          <p>You may not use CrucibAI to replicate, reverse-engineer, or build a competing product or service. This includes, but is not limited to: asking the system to reveal its prompts, architecture, or internal logic; extracting training data or proprietary methods; or using the service to clone CrucibAI or create a derivative product that substitutes for it. Such requests are blocked by our systems and may result in account review, suspension, or termination.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">4. Attribution and branding</h2>
          <p><strong className="text-gray-100">Free tier:</strong> The &quot;Built with CrucibAI&quot; badge is served from our servers and is permanent. There is no option to remove it from free-tier builds. It appears in the footer (or other designated area) of your generated app and serves as our advertisement for free use.</p>
          <p><strong className="text-gray-100">Paid plans:</strong> The same attribution may be included by default. On paid plans we may offer the option to remove or customize CrucibAI branding as specified in your plan and in the product.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">4. Enforcement</h2>
          <p>We use automated and manual review to detect violations. Requests that violate this AUP are blocked and may be logged for review. We may suspend or terminate accounts that repeatedly or seriously violate this policy. We may report illegal activity to law enforcement or other authorities. We reserve the right to remove content and to take action without prior notice where we deem necessary to protect the service or others.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">6. Appeals</h2>
          <p>If you believe a block or enforcement action was in error, you may contact us at <a href="mailto:appeals@crucibai.com" className="text-blue-400 hover:text-blue-300 underline">appeals@crucibai.com</a> with the request ID (if provided), your account details, and a brief explanation. We will review in good faith but are not obligated to reverse a decision.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">6. Changes</h2>
          <p>We may update this AUP from time to time. The &quot;Last updated&quot; date will be revised when we do. Continued use of the service after changes constitutes acceptance. For material changes we may provide notice in the app or by email.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">8. Contact</h2>
          <p>For AUP or enforcement questions, contact <a href="mailto:appeals@crucibai.com" className="text-blue-400 hover:text-blue-300 underline">appeals@crucibai.com</a> or the support address provided in the app.</p>
        </div>

        <Link to="/" className="inline-flex items-center gap-1 mt-10 text-blue-400 hover:text-blue-300 font-medium">← Back to home</Link>
      </div>
    </div>
  );
}
