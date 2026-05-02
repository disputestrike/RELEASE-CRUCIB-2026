/**
 * Pricing Page — Arctic Clarity Design System
 * Three pricing tiers + feature comparison table + FAQ
 */

import { useState } from "react";
import { Link } from "wouter";
import { CheckCircle, X, Zap, ArrowRight, HelpCircle } from "lucide-react";
import MarketingNav from "@/components/MarketingNav";
import { toast } from "sonner";

const plans = [
  {
    name: "Starter",
    desc: "Perfect for small teams getting started.",
    monthlyPrice: 0,
    yearlyPrice: 0,
    cta: "Get started free",
    ctaVariant: "outline" as const,
    highlight: false,
    badge: null,
    features: [
      "Up to 3 team members",
      "5 dashboards",
      "Basic analytics",
      "7-day data retention",
      "Email support",
      null,
      null,
      null,
    ],
  },
  {
    name: "Pro",
    desc: "For growing teams that need more power.",
    monthlyPrice: 49,
    yearlyPrice: 39,
    cta: "Start Pro trial",
    ctaVariant: "primary" as const,
    highlight: true,
    badge: "Most popular",
    features: [
      "Up to 25 team members",
      "Unlimited dashboards",
      "Advanced analytics",
      "90-day data retention",
      "Priority email & chat support",
      "Workflow automation",
      "150+ integrations",
      null,
    ],
  },
  {
    name: "Enterprise",
    desc: "For large organizations with custom needs.",
    monthlyPrice: 149,
    yearlyPrice: 119,
    cta: "Contact sales",
    ctaVariant: "outline" as const,
    highlight: false,
    badge: null,
    features: [
      "Unlimited team members",
      "Unlimited dashboards",
      "AI-powered analytics",
      "Unlimited data retention",
      "24/7 dedicated support",
      "Advanced automation",
      "Custom integrations",
      "SSO & audit logs",
    ],
  },
];

const comparisonFeatures = [
  { label: "Team members", starter: "3", pro: "25", enterprise: "Unlimited" },
  { label: "Dashboards", starter: "5", pro: "Unlimited", enterprise: "Unlimited" },
  { label: "Data retention", starter: "7 days", pro: "90 days", enterprise: "Unlimited" },
  { label: "Analytics", starter: "Basic", pro: "Advanced", enterprise: "AI-powered" },
  { label: "Integrations", starter: "10", pro: "150+", enterprise: "Custom" },
  { label: "Workflow automation", starter: false, pro: true, enterprise: true },
  { label: "SSO / SAML", starter: false, pro: false, enterprise: true },
  { label: "Audit logs", starter: false, pro: false, enterprise: true },
  { label: "Custom contracts", starter: false, pro: false, enterprise: true },
  { label: "SLA guarantee", starter: false, pro: "99.9%", enterprise: "99.99%" },
];

const faqs = [
  {
    q: "Can I change plans at any time?",
    a: "Yes. You can upgrade or downgrade your plan at any time. Changes take effect immediately, and we'll prorate any billing differences.",
  },
  {
    q: "Is there a free trial for paid plans?",
    a: "Absolutely. All paid plans include a 14-day free trial with no credit card required. You'll have full access to all features during the trial.",
  },
  {
    q: "What payment methods do you accept?",
    a: "We accept all major credit cards (Visa, Mastercard, Amex), PayPal, and wire transfers for Enterprise plans.",
  },
  {
    q: "Can I cancel my subscription?",
    a: "Yes, you can cancel at any time from your billing settings. Your access continues until the end of the current billing period.",
  },
];

