import { Link } from 'react-router-dom';

export default function Cookies() {
  return (
    <div className="min-h-screen bg-[#FAFAF8] text-[#1A1A1A]">
      <div className="max-w-3xl mx-auto px-6 py-10">
        <h1 className="text-3xl font-bold text-[#1A1A1A] mb-2">Cookie Policy</h1>
        <p className="text-sm text-gray-600 mb-8">Last updated: February 2026</p>

        <div className="space-y-6 text-[#1A1A1A] leading-relaxed">
          <p>This Cookie Policy explains how CrucibAI uses cookies and similar technologies when you use our website and service. It should be read together with our <Link to="/privacy" className="text-gray-500 hover:text-gray-500 underline">Privacy Policy</Link>. Where required by law (e.g. GDPR, ePrivacy), we obtain your consent for non-essential cookies before use.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">1. What are cookies?</h2>
          <p>Cookies are small text files stored on your device when you visit a website. They are widely used to make sites work, remember your preferences, and understand how the site is used. We also use similar technologies such as local storage and session storage where relevant.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">2. How we use cookies</h2>
          <p><strong className="text-gray-100">Strictly necessary (essential):</strong> These are required for the service to function. They include, for example, authentication and session cookies so you stay logged in, and security-related cookies. We do not need your consent for these under applicable law.</p>
          <p><strong className="text-gray-100">Functional:</strong> These remember your preferences (e.g. theme, language) and improve your experience. They may be essential or subject to consent depending on jurisdiction.</p>
          <p><strong className="text-gray-100">Analytics and performance:</strong> We may use first- or third-party analytics to understand how the service is used (e.g. page views, feature usage). Where required (e.g. GDPR), we only use these with your consent. You can control or opt out via cookie settings or your browser.</p>
          <p><strong className="text-gray-100">Marketing (if any):</strong> If we use cookies for marketing or advertising, we will do so only with your consent where required by law.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">3. Duration</h2>
          <p>Session cookies are deleted when you close your browser. Persistent cookies remain for a set period (e.g. until expiry or until you delete them). We will specify retention in our cookie list or in the cookie banner/settings.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">4. Your choices</h2>
          <p>You can control cookies through your browser settings (e.g. block or delete cookies). Note that blocking essential cookies may prevent the service from working properly. Where we use a cookie consent mechanism (e.g. in the EU), you can accept or reject non-essential categories there.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">5. Third-party cookies</h2>
          <p>Third-party services we use (e.g. analytics, payment, or support widgets) may set their own cookies. Their use is governed by their respective privacy and cookie policies. We encourage you to review those policies.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">6. Updates</h2>
          <p>We may update this Cookie Policy from time to time. We will post the revised policy and update the &quot;Last updated&quot; date. Where required by law, we may ask for your consent again for material changes.</p>

          <h2 className="text-xl font-semibold text-[#1A1A1A] mt-8 mb-3">7. Contact</h2>
          <p>For questions about our use of cookies, contact us at the support or privacy address provided in the app or on our website.</p>
        </div>

        <Link to="/" className="inline-flex items-center gap-1 mt-10 text-gray-500 hover:text-gray-500 font-medium">← Back to home</Link>
      </div>
    </div>
  );
}
