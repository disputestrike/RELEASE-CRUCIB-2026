# Legal Pages Audit — Coverage & Footer

**Purpose:** From a legal perspective, ensure we have what competitors typically have; confirm footer and “who we are” work. **Not a substitute for a lawyer** — have counsel review before launch.

---

## 1. What we have (legal pages)

| Page | Route | Content summary | Competitor parity |
|------|--------|------------------|-------------------|
| **Terms of Use** | `/terms` | Acceptance, AI disclaimer, use of service, age/eligibility (COPPA), accounts, plans/tokens/billing, acceptable use (ref to AUP), EU AI Act, IP, disclaimers, limitation of liability, indemnification, export/sanctions, changes, governing law, general, contact. | ✅ Standard. |
| **Privacy Policy** | `/privacy` | Data we collect, legal basis (GDPR), use, API keys/third parties, international transfers, retention, sharing, cookies (ref to Cookie Policy), children (COPPA), GDPR/UK rights, CCPA/CPRA, DPO contact, security, changes, contact. | ✅ GDPR, CCPA, DPO. |
| **Acceptable Use Policy (AUP)** | `/aup` | Prohibited uses (illegal, NSFW, gambling, harassment, misinformation, privacy violations, unlicensed advice, child safety), EU AI Act prohibited practices, no replication/IP extraction, attribution/branding, enforcement, appeals, changes, contact. | ✅ Standard + EU AI Act. |
| **DMCA & Copyright** | `/dmca` | Takedown notices (required elements), counter-notice, repeat infringers, misrepresentation, contact (dmca@crucibai.com). | ✅ DMCA-compliant. |
| **Cookie Policy** | `/cookies` | What cookies are, how we use them (necessary, functional, analytics, marketing), duration, choices, third-party cookies, updates, contact. | ✅ ePrivacy/GDPR. |
| **Security & Trust** | `/security` | Platform security (auth, secrets, rate limiting, headers, HTTPS, payments), your code (security scan, a11y, validate-and-fix), fraud/abuse, reporting (security@crucibai.com), links to Privacy and Terms. | ✅ Trust page. |
| **About** | `/about` | Who we are (Inevitable AI, 120-agent swarm), what we do, for everyone, legal/policies (links to Privacy, AUP, Terms, DMCA, Cookies), contact. | ✅ “Who we are” + descriptions. |

---

## 2. Footer and navigation

- **PublicFooter:** Links to Privacy, Terms, Acceptable Use, DMCA, Cookies (Legal column); About us (first column); Security & Trust (Resources). All use `<Link to="...">` and match routes in `App.js`.
- **LandingPage / OurProjectsPage:** Same legal links in footer sections; About and “Why CrucibAI” link to `/about`.
- **Layout (app footer):** Privacy, Terms, About.
- **Routes in App.js:** `/privacy`, `/terms`, `/security`, `/aup`, `/dmca`, `/cookies`, `/about` — all present and wired.

**Check:** Every footer legal link resolves to the correct component; no 404s.

---

## 3. Cross-links between legal pages

- **Terms** → Privacy, AUP.
- **Privacy** → AUP, Terms, Cookie Policy.
- **Security** → Privacy, Terms.
- **About** → Privacy, AUP, Terms, DMCA, Cookies.
- **AUP, DMCA, Cookies** → “Back to home”; AUP/DMCA have contact emails (appeals@, dmca@).

---

## 4. Contact and addresses

- **Privacy:** “support or legal contact address … (e.g. privacy@crucibai.com or legal@crucibai.com)”.
- **Terms:** “support or legal address provided in the app or on our website”.
- **Security:** security@crucibai.com.
- **AUP:** appeals@crucibai.com.
- **DMCA:** dmca@crucibai.com.
- **About:** “support@crucibai.com, or the Enterprise contact form”; “Privacy Policy or Terms” for legal.

**Recommendation:** Add a single **Contact** or **Legal** page (or a clear block on About) listing: support@, privacy@, legal@, security@, appeals@, dmca@, and physical/registered address when you have one.

---

## 5. Fixes applied (this audit)

- **Terms.jsx:** Duplicate section numbers corrected (4–16); “Please note” box styled for light theme (readable contrast).
- **Aup.jsx:** Section numbering 1–8; list and strong text contrast fixed for light background.
- **Security.jsx:** List and strong text contrast fixed; Security callout box made readable on light bg.
- **Dmca.jsx, Cookies.jsx:** List/strong text contrast fixed for light theme.
- **About.jsx:** Link and “Back to home”/Pricing/Enterprise colors fixed for visibility.

---

## 6. Optional (competitor-style) additions

- **Refund policy:** Terms already reference “refund policy as stated at the time of purchase.” A short `/refunds` page (or a Refunds section in Terms) would match many competitors.
- **Billing / commercial terms:** If you offer enterprise or custom contracts, a “Billing” or “Commercial Terms” page or section can help.
- **DPA / subprocessor list:** Privacy already mentions “we may offer a Data Processing Agreement (DPA) and subprocessor list upon request.” No code change; have the documents ready for enterprise.

---

## 7. Lawyer checklist (for counsel)

Before launch, have a lawyer confirm:

- [ ] Terms: jurisdiction, limitation of liability cap, arbitration/class waiver if any.
- [ ] Privacy: GDPR/UK/CCPA accuracy, lawful bases, retention, DPO/rep if required.
- [ ] AUP: prohibited uses and enforcement aligned with local law.
- [ ] DMCA: designated agent and notice/counter-notice process.
- [ ] Cookies: consent mechanism (e.g. banner) where required (EU/UK).
- [ ] Contact/address: registered address and contact details correct and visible where required.

---

*This audit confirms coverage and footer wiring from a product perspective. It is not legal advice. Have all legal pages reviewed by qualified counsel before going live.*
