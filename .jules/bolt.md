## 2026-09-29 - Pre-fetching operational lists across report generators
**Learning:** Calling `list_homologacao()`, `list_customizacao()`, `list_atividade()`, and `list_release()` inside loops or nested calculation functions for report cycle comparisons causes repeated database roundtrips. Pre-fetching full lists once at the method entry point and passing them as arguments eliminates up to 8 DB queries per report request.
**Action:** When building aggregate or multi-cycle reporting services, pre-fetch entity lists at the top-level method and pass them down to helper functions.
