# Google rotating signing keys — offline review

**144 HOLD**. This branch adds a bounded, optionally network-capable *server-only* JWKS fetch-and-cache helper; no network request is made by tests or the SHAI gateway. No public service or sign-in is connected.

Verified provider discovery source: https://accounts.google.com/.well-known/openid-configuration lists issuer https://accounts.google.com, jwks_uri https://www.googleapis.com/oauth2/v3/certs and ID-token RS256. https://developers.google.com/identity/openid-connect/openid-connect directs verifiers to fetch Google public signing keys from discovery and follow HTTP cache directives.

The cache pins that exact HTTPS endpoint and rejects redirects, unexpected status/content type, payloads over 64 KiB, duplicate JSON keys or kid, malformed JWKs, unsupported algorithms/size, and bad/missing cache directives. It accepts RSA 2048/3072/4096-bit public keys with e=65537. Cache changes are atomic; previously cached keys NEVER gain more lifetime on fetch/parse failure. Keys disappear on expiry, without a stale grace period; removed kids are not retained after rotation. A JWT header cannot supply a JWK URL nor trigger remote fetching.

An explicit \`fetch_pinned_google_jwks\` helper *could* fetch Google's public JWKS if called by a separate future server-side operator-controlled refresh, using system HTTPS validation; **this change does not invoke it in production or tests**. All simulated rotation tests use fake RSA keys and fake HTTP objects. The parser is deliberately strict: a change in Google's published JWK fields may cause closed-mode rejection, not silently relax trust.

Remaining: independently review DNS/TLS/proxy/egress pinning, OIDC discovery metadata handling, key rotation during outages, retry/circuit breaker policy, cache synchronization across replicas, real Google verification fixtures and observability without logging tokens, server-issued session binding, Android sign-in. The existing /chat gateway still accepts only its own EdDSA sessions; no Google ID token can be passed through as authority.

This is a review of code and synthetic test coverage, NOT a demonstration of a live, secure Google login. No deployment/merge authorised by this step. **144 HOLD**.
