# Gaps and Integrations Review — Can We Close Them?

**Purpose:** Review the main product gap (Meta/Google Ads “post to ad platforms”) and other high-value integrations. What we can do today, what would close the gap, and what’s optional.

---

## 1. The “Ads running” gap (Meta / Google Ads)

**Current state:**  
We produce the **copy and creative concepts** (Content Agent, Workspace). We build the **funnel and landing page**. We do **not** have a built-in “post to Meta/Google Ads” button. So “ads running” = we power content and funnel; the user (or their stack) runs the campaigns.

**Can we close this gap?**

### Option A: Keep current model (recommended for now)

- **Message:** “You run the ads; we built the stack.” (Already in **docs/MESSAGING_AND_BRAND_VOICE.md**.)
- **Today:** User takes our copy/creatives and pastes into Meta Ads Manager / Google Ads, or uses an HTTP step in an agent to call **their** backend that holds API keys and calls Meta/Google.
- **Pros:** No OAuth, no ad-platform compliance burden, no storing ad credentials. We stay “generate + orchestrate”; they own spend and platform rules.
- **Cons:** Not one-click “create campaign” inside CrucibAI.

### Option B: HTTP → user’s endpoint (already possible)

- User creates a small service (or uses Zapier/Make) that accepts our payload (headline, body, CTA, optional image URL) and creates the ad via Meta/Google API.
- In CrucibAI: agent action = **HTTP** POST to their endpoint with `{{steps.0.output}}` (Content Agent output). They store Meta/Google tokens on their side.
- **No product change**; we document this pattern in Learn or HOW_MARKETERS_USE_CRUCIBAI so users know they can “close the loop” themselves.

### Option C: Native “Meta Ads” / “Google Ads” action (future)

- Add action types e.g. `meta_ads` and `google_ads` in the automation executor.
- **Requires:** User connects ad account (OAuth or API key in Settings); we store token securely and call Meta Marketing API / Google Ads API from our backend.
- **Effort:** High — OAuth flows, per-platform API surface (campaigns, ad sets, creatives, image upload), compliance (Meta/Google dev policies, app review), error handling, and maintenance.
- **When to consider:** If we see strong demand and are willing to own credential storage and API churn. Until then, Option A + B are sufficient and honest.

**Recommendation (launch):**  
- **Option A is the launch position.** We do not change product or do more work. Message: “You run the ads; we built the stack.” No native Meta/Google Ads integration before launch.  
- **Option B:** Already documented in HOW_MARKETERS_USE_CRUCIBAI for users who want to wire their own endpoint. No product build.  
- **Option C:** Post-launch roadmap only. We stop building features and get ready to launch.

---

## 2. Other integration gaps (short scan)

| Area | We have today | Gap? | How to close (if we want) |
|------|----------------|------|----------------------------|
| **Payments** | Stripe (checkout, webhook) | No | — |
| **Email** | Resend / SendGrid (env API key) in executor | No | — |
| **Slack** | Slack action (webhook_url in config) | No | — |
| **HTTP** | Any URL, method, headers, body | No | User can call any API (including their own “post to ads” service). |
| **Meta/Google Ads** | Copy/creatives only | Yes | See §1 (Option B doc now; Option C later). |
| **CRM (HubSpot, Salesforce)** | Not first-class | Small | HTTP action today; optional native “HubSpot create lead” etc. later. |
| **LinkedIn / Twitter / TikTok ads** | No | Same as Meta/Google | Same pattern: copy from us, they post; or HTTP to their proxy; or future native. |
| **Analytics (GA4, Meta Pixel)** | We build the site; they add script | No | We could add “inject GA4/Meta Pixel” in build or deploy (env or UI). Optional. |

**Summary:**  
The only **positioning** gap we called out is “post to Meta/Google Ads.” Closing it **without** building native ad APIs: document the HTTP → your-endpoint pattern (Option B). Closing it **with** native: add Meta/Google actions later (Option C) when we’re ready for that commitment.

---

## 3. Messaging alignment

Our branding and processes now state clearly (**docs/MESSAGING_AND_BRAND_VOICE.md**):

- “Describe your idea on Monday. By Friday you can have a live site, automations, and the copy to run ads. Same AI that builds your app runs your workflows.”
- “You run the ads; we built the stack.”

So we **do not** overclaim “we post your ads”; we **do** claim “we power the content and the funnel, you (or your HTTP integration) run the campaigns.” That is consistent with this gap review and with Option A/B.

---

## 4. Launch position

- **We are not adding features before launch.** Ads gap stays as Option A: we power content and funnel; they run the campaigns. Option B (HTTP to user endpoint) is documented only. Option C (native Meta/Google) is post-launch roadmap.
- **Action items:** Done. Messaging in MESSAGING_AND_BRAND_VOICE; Option B described in HOW_MARKETERS_USE_CRUCIBAI. No further build for ads integration until after launch.
