/**
 * MarketingNav — Arctic Clarity Design System
 * Clean top navigation for the public-facing landing page
 * Sticky with blur backdrop on scroll
 */

import { useState, useEffect } from "react";
import { Link } from "wouter";
import { Zap, Menu, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

const navLinks = [
  { label: "Features", href: "#features" },
  { label: "Pricing", href: "/pricing" },
  { label: "Customers", href: "#testimonials" },
  { label: "Blog", href: "#" },
];

export default function MarketingNav() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handler);
    return () => window.removeEventListener("scroll", handler);
  }, []);

  const handleComingSoon = () => toast.info("Feature coming soon!");

  return (
    <header
      className={`
        fixed top-0 left-0 right-0 z-50 transition-all duration-300
        ${scrolled
          ? "bg-white/90 backdrop-blur-md shadow-sm border-b border-slate-200/80"
          : "bg-transparent"
        }
      `}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center h-16">
          {/* Logo */}
          <Link href="/">
            <a className="flex items-center gap-2.5 flex-shrink-0">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
                <Zap className="w-4 h-4 text-white" />
              </div>
              <span
                className="font-bold text-lg text-slate-900 tracking-tight"
                style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}
              >
                FlowDesk
              </span>
            </a>
          </Link>

          {/* Desktop nav links */}
          <nav className="hidden md:flex items-center gap-1 ml-10">
            {navLinks.map(({ label, href }) => (
              href.startsWith("#") ? (
                <a
                  key={label}
                  href={href}
                  className="text-sm font-medium text-slate-600 hover:text-slate-900 px-3 py-2 rounded-md hover:bg-slate-100 transition-colors"
                >
                  {label}
                </a>
              ) : (
                <Link key={label} href={href}>
                  <a className="text-sm font-medium text-slate-600 hover:text-slate-900 px-3 py-2 rounded-md hover:bg-slate-100 transition-colors">
                    {label}
                  </a>
                </Link>
              )
            ))}
          </nav>

          {/* CTA buttons */}
          <div className="hidden md:flex items-center gap-3 ml-auto">
            <Link href="/dashboard">
              <a className="text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors">
                Sign in
              </a>
            </Link>
            <Link href="/dashboard">
              <a className="btn-gradient inline-flex items-center gap-2 text-sm font-semibold px-4 py-2 rounded-lg">
                Get started free
              </a>
            </Link>
          </div>

          {/* Mobile menu button */}
          <button
            className="md:hidden ml-auto text-slate-600 hover:text-slate-900 p-2"
            onClick={() => setMobileOpen(!mobileOpen)}
          >
            {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden bg-white border-t border-slate-200 px-4 py-4 space-y-1">
          {navLinks.map(({ label, href }) => (
            <a
              key={label}
              href={href}
              className="block text-sm font-medium text-slate-700 hover:text-indigo-600 py-2.5 border-b border-slate-100 last:border-0"
              onClick={() => setMobileOpen(false)}
            >
              {label}
            </a>
          ))}
          <div className="pt-3 flex flex-col gap-2">
            <Link href="/dashboard">
              <a className="block text-center text-sm font-medium text-slate-700 border border-slate-300 rounded-lg py-2.5">
                Sign in
              </a>
            </Link>
            <Link href="/dashboard">
              <a className="btn-gradient block text-center text-sm font-semibold rounded-lg py-2.5">
                Get started free
              </a>
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
