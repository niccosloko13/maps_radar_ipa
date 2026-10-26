# Search address report

PASS. `parseAddressQuery` is exported as the explicit structured parser. Ranking uses street exactness (+100), city exactness (+60), exact number (+80), prefix (+20), approximate number on the same street (+15), and strong penalties for different street/city. Thus fuzzy results cannot outrank an exact street/city match.

The response now includes `address_state`: `EXACT_ADDRESS`, `APPROXIMATE_NUMBER`, `STREET_ONLY`, or `FUZZY_ALTERNATIVE`, plus a matching Portuguese label. Existing `match_quality` remains for compatibility. Existing coordinate/label deduplication is retained.

Scoped test: `python -m unittest test_navigation_intelligence -v` — 10 passed. Rui Barbosa 198, 521 and 818 all keep Rua Rui Barbosa / Praia Grande first. Number 999999 keeps that street first with `APPROXIMATE_NUMBER`; it is not labeled as a missing number on a different street. CEP coverage passed in the same suite.
