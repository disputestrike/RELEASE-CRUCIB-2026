/** @jest-environment jsdom */
import '@testing-library/jest-dom';
/**
 * Nav & Pages click-through verification.
 * Evidence: Nav has Our solution (dropdown), Pricing, Our Project, Dashboard, Log in, Get started (no Sign up in header).
 * No Prompts, Templates, Documentation in nav. Blog removed from primary nav. All links go to correct routes.
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import LandingPage from '../pages/LandingPage';
import PublicNav from '../components/PublicNav';

const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

jest.mock('../authContext', () => ({
  useAuth: () => ({ user: null, token: null }),
}));

jest.mock('axios', () => ({ get: () => Promise.resolve({ data: {} }) }));

describe('Nav and pages — link and click-through verification', () => {
  beforeEach(() => {
    mockNavigate.mockClear();
  });

  const requiredNavLinkPaths = ['/pricing', '/our-projects'];
  const forbiddenInNav = ['/prompts', '/templates', '/learn', '/blog'];

  it('LandingPage: nav contains Our solution, Pricing, Our Projects (no Blog / Features in bar) and no Prompts/Templates/Documentation', () => {
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
    expect(screen.getByRole('button', { name: /our solution/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /log in/i })).toHaveAttribute('href', '/auth');
    expect(screen.queryByRole('link', { name: /^sign up$/i })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /get started/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^dashboard$/i })).toBeInTheDocument();
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

  it('LandingPage: footer has Our solution, Pricing, Privacy, Terms links (no Blog in footer)', () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>
    );
    const footer = document.querySelector('footer');
    expect(footer).toBeInTheDocument();
    const links = footer.querySelectorAll('a[href]');
    const hrefs = Array.from(links).map((a) => a.getAttribute('href'));
    expect(hrefs).toContain('/our-projects#solutions');
    expect(hrefs).toContain('/pricing');
    expect(hrefs).not.toContain('/blog');
    expect(hrefs).toContain('/privacy');
    expect(hrefs).toContain('/terms');
  });

  it('OurProjectsPage source: nav has Our solution dropdown wiring and story anchors', () => {
    const fs = require('fs');
    const path = require('path');
    const src = fs.readFileSync(path.join(__dirname, '../pages/OurProjectsPage.jsx'), 'utf8');
    expect(src).toMatch(/SolutionsNavDropdown/);
    expect(src).toMatch(/to="\/pricing"/);
    expect(src).toMatch(/to="\/our-projects"/);
    expect(src).not.toMatch(/to="\/blog"/);
    expect(src).toMatch(/id="solutions"/);
    expect(src).toMatch(/id="solution-founders"/);
    expect(src).toMatch(/id="use-case-poc"/);
    expect(src).toMatch(/One AI\. Two superpowers/);
    expect(src).toMatch(/No black boxes/);
    expect(src).toMatch(/Monday to Friday\. One platform/);
  });

  it('PublicNav: has Our solution, Pricing, Our Project, Log in, Get started, no Sign up (no Blog)', () => {
    render(
      <MemoryRouter>
        <PublicNav />
      </MemoryRouter>
    );
    expect(screen.getByRole('button', { name: /our solution/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /pricing/i })).toHaveAttribute('href', '/pricing');
    expect(screen.getByRole('link', { name: /projects/i })).toHaveAttribute('href', '/our-projects');
    expect(screen.queryByRole('link', { name: /^blog$/i })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: /log in/i })).toHaveAttribute('href', '/auth');
    expect(screen.queryByRole('link', { name: /^sign up$/i })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /get started/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /^dashboard$/i })).toHaveAttribute('href', '/app');
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
