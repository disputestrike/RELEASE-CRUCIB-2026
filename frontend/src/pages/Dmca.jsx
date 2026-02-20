import { Link } from 'react-router-dom';

export default function Dmca() {
  return (
    <div className="min-h-screen bg-[#FAFAF8] text-[#1A1A1A]">
      <div className="max-w-3xl mx-auto px-6 py-10">
        <h1 className="text-3xl font-bold text-[#1A1A1A] mb-2">DMCA & Copyright Policy</h1>
        <p className="text-sm text-[#666666] mb-8">Last updated: February 2026</p>

        <div className="space-y-6 text-[#1A1A1A] leading-relaxed">
          <p>CrucibAI respects intellectual property and complies with the Digital Millennium Copyright Act (DMCA) and other applicable copyright laws. This policy explains how we handle claims of copyright infringement and how you may submit a takedown notice or counter-notice.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">1. Takedown notices</h2>
          <p>If you are a copyright owner or authorized to act on their behalf and believe that content generated, hosted, or made available through CrucibAI infringes your copyright, you may submit a DMCA takedown notice. Your notice must be sent to <a href="mailto:dmca@crucibai.com" className="text-orange-400 hover:text-orange-300 underline">dmca@crucibai.com</a> and must include:</p>
          <ul className="list-disc pl-6 space-y-2 text-gray-300">
            <li>Your full name, address, telephone number, and email address.</li>
            <li>A description of the copyrighted work you believe has been infringed.</li>
            <li>The URL or other specific location of the allegedly infringing material on our service.</li>
            <li>A statement that you have a good-faith belief that use of the material is not authorized by the copyright owner, its agent, or the law.</li>
            <li>A statement, under penalty of perjury, that the information in the notice is accurate and that you are authorized to act on behalf of the copyright owner.</li>
            <li>Your physical or electronic signature.</li>
          </ul>
          <p>We will process valid notices promptly and may remove or disable access to the material in question. We may forward your notice to the user who posted the content and/or to third parties as required by law.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">2. Counter-notice</h2>
          <p>If your content was removed or disabled as a result of a DMCA notice and you believe the removal was mistaken or that you have the right to use the material, you may submit a counter-notice. Your counter-notice must be sent to <a href="mailto:dmca@crucibai.com" className="text-orange-400 hover:text-orange-300 underline">dmca@crucibai.com</a> and must include:</p>
          <ul className="list-disc pl-6 space-y-2 text-gray-300">
            <li>Your name, address, telephone number, and email address.</li>
            <li>Identification of the material that was removed or disabled and the location where it appeared before removal.</li>
            <li>A statement under penalty of perjury that you have a good-faith belief the material was removed or disabled as a result of mistake or misidentification.</li>
            <li>Consent to the jurisdiction of the federal court in your district (or if outside the U.S., any judicial district in which CrucibAI may be found) and that you will accept service of process from the person who submitted the original notice or their agent.</li>
            <li>Your physical or electronic signature.</li>
          </ul>
          <p>If we receive a valid counter-notice, we may forward it to the original claimant. The claimant may then file a court action. If we do not receive notice that a lawsuit has been filed within 10–14 business days, we may restore the content.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">3. Repeat infringers</h2>
          <p>We may terminate, in appropriate circumstances, the accounts of users who are repeat infringers. We also reserve the right to terminate accounts that we determine, in our sole discretion, have engaged in serious or repeated infringement.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">4. Misrepresentation</h2>
          <p>Under the DMCA, any person who knowingly materially misrepresents that material is infringing, or that material was removed or disabled by mistake, may be liable for damages. We may seek damages and other remedies to the fullest extent permitted by law.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">5. Contact</h2>
          <p>For all DMCA and copyright-related inquiries, contact us at <a href="mailto:dmca@crucibai.com" className="text-orange-400 hover:text-orange-300 underline">dmca@crucibai.com</a>.</p>
        </div>

        <Link to="/" className="inline-flex items-center gap-1 mt-10 text-orange-400 hover:text-orange-300 font-medium">← Back to home</Link>
      </div>
    </div>
  );
}
