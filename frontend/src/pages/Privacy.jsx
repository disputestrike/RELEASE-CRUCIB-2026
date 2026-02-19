import { Link } from 'react-router-dom';


export default function Privacy() {
  return (
    <div className="min-h-screen bg-[#FAFAF8] text-[#1A1A1A]">
      <div className="max-w-3xl mx-auto px-6 py-10">
        <h1 className="text-3xl font-bold text-[#1A1A1A] mb-2">Privacy Policy</h1>
        <p className="text-sm text-[#666666] mb-8">Last updated: February 2026</p>

        <div className="space-y-6 text-[#1A1A1A] leading-relaxed">
          <p>CrucibAI (&quot;we,&quot; &quot;our,&quot; or &quot;us&quot;) respects your privacy. This Privacy Policy describes what data we collect, how we use it, your rights, and how we comply with applicable law including the EU General Data Protection Regulation (GDPR), UK GDPR, the California Consumer Privacy Act (CCPA) as amended by the CPRA, and other data protection laws. By using our service, you agree to this policy.</p>
          <p className="text-gray-300 text-sm">
            <strong className="text-gray-100">For content-safety and prohibited uses,</strong> see our <Link to="/aup" className="text-blue-400 hover:text-blue-300 underline">Acceptable Use Policy</Link>. <strong className="text-gray-100">For terms of use and prohibited AI practices,</strong> see our <Link to="/terms" className="text-blue-400 hover:text-blue-300 underline">Terms of Use</Link>.
          </p>
          <p className="text-gray-300 text-sm">
            <strong className="text-gray-100">NOTICE TO EUROPEAN USERS:</strong> If you are in the European Economic Area or the United Kingdom, see <strong className="text-gray-100">Section 2 (Legal basis)</strong> and <strong className="text-gray-100">Section 10 (Your rights GDPR / UK GDPR)</strong> below for additional information.
          </p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">1. Data we collect</h2>
          <p><strong className="text-gray-100">Account data.</strong> When you register, we collect your email address, name, and password (stored in hashed form). We use this to create and manage your account, authenticate you, and communicate with you.</p>
          <p><strong className="text-gray-100">Project and build data.</strong> We store the projects you create, prompts you submit, generated code and assets, and build logs. This data is used to provide the service, improve quality, and support you.</p>
          <p><strong className="text-gray-100">Usage and billing.</strong> We record token consumption, credit usage, feature usage, and billing-related events to operate the platform, enforce limits, and process payments.</p>
          <p><strong className="text-gray-100">Device and log data.</strong> We may collect IP address, browser type, and similar technical data in server logs and for security and abuse prevention.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">2. Legal basis (GDPR / UK GDPR)</h2>
          <p>If you are in the European Economic Area (EEA) or the United Kingdom, we process your personal data on the following legal bases:</p>
          <ul className="list-disc pl-6 space-y-2 text-gray-300">
            <li><strong className="text-gray-100">Contract (Art. 6(1)(b)):</strong> Performance of our contract with you (account, service delivery, billing).</li>
            <li><strong className="text-gray-100">Legitimate interests (Art. 6(1)(f)):</strong> Security, fraud prevention, abuse detection, improvement of the service, analytics (where not overridden by your rights).</li>
            <li><strong className="text-gray-100">Legal obligation (Art. 6(1)(c)):</strong> Compliance with law (e.g. tax, anti-money laundering, responding to lawful requests).</li>
            <li><strong className="text-gray-100">Consent (Art. 6(1)(a)):</strong> Where we ask for your consent (e.g. marketing, optional features); you may withdraw consent at any time.</li>
          </ul>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">3. How we use your data</h2>
          <p>We use the data above to: provide, maintain, and improve CrucibAI; process transactions; send service-related and security notices; respond to support requests; detect and prevent fraud and abuse; and comply with legal obligations.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">4. API keys and third-party providers</h2>
          <p>If you add API keys in Settings (e.g. for OpenAI, Anthropic, or deployment platforms), we store them securely and use them only to perform actions on your behalf. We do not share your API keys with third parties except as necessary to provide the service. Use of those providers is subject to their respective privacy policies. We act as a data controller for your account data; where we use subprocessors (hosting, AI providers, payment processors), we ensure appropriate contracts and safeguards are in place.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">5. International transfers</h2>
          <p>Your data may be processed in the United States or other countries where we or our subprocessors operate. Where we transfer personal data from the EEA or UK to a country not recognized as providing adequate protection, we implement appropriate safeguards (e.g. Standard Contractual Clauses approved by the European Commission or UK equivalents, or other mechanisms permitted by law). You may request details of the safeguards we use by contacting us.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">6. Data retention</h2>
          <p>We retain your account, project, and usage data for as long as your account is active and as needed to fulfill the purposes described in this policy or as required by law. You may request deletion of your personal data or full account by contacting support; we will process such requests in accordance with applicable law (including GDPR Art. 17 right to erasure where applicable).</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">7. Sharing and disclosure</h2>
          <p>We do not sell your personal data. We may share data with service providers (subprocessors) who assist in operating our platform (e.g. hosting, analytics, payment processors, AI providers) under contractual obligations to protect your data. We may disclose data when required by law, to protect our rights or safety, or in connection with a merger or sale of assets. For enterprise customers, we may offer a Data Processing Agreement (DPA) and subprocessor list upon request.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">8. Cookies and similar technologies</h2>
          <p>We use cookies and similar technologies (e.g. local storage) to: keep you logged in (session/authentication); remember your preferences; and operate the service. We may use analytics cookies to understand how the service is used (we may use first- or third-party tools). You can control cookies through your browser settings. Essential cookies are necessary for the service to function; disabling them may limit functionality. Where required by law (e.g. GDPR), we obtain consent for non-essential cookies before use. For more detail, see our <Link to="/cookies" className="text-blue-400 hover:text-blue-300 underline">Cookie Policy</Link>.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">9. Children and minors (COPPA / under-16)</h2>
          <p>Our service is not directed to children under 16 (or under 13 in the United States, in line with COPPA). We do not knowingly collect personal data from children. If you are under 16 (or 13 in the US), do not register or provide personal data. If we learn that we have collected personal data from a child without parental consent, we will delete it promptly. If you believe we have collected a child&apos;s data in error, contact us immediately.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">10. Your rights (GDPR / UK GDPR)</h2>
          <p>If you are in the EEA or UK, you have the following rights regarding your personal data:</p>
          <ul className="list-disc pl-6 space-y-2 text-gray-300">
            <li><strong className="text-gray-100">Access (Art. 15):</strong> Request a copy of your personal data we hold.</li>
            <li><strong className="text-gray-100">Rectification (Art. 16):</strong> Request correction of inaccurate or incomplete data.</li>
            <li><strong className="text-gray-100">Erasure (Art. 17):</strong> Request deletion of your data in certain circumstances.</li>
            <li><strong className="text-gray-100">Restriction (Art. 18):</strong> Request that we limit processing in certain circumstances.</li>
            <li><strong className="text-gray-100">Data portability (Art. 20):</strong> Request a copy of your data in a structured, machine-readable format where applicable.</li>
            <li><strong className="text-gray-100">Object (Art. 21):</strong> Object to processing based on legitimate interests or for direct marketing.</li>
            <li><strong className="text-gray-100">Withdraw consent:</strong> Where processing is based on consent, you may withdraw it at any time.</li>
            <li><strong className="text-gray-100">Complaint:</strong> You have the right to lodge a complaint with a supervisory authority in your country (e.g. your national data protection authority).</li>
          </ul>
          <p>To exercise any of these rights, contact us at the support or privacy contact address provided in the app or on our website. We will respond within the timeframes required by applicable law (e.g. one month under GDPR, extendable where necessary).</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">11. California and other US state privacy rights (CCPA / CPRA)</h2>
          <p>If you are a California resident, you may have the right to: know what personal information we collect, use, and disclose; request deletion of your personal information; correct inaccuracies; opt out of the &quot;sale&quot; or &quot;sharing&quot; of your personal information (we do not sell or share personal information for cross-context behavioral advertising as defined under CCPA); and non-discrimination for exercising your rights. To submit a request, contact us at the support or privacy address. We may need to verify your identity. You may designate an authorized agent to make a request on your behalf where permitted by law. Other US states may provide similar rights (e.g. access, deletion, opt-out); we will honor them in accordance with applicable state law.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">12. Data Protection Officer (DPO) and EU/UK contact</h2>
          <p>For questions about data protection, GDPR/UK GDPR, or to exercise your rights, you may contact our Data Protection Officer or privacy team at the legal or privacy contact address provided in the app or on our website. If we have an EU or UK representative, their contact details will be listed on our website or in the app.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">13. Security</h2>
          <p>We use industry-standard measures to protect your data, including encryption in transit and at rest, access controls, and secure storage of credentials. You are responsible for keeping your password and API keys confidential. No method of transmission or storage is 100% secure; we cannot guarantee absolute security.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">14. Changes</h2>
          <p>We may update this Privacy Policy from time to time. We will post the revised policy and update the &quot;Last updated&quot; date. For material changes that affect how we use your data, we may provide additional notice (e.g. email or in-app). Continued use of the service after changes constitutes acceptance. Where required by law (e.g. GDPR), we may seek your consent for material changes.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">15. Contact</h2>
          <p>For privacy questions, to exercise your rights, or for DPA requests: contact us at the support or legal contact address provided in the app or on our website (e.g. privacy@crucibai.com or legal@crucibai.com).</p>
        </div>

        <Link to="/" className="inline-flex items-center gap-1 mt-10 text-blue-400 hover:text-blue-300 font-medium">← Back to home</Link>
      </div>
    </div>
  );
}
