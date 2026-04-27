import { Link } from 'react-router-dom';

export default function About() {
  return (
    <div className="min-h-screen bg-[#FAFAF8] text-[#1A1A1A]">
      <div className="max-w-3xl mx-auto px-6 py-10">
        <h1 className="text-3xl font-bold text-[#1A1A1A] mb-2">About CrucibAI — Inevitable AI</h1>
        <p className="text-sm text-gray-600 mb-8">Last updated: February 2026</p>

        <div className="space-y-6 text-[#1A1A1A] leading-relaxed">
          <p>CrucibAI is Inevitable AI: the platform where intelligence doesn&apos;t just act, it makes outcomes inevitable. We help developers and teams plan, build, and ship applications using a swarm of agents and sub-agents—plan-first, full transparency, and validator-gated code.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">What we do</h2>
          <p>We provide a plan-first build experience: you describe what you want, and our agent swarm handles planning, frontend and backend generation, database design, testing, images and videos, and deployment guidance. You get code you own, proof artifacts, target-specific validator gates, and full control to edit and extend your project.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">For everyone</h2>
          <p>CrucibAI is built for individuals, startups, and enterprises. Whether you&apos;re prototyping an idea, building a side project, or scaling a product team, our platform is designed to be flexible and compliant with modern security and legal standards—including GDPR, CCPA, and AI governance where applicable.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">Legal and policies</h2>
          <p>For how we collect and use your data, see our <Link to="/privacy" className="text-[#1A1A1A] hover:text-[#333] underline">Privacy Policy</Link>. For content-safety and prohibited uses, see our <Link to="/aup" className="text-[#1A1A1A] hover:text-[#333] underline">Acceptable Use Policy</Link>. For terms of use, see our <Link to="/terms" className="text-[#1A1A1A] hover:text-[#333] underline">Terms of Use</Link>. For copyright and DMCA, see our <Link to="/dmca" className="text-[#1A1A1A] hover:text-[#333] underline">DMCA & Copyright Policy</Link>. To manage cookies, see our <Link to="/cookies" className="text-[#1A1A1A] hover:text-[#333] underline">Cookie Policy</Link>.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">Contact</h2>
          <p>For general inquiries, support, or enterprise sales, use the contact options provided in the app or on our website (e.g. support@crucibai.com, or the Enterprise contact form). For privacy or legal requests, see the contact section in our Privacy Policy or Terms.</p>
        </div>

        <div className="mt-10 flex flex-wrap gap-4">
          <Link to="/" className="inline-flex items-center gap-1 text-[#1A1A1A] hover:text-[#333] font-medium">← Back to home</Link>
          <Link to="/pricing" className="inline-flex items-center gap-1 text-[#1A1A1A] hover:text-[#333] font-medium">Pricing</Link>
          <Link to="/enterprise" className="inline-flex items-center gap-1 text-[#1A1A1A] hover:text-[#333] font-medium">Enterprise</Link>
        </div>
      </div>
    </div>
  );
}
