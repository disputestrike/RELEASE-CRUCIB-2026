/**
 * CrucibAI Feature Flags
 *
 * Add a flag here to gate unfinished features. Check flags in components with:
 *   import { FEATURE_FLAGS } from '../config/featureFlags';
 *   {FEATURE_FLAGS.revenueAnalytics && <RevenueAnalyticsDashboard />}
 */
export const FEATURE_FLAGS = {
  // behind-flag: revenue dashboard requires Stripe webhook integration (Wave 5)
  revenueAnalytics: false,
};
