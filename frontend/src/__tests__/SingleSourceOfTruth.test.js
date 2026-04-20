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
        'TokenCenter.jsx', 'Features.jsx', 'Enterprise.jsx', 'Dashboard.jsx', 'DashboardVNext.jsx', 'UnifiedWorkspace.jsx', 'WorkspaceVNext.jsx', 'CrucibAIWorkspace.jsx',
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
      expect(source).toMatch(/path="dashboard" element=.*DashboardVNext/);
      expect(source).toMatch(/path="workspace" element=.*WorkspaceVNext|path="\/app\/workspace" element=.*WorkspaceVNext/);
      expect(source).toMatch(/path="\/app\/workspace-engine" element=.*RedirectWorkspaceAliasToCanonical/);
      expect(source).toMatch(/path="live" element=.*MonitoringDashboard/);
      expect(source).toMatch(/path="tokens" element=.*TokenCenter/);
    });
    it('authenticated redirects and aliases converge on /app/workspace', () => {
      const appPath = path.join(__dirname, '../App.js');
      const source = fs.readFileSync(appPath, 'utf8');
      expect(source).toMatch(/Navigate to="\/app\/workspace" replace/);
      expect(source).toMatch(/return <Navigate to={`\/app\/workspace\$\{search\}`} state=\{state\} replace \/>/);
      expect(source).toMatch(/function RedirectAppIndexToWorkspace\(\)/);
      expect(source).toMatch(/function RedirectWorkspaceAliasToCanonical\(\)/);
      expect(source).toMatch(/Route index element=\{<RedirectAppIndexToWorkspace \/>\}/);
    });

    it('workspace aliases preserve surface query modes and state', () => {
      const appPath = path.join(__dirname, '../App.js');
      const source = fs.readFileSync(appPath, 'utf8');
      expect(source).toMatch(/function RedirectWorkspaceAliasToCanonical\(\)/);
      expect(source).toMatch(/return <Navigate to={`\/app\/workspace\$\{search\}`} state=\{state\} replace \/>/);
      expect(source).toMatch(/path="\/app\/workspace-unified" element=\{<RedirectWorkspaceAliasToCanonical \/>\}/);
      expect(source).toMatch(/path="\/app\/workspace-manus" element=\{<RedirectWorkspaceAliasToCanonical \/>\}/);
      expect(source).toMatch(/path="\/app\/workspace-classic" element=\{<RedirectWorkspaceAliasToCanonical \/>\}/);
    });
  });

  describe('§1.3 Canonical workspace entry points', () => {
    it('OnboardingPage routes users into /app/workspace', () => {
      const onboardingPath = path.join(__dirname, '../pages/OnboardingPage.jsx');
      const source = fs.readFileSync(onboardingPath, 'utf8');
      expect(source).toMatch(/navigate\('\/app\/workspace'/);
      expect(source).toMatch(/href="\/app\/workspace"/);
    });
    it('Sidebar exposes dashboard, workspace, and live view destinations', () => {
      const sidebarPath = path.join(__dirname, '../components/Sidebar.jsx');
      const source = fs.readFileSync(sidebarPath, 'utf8');
      expect(source).toMatch(/Link to="\/app\/dashboard"/);
      expect(source).toMatch(/navigate\('\/app\/workspace'/);
      expect(source).toMatch(/Link to="\/app\/workspace"/);
      expect(source).toMatch(/Link to="\/app\/live"/);
      expect(source).toMatch(/href="\/app\/workspace"/);
      expect(source).toMatch(/\/app\/workspace\?chatTaskId=/);
    });
    it('Layout shell does not own a competing right panel or outlet context', () => {
      const layoutPath = path.join(__dirname, '../components/Layout.jsx');
      const source = fs.readFileSync(layoutPath, 'utf8');
      expect(source).not.toMatch(/import RightPanel from/);
      expect(source).not.toMatch(/setRightPanelVisible/);
      expect(source).not.toMatch(/<Outlet context=/);
      expect(source).toMatch(/rightPanel=\{null\}/);
    });
    it('public dashboard entry links target /app/workspace', () => {
      const publicNavPath = path.join(__dirname, '../components/PublicNav.jsx');
      const landingPath = path.join(__dirname, '../pages/LandingPage.jsx');
      const projectsPath = path.join(__dirname, '../pages/OurProjectsPage.jsx');
      const publicNav = fs.readFileSync(publicNavPath, 'utf8');
      const landing = fs.readFileSync(landingPath, 'utf8');
      const projects = fs.readFileSync(projectsPath, 'utf8');

      expect(publicNav).toMatch(/to="\/app\/workspace"/);
      expect(landing).toMatch(/navigate\('\/app\/workspace'\)/);
      expect(projects).toMatch(/navigate\('\/app\/workspace'\)/);
    });
    it('pricing, learn, and payments CTAs route to /app/workspace', () => {
      const pricingPath = path.join(__dirname, '../pages/Pricing.jsx');
      const learnPath = path.join(__dirname, '../pages/LearnPublic.jsx');
      const paymentsPath = path.join(__dirname, '../pages/PaymentsWizard.jsx');
      const pricing = fs.readFileSync(pricingPath, 'utf8');
      const learn = fs.readFileSync(learnPath, 'utf8');
      const payments = fs.readFileSync(paymentsPath, 'utf8');

      expect(pricing).toMatch(/navigate\('\/app\/workspace'\)/);
      expect(learn).toMatch(/navigate\('\/app\/workspace'\)/);
      expect(payments).toMatch(/navigate\('\/app\/workspace'\)/);
    });
    it('agent monitor, templates, examples, share, and builder pages use canonical workspace links', () => {
      const agentMonitorPath = path.join(__dirname, '../pages/AgentMonitor.jsx');
      const templatesPath = path.join(__dirname, '../pages/TemplatesGallery.jsx');
      const examplesPath = path.join(__dirname, '../pages/ExamplesGallery.jsx');
      const sharePath = path.join(__dirname, '../pages/ShareView.jsx');
      const builderPath = path.join(__dirname, '../pages/Builder.jsx');
      const agentMonitor = fs.readFileSync(agentMonitorPath, 'utf8');
      const templates = fs.readFileSync(templatesPath, 'utf8');
      const examples = fs.readFileSync(examplesPath, 'utf8');
      const share = fs.readFileSync(sharePath, 'utf8');
      const builder = fs.readFileSync(builderPath, 'utf8');

      expect(agentMonitor).toMatch(/to="\/app\/workspace"/);
      expect(templates).toMatch(/navigate\('\/app\/workspace'\)/);
      expect(examples).toMatch(/navigate\('\/app\/workspace'\)/);
      expect(share).toMatch(/to="\/app\/workspace"/);
      expect(builder).toMatch(/navigate\('\/app\/workspace'\)/);
    });
    it('legacy workspace variants keep home/back links on /app/workspace', () => {
      const workspaceClassicPath = path.join(__dirname, '../pages/Workspace.jsx');
      const workspaceManusV2Path = path.join(__dirname, '../pages/WorkspaceManusV2.jsx');
      const workspaceClassic = fs.readFileSync(workspaceClassicPath, 'utf8');
      const workspaceManusV2 = fs.readFileSync(workspaceManusV2Path, 'utf8');

      expect(workspaceClassic).toMatch(/navigate\('\/app\/workspace'\)/);
      expect(workspaceClassic).toMatch(/href="\/app\/workspace"/);
      expect(workspaceManusV2).toMatch(/navigate\('\/app\/workspace'\)/);
      expect(workspaceManusV2).toMatch(/to="\/app\/workspace"/);
    });
    it('RightPanel exposes preview, code, files, and publish modes', () => {
      const rightPanelPath = path.join(__dirname, '../components/RightPanel.jsx');
      const source = fs.readFileSync(rightPanelPath, 'utf8');

      expect(source).toMatch(/const tabs = \['preview', 'code', 'files', 'publish', 'proof'\]/);
      expect(source).toMatch(/tab === 'preview'/);
      expect(source).toMatch(/tab === 'code'/);
      expect(source).toMatch(/tab === 'files'/);
      expect(source).toMatch(/tab === 'publish'/);
      expect(source).toMatch(/\/jobs\/\$\{jobId\}\/workspace\/files/);
      expect(source).toMatch(/\/jobs\/\$\{jobId\}\/workspace\/download/);
    });
  });

  describe('§1.4 Pricing → TokenCenter wiring (source contract)', () => {
    it('Pricing page source navigates to /app/tokens with state.addon when user and addon button', () => {
      const pricingPath = path.join(__dirname, '../pages/Pricing.jsx');
      const source = fs.readFileSync(pricingPath, 'utf8');
      expect(source).toMatch(/state:\s*\{\s*addon:\s*key\s*\}/);
      expect(source).toMatch(/\/app\/tokens/);
    });
    it('Pricing page source navigates to tokens with addon query when not logged in', () => {
      const pricingPath = path.join(__dirname, '../pages/Pricing.jsx');
      const source = fs.readFileSync(pricingPath, 'utf8');
      expect(source).toMatch(/\/app\/tokens\?addon=/);
      expect(source).toMatch(/encodeURIComponent\(key\)/);
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
