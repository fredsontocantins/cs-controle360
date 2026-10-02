## 2026-04-28 - Class-level Tuple Constants for Text Classification in PDF Parsing
**Learning:** Instantiating list literals and `any()` generator expressions per line inside PDF parsing loops creates significant GC and allocation overhead.
**Action:** Move static keyword lists and resolution markers to class-level tuple constants (`_CORRECAO_KEYWORDS`, `_NOVA_FUNCIONALIDADE_KEYWORDS`, etc.) and replace generator expressions with explicit loops and early breaks.
