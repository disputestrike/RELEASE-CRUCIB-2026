# Braintree Billing Setup

CrucibAI billing runs under the legal company **Starlight LLC**. Product brands such as Crucible AI, RevTree, and Gulfshire are product lines under Starlight, not separate legal entities.

## Railway Environment

Set these variables in Railway:

```bash
BRAINTREE_ENVIRONMENT=sandbox
BRAINTREE_MERCHANT_ID=
BRAINTREE_PUBLIC_KEY=
BRAINTREE_PRIVATE_KEY=
BRAINTREE_MERCHANT_ACCOUNT_ID=
APP_URL=https://your-production-domain.com
DATABASE_URL=
```

For production, change only:

```bash
BRAINTREE_ENVIRONMENT=production
```

Webhook endpoint:

```text
https://your-production-domain.com/api/webhooks/braintree
```

## Braintree Dashboard Setup

1. Create or confirm one Braintree gateway account for Starlight LLC.
2. Use one default merchant account ID for now and set it as `BRAINTREE_MERCHANT_ACCOUNT_ID`.
3. Enable recurring billing.
4. Create Braintree plans for every recurring app plan you sell.
5. Map those plan IDs to local `prices` records through the `braintree_plan_id` field.

Optional env fallback for seeded Crucible AI plans:

```bash
BRAINTREE_PLAN_BUILDER_MONTHLY=
BRAINTREE_PLAN_PRO_MONTHLY=
BRAINTREE_PLAN_SCALE_MONTHLY=
BRAINTREE_PLAN_TEAMS_MONTHLY=
BRAINTREE_PLAN_BUILDER_YEARLY=
BRAINTREE_PLAN_PRO_YEARLY=
BRAINTREE_PLAN_SCALE_YEARLY=
BRAINTREE_PLAN_TEAMS_YEARLY=
```

The backend still treats the database price rows as the source of truth. These variables only help seed missing `braintree_plan_id` values.

## What The App Provides

- `GET /api/billing/client-token`
- `POST /api/checkout/one-time`
- `POST /api/checkout/subscription`
- `GET /api/billing/overview`
- `POST /api/billing/payment-method`
- `POST /api/billing/change-plan`
- `POST /api/billing/cancel-subscription`
- `POST /api/billing/resume-subscription`
- `GET /api/billing/history`
- `POST /api/webhooks/braintree`

Frontend:

- `/app/billing`
- `/app/account/billing`

The frontend uses Braintree Drop-in. It never collects raw card numbers in regular inputs and never receives private Braintree credentials.

## Stripe Migration Notes

- Existing Stripe IDs are preserved as nullable/deprecated JSON fields where present.
- New payments use Braintree only.
- Existing Stripe subscribers need a separate operational migration plan because card vaults cannot be copied from Stripe to Braintree without customer/payment-method reauthorization.

## Security Rules

- Do not expose `BRAINTREE_PRIVATE_KEY` to the frontend.
- Do not trust frontend price or amount values.
- Use Braintree nonces/tokens only.
- Store only card metadata: brand/type, last4, and expiration.
- Verify webhooks through the Braintree SDK.
- Billing events are idempotent by provider/type/signature/payload digest.

