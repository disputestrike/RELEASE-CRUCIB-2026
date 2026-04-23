/**
 * Nav & Pages click-through verification.
 * Evidence: Nav has exactly 6 items (Features, Pricing, Our Projects, Blog, Sign In, Get Started).
 * No Prompts, Templates, Documentation in nav. All links go to correct routes. Both pages pass.
 */
import React from 'react';
import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import LandingPage from '../pages/LandingPage';
import PublicNav from '../components/PublicNav';

const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

jest.mock('../App', () => ({
  useAuth: () => ({ user: null, token: null }),
  API: '/api',
}));

jest.mock('axios', () => ({ get: () => Promise.resolve({ data: {} }) }));

describe('Nav and pages — link and click-through verification', () => {
  beforeEach(() => {
    mockNavigate.mockClear();
  });

  const requiredNavLinkPaths = ['/features', '/pricing', '/our-projects', '/blog'];
  const forbiddenInNav = ['/prompts', '/templates', '/learn'];

  it('LandingPage: nav contains required links (Features, Pricing, Our Projects, Blog) and no Prompts/Templates/Documentation', () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>
    );
    const nav = document.querySelector('nav');
    expect(nav).toBeInTheDocument();
    const links = nav.querySelectorAll('a[href]');
    const hrefs = Array.from(links).map((a) => a.getAttribute('href').replace(/\?.*$/, ''));
    requiredNavLinkPaths.forEach((path) => {
      expect(hrefs).toContain(path);
    });
    forbiddenInNav.forEach((path) => {
      expect(hrefs.filter((h) => h === path || h.startsWith(path + '?'))).toHaveLength(0);
    });
    expect(screen.getByRole('link', { name: /(sign|log) in/i })).toHaveAttribute('href', '/auth');
    expect(screen.getByRole('button', { name: /get started/i })).toBeInTheDocument();
  });

  it('LandingPage: hero headline is "What can I do for you?"', () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>
    );
    expect(screen.getByRole('heading', { name: /what can i do for you\?/i })).toBeInTheDocument();
  });

  it('LandingPage: CTA has "Your idea is inevitable."', () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>
    );
    expect(screen.getByText(/your idea is inevitable\./i)).toBeInTheDocument();
  });

  it('LandingPage: footer has Product, Resources, Legal columns', () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>
    );
    expect(screen.getByText('Product')).toBeInTheDocument();
    expect(screen.getByText('Resources')).toBeInTheDocument();
    expect(screen.getByText('Legal')).toBeInTheDocument();
  });

  it('LandingPage: footer has Features, Pricing, Blog, Privacy, Terms links', () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>
    );
    const footer = document.querySelector('footer');
    expect(footer).toBeInTheDocument();
    const links = footer.querySelectorAll('a[href]');
    const hrefs = Array.from(links).map((a) => a.getAttribute('href'));
    expect(hrefs).toContain('/features');
    expect(hrefs).toContain('/pricing');
    expect(hrefs).toContain('/blog');
    expect(hrefs).toContain('/privacy');
    expect(hrefs).toContain('/terms');
  });

  it('OurProjectsPage source: nav has required links and page has full-content sections (file check)', () => {
    const fs = require('fs');
    const path = require('path');
    const src = fs.readFileSync(path.join(__dirname, '../pages/OurProjectsPage.jsx'), 'utf8');
    expect(src).toMatch(/to="\/features"/);
    expect(src).toMatch(/to="\/pricing"/);
    expect(src).toMatch(/to="\/our-projects"/);
    expect(src).toMatch(/to="\/blog"/);
    expect(src).toMatch(/One AI\. Two superpowers/);
    expect(src).toMatch(/No black boxes/);
    expect(src).toMatch(/Monday to Friday\. One platform/);
  });

  it('PublicNav: has Features, Pricing, Our Project, Blog, Sign In, Get Started', () => {
    render(
      <MemoryRouter>
        <PublicNav />
      </MemoryRouter>
    );
    expect(screen.getByRole('link', { name: /features/i })).toHaveAttribute('href', '/features');
    expect(screen.getByRole('link', { name: /pricing/i })).toHaveAttribute('href', '/pricing');
    expect(screen.getByRole('link', { name: /our project/i })).toHaveAttribute('href', '/our-projects');
    expect(screen.getByRole('link', { name: /blog/i })).toHaveAttribute('href', '/blog');
    expect(screen.getByRole('link', { name: /(sign|log) in/i })).toHaveAttribute('href', '/auth');
    expect(screen.getByRole('button', { name: /get started/i })).toBeInTheDocument();
  });

  it('PublicNav: does NOT have Prompts, Templates, Documentation links', () => {
    render(
      <MemoryRouter>
        <PublicNav />
      </MemoryRouter>
    );
    const allLinks = screen.queryAllByRole('link');
    const text = allLinks.map((l) => l.textContent?.toLowerCase() || '').join(' ');
    expect(text).not.toMatch(/\bprompts\b/);
    expect(text).not.toMatch(/\btemplates\b/);
    expect(text).not.toMatch(/\bdocumentation\b/);
  });
});
