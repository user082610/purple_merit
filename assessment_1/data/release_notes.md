# Release Notes — Express Checkout v2

**Release version:** v2.4.1  
**Feature owner:** Payments Team  
**Rollout started:** 2026-03-27  
**Rollout scope:** 100% of users (gradual rollout completed by Day 3)

---

## What Changed

Express Checkout v2 replaces the legacy multi-step checkout flow with a single-page experience. Key changes:

- Consolidated address + payment into one screen
- New auto-save for payment methods (tokenised via Stripe)
- Parallel API calls to reduce perceived load time
- Client-side cart validation before payment attempt

## What We Were Trying to Fix

The old flow had a 42% drop-off between cart and confirmation. Internal testing showed the new flow reduced that to ~28% in staging.

## Staging Results

- Crash rate: 0.6% (acceptable)
- p95 API latency: 210ms (under 300ms target)
- Payment success rate: 97.4%

---

## Known Risks at Launch

1. **Payment gateway timeout under load** — Observed intermittently in staging when concurrent sessions exceeded ~1,200. Root cause not fully resolved; a connection pool increase was applied as a temporary mitigation. Monitoring was set up but alerting thresholds were not tightened post-launch.

2. **iOS 17 + WKWebView rendering edge case** — Flagged in QA but not consistently reproducible. Deprioritised before launch. No workaround documented.

3. **Parallel API calls and race condition** — The new client-side parallel fetch pattern was not load-tested at full traffic. Potential for inconsistent state between cart validation and payment token generation under high concurrency.

---

## Rollback Plan

1. Feature flag `checkout_v2_enabled` → set to `false`
2. Revert Nginx routing to legacy checkout service
3. Stripe token cache flush not required (tokens are backwards-compatible)
4. ETA to rollback: ~15 minutes with on-call engineer

---

*Last updated: 2026-03-26 by @jayden.r (Payments Team lead)*
