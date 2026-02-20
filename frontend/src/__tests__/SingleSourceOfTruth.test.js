/**
 * Master Single Source of Truth tests (MASTER_SINGLE_SOURCE_OF_TRUTH_TEST.md).
 * §1.1 Routes resolve, §1.2 API base, §1.4 Pricing ↔ TokenCenter wiring.
 */
const fs = require('fs');
const path = require('path');

describe('Single Source of Truth', () => {
  describe('§1.2 API base', () => {
    it('App.js defines API and points to /api or backend URL', () => {
      const appPath = path.join(__dirname, '../App.js');
      const source = fs.readFileSync(appPath, 'utf8');
      expect(source).toMatch(/export const API = /);
      expect(source).toMatch(/\/api/);
      expect(source).toMatch(/REACT_APP_BACKEND_URL|BACKEND_URL/);
    });
  });

  describe('§1.1 Route components exist', () => {
    it('all public and app route component files exist', () => {
      const pagesDir = path.join(__dirname, '../pages');
      const componentsDir = path.join(__dirname, '../components');
      const files = [
        'LandingPage.jsx', 'AuthPage.jsx', 'Pricing.jsx', 'TemplatesPublic.jsx', 'LearnPublic.jsx',
        'TokenCenter.jsx', 'Features.jsx', 'Enterprise.jsx', 'Dashboard.jsx', 'Workspace.jsx',
      ];
      const missing = files.filter((f) => !fs.existsSync(path.join(pagesDir, f)));
      expect(missing).toEqual([]);
      expect(fs.existsSync(path.join(componentsDir, 'Layout.jsx'))).toBe(true);
    });
    it('App.js declares all critical routes', () => {
      const appPath = path.join(__dirname, '../App.js');
      const source = fs.readFileSync(appPath, 'utf8');
      expect(source).toMatch(/path="\/" element=.*LandingPage/);
      expect(source).toMatch(/path="\/pricing" element=.*Pricing/);
      expect(source).toMatch(/path="\/app".*Layout/);
      expect(source).toMatch(/path="tokens" element=.*TokenCenter/);
    });
  });

  describe('§1.4 Pricing → TokenCenter wiring (source contract)', () => {
    it('Pricing page source navigates to /app/tokens with state.addon when user and addon button', () => {
      const pricingPath = path.join(__dirname, '../pages/Pricing.jsx');
      const source = fs.readFileSync(pricingPath, 'utf8');
      expect(source).toMatch(/state:\s*\{\s*addon:\s*key\s*\}/);
      expect(source).toMatch(/\/app\/tokens/);
    });
    it('Pricing page source uses redirect with addon query when not logged in', () => {
      const pricingPath = path.join(__dirname, '../pages/Pricing.jsx');
      const source = fs.readFileSync(pricingPath, 'utf8');
      expect(source).toMatch(/redirect.*addon/);
      expect(source).toMatch(/\/app\/tokens\?addon=/);
    });
    it('TokenCenter source reads addon from location.state or searchParams', () => {
      const tokenPath = path.join(__dirname, '../pages/TokenCenter.jsx');
      const source = fs.readFileSync(tokenPath, 'utf8');
      expect(source).toMatch(/location\.state\?\.addon/);
      expect(source).toMatch(/searchParams\.get\(['"]addon['"]\)/);
      expect(source).toMatch(/addonFromPricing/);
    });
  });

  describe('§2.1 Two-color system (public pages no orange)', () => {
    const publicPages = ['Pricing.jsx', 'LandingPage.jsx', 'LearnPublic.jsx', 'TemplatesPublic.jsx', 'AuthPage.jsx', 'Features.jsx', 'PublicNav.jsx', 'PublicFooter.jsx'];
    it('public marketing pages do not use orange (orange-*, #f97316)', () => {
      const pagesDir = path.join(__dirname, '../pages');
      const componentsDir = path.join(__dirname, '../components');
      const orangePattern = /orange-\d+|#f97316|from-orange|to-orange|border-orange|bg-orange|text-orange/;
      const violations = [];
      publicPages.forEach((f) => {
        const dir = f.includes('Nav') || f.includes('Footer') ? componentsDir : pagesDir;
        const p = path.join(dir, f);
        if (fs.existsSync(p)) {
          const source = fs.readFileSync(p, 'utf8');
          if (orangePattern.test(source)) violations.push(f);
        }
      });
      expect(violations).toEqual([]);
    });
  });
});