export default function Pricing() {
  const [yearly, setYearly] = useState(false);
  const [openFaq, setOpenFaq] = useState<number | null>(null);
  const handleComingSoon = () => toast.info("Feature coming soon!");

  return (
    <div className="min-h-screen bg-white">
      <MarketingNav />

      {/* Hero */}
      <section className="pt-28 pb-16 bg-gradient-to-b from-slate-50 to-white">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <span className="inline-block text-xs font-semibold text-indigo-600 uppercase tracking-widest mb-3">
            Pricing
          </span>
          <h1
            className="text-4xl lg:text-5xl font-extrabold text-slate-900 mb-4"
            style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}
          >
            Simple, transparent pricing
          </h1>
          <p className="text-lg text-slate-500 mb-8">
            Start free, scale as you grow. No hidden fees, no surprises.
          </p>

          {/* Toggle */}
          <div className="inline-flex items-center gap-3 bg-slate-100 rounded-full p-1">
            <button
              className={`px-5 py-2 rounded-full text-sm font-semibold transition-all ${
                !yearly ? "bg-white shadow text-slate-900" : "text-slate-500"
              }`}
              onClick={() => setYearly(false)}
            >
              Monthly
            </button>
            <button
              className={`px-5 py-2 rounded-full text-sm font-semibold transition-all ${
                yearly ? "bg-white shadow text-slate-900" : "text-slate-500"
              }`}
              onClick={() => setYearly(true)}
            >
              Yearly
              <span className="ml-2 text-xs font-bold text-emerald-600 bg-emerald-100 px-1.5 py-0.5 rounded-full">
                Save 20%
              </span>
            </button>
          </div>
        </div>
      </section>

      {/* Pricing cards */}
      <section className="pb-20 bg-white">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-3 gap-6 items-stretch">
            {plans.map(({ name, desc, monthlyPrice, yearlyPrice, cta, ctaVariant, highlight, badge, features }) => {
              const price = yearly ? yearlyPrice : monthlyPrice;
              return (
                <div
                  key={name}
                  className={`relative rounded-2xl p-7 flex flex-col ${
                    highlight
                      ? "bg-indigo-600 text-white ring-2 ring-indigo-600 shadow-2xl shadow-indigo-200"
                      : "bg-white border border-slate-200 shadow-sm"
                  }`}
                >
                  {badge && (
                    <div className="absolute -top-3.5 left-1/2 -translate-x-1/2">
                      <span className="bg-amber-400 text-amber-900 text-xs font-bold px-3 py-1 rounded-full">
                        {badge}
                      </span>
                    </div>
                  )}

                  <div className="mb-6">
                    <div className="flex items-center gap-2 mb-2">
                      <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${highlight ? "bg-white/20" : "bg-indigo-100"}`}>
                        <Zap className={`w-3.5 h-3.5 ${highlight ? "text-white" : "text-indigo-600"}`} />
                      </div>
                      <h2
                        className={`text-lg font-bold ${highlight ? "text-white" : "text-slate-900"}`}
                        style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}
                      >
                        {name}
                      </h2>
                    </div>
                    <p className={`text-sm ${highlight ? "text-indigo-200" : "text-slate-500"}`}>{desc}</p>
                  </div>

                  <div className="mb-6">
                    <div className="flex items-end gap-1">
                      <span
                        className={`text-4xl font-extrabold ${highlight ? "text-white" : "text-slate-900"}`}
                        style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}
                      >
                        {price === 0 ? "Free" : `$${price}`}
                      </span>
                      {price > 0 && (
                        <span className={`text-sm mb-1.5 ${highlight ? "text-indigo-200" : "text-slate-500"}`}>
                          /mo {yearly && <span className="text-xs">billed annually</span>}
                        </span>
                      )}
                    </div>
                  </div>

                  <button
                    onClick={handleComingSoon}
                    className={`w-full py-3 rounded-xl text-sm font-semibold mb-6 transition-all flex items-center justify-center gap-2 ${
                      ctaVariant === "primary"
                        ? "bg-white text-indigo-700 hover:bg-indigo-50"
                        : highlight
                        ? "bg-indigo-500 text-white hover:bg-indigo-400"
                        : "bg-indigo-600 text-white hover:bg-indigo-700"
                    }`}
                  >
                    {cta}
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>

                  <ul className="space-y-3 flex-1">
                    {features.map((f, i) =>
                      f ? (
                        <li key={i} className="flex items-start gap-2.5">
                          <CheckCircle className={`w-4 h-4 flex-shrink-0 mt-0.5 ${highlight ? "text-indigo-200" : "text-emerald-500"}`} />
                          <span className={`text-sm ${highlight ? "text-indigo-100" : "text-slate-600"}`}>{f}</span>
                        </li>
                      ) : (
                        <li key={i} className="flex items-start gap-2.5 opacity-30">
                          <X className={`w-4 h-4 flex-shrink-0 mt-0.5 ${highlight ? "text-white" : "text-slate-400"}`} />
                          <span className={`text-sm ${highlight ? "text-white" : "text-slate-400"}`}>Not included</span>
                        </li>
                      )
                    )}
                  </ul>
                </div>
              );
            })}
          </div>

          <p className="text-center text-sm text-slate-400 mt-8">
            All plans include a 14-day free trial · No credit card required · Cancel anytime
          </p>
        </div>
      </section>

      {/* Comparison table */}
      <section className="py-20 bg-slate-50">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2
            className="text-2xl font-extrabold text-slate-900 text-center mb-10"
            style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}
          >
            Compare all features
          </h2>
          <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left text-sm font-semibold text-slate-500 px-6 py-4 w-1/2">Feature</th>
                  {["Starter", "Pro", "Enterprise"].map((p) => (
                    <th
                      key={p}
                      className={`text-center text-sm font-bold px-4 py-4 ${
                        p === "Pro" ? "text-indigo-600 bg-indigo-50/50" : "text-slate-700"
                      }`}
                      style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}
                    >
                      {p}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {comparisonFeatures.map(({ label, starter, pro, enterprise }, i) => (
                  <tr key={label} className={`border-b border-slate-100 last:border-0 ${i % 2 === 0 ? "" : "bg-slate-50/50"}`}>
                    <td className="px-6 py-3.5 text-sm text-slate-600">{label}</td>
                    {[starter, pro, enterprise].map((val, j) => (
                      <td
                        key={j}
                        className={`px-4 py-3.5 text-center ${j === 1 ? "bg-indigo-50/30" : ""}`}
                      >
                        {typeof val === "boolean" ? (
                          val ? (
                            <CheckCircle className="w-4 h-4 text-emerald-500 mx-auto" />
                          ) : (
                            <X className="w-4 h-4 text-slate-300 mx-auto" />
                          )
                        ) : (
                          <span className={`text-sm font-medium ${j === 1 ? "text-indigo-700" : "text-slate-600"}`}>
                            {val}
                          </span>
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-20 bg-white">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2
            className="text-2xl font-extrabold text-slate-900 text-center mb-10"
            style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}
          >
            Frequently asked questions
          </h2>
          <div className="space-y-3">
            {faqs.map(({ q, a }, i) => (
              <div
                key={i}
                className="border border-slate-200 rounded-xl overflow-hidden"
              >
                <button
                  className="w-full flex items-center justify-between px-5 py-4 text-left"
                  onClick={() => setOpenFaq(openFaq === i ? null : i)}
                >
                  <span className="text-sm font-semibold text-slate-900">{q}</span>
                  <HelpCircle className={`w-4 h-4 flex-shrink-0 ml-4 transition-colors ${openFaq === i ? "text-indigo-600" : "text-slate-400"}`} />
                </button>
                {openFaq === i && (
                  <div className="px-5 pb-4 text-sm text-slate-500 leading-relaxed border-t border-slate-100">
                    {a}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-slate-900 text-slate-400 py-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
              <Zap className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="font-bold text-white" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>FlowDesk</span>
          </div>
          <p className="text-xs">© 2026 FlowDesk, Inc. All rights reserved.</p>
          <Link href="/">
            <a className="text-xs text-slate-400 hover:text-white transition-colors">← Back to home</a>
          </Link>
        </div>
      </footer>
    </div>
  );
}
