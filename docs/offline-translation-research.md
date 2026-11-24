# Offline translation engine research (November 2026)

Goal: replace the NLLB-200-distilled-600M / CTranslate2 offline provider
(CC-BY-NC-4.0, weak phrase quality, unusable cross-attention alignment)
with the best available engine for whole-phrase subtitle translation.
Per-word tooltips stay dictionary-first (kaikki Wiktionary); the engine
owes us phrase quality and latency only.

## Requirements

* Coverage: subtitle languages `eng/deu/rus` into UI locales `en/de/ru/th`.
* Latency budget: **3 s per phrase** (interactive click-to-translate).
* Prompt protocol: collapsed one-liner `Translate subtitle into <language>:
  <subtitle text>` - no system message, no dictionary injection. Dedicated
  MT models use their own card templates verbatim instead (they are
  completion-style models; a chat prompt would misrepresent them).
* License: open source preferred. License-restricted models were benchmarked
  anyway: the project is non-commercial, based in Thailand, and ships no
  weights - end users download them themselves (the established
  `tools/prepare_nllb.py` flow).

## Procedure

1. **Phrase sets** - `tools/benchmark_translation.py --extract` parses the
   three sample SRTs (`samples/`, Big Lebowski EN/DE/RU) through the real
   analysis pipeline (`core.analyzer`: HTML strip, entity unescape, hyphen
   and www-spam filters, spaCy tokenization) and keeps the last 30 cues per
   file, with lemma/POS/morph annotations.
   -> 270 phrases per engine (3 files x 30 cues x 3 target locales each).
2. **Engines** - three shapes behind one `translate(text, src, tgt, words)`
   contract: CTranslate2 in-process (NLLB baseline, MADLAD), a local
   `llama-server` subprocess per GGUF model, and an OpenAI-compatible HTTP
   endpoint (the LAN llama server).
3. **Thinking-mode verification** - `tools/trace_thinking.py` dumps the full
   request payload and raw response per engine. The remote Qwen3.6 got a
   differential test: no kwarg and `enable_thinking: true` both produce
   reasoning (512-token cap, ~27 s, visible content empty - reasoning lands
   in a separate `reasoning_content` field), only
   `chat_template_kwargs: {"enable_thinking": false}` yields the direct
   translation (1.2 s). The knob must therefore always be passed explicitly.
   Local evidence: served Jinja templates from `GET /props` - HY-MT1.5
   (Hunyuan) and GemmaX2 (raw completion, no template at all) have no
   thinking concept; Qwen3-4B-2507-*Instruct* carries Qwen's conditional
   think branch but never emits `<think>`.
4. **Latency budget** - each engine run starts one *unmeasured* warmup
   phrase (cold start is not steady state), then a 5-phrase elimination
   probe: median above 3000 ms marks the engine `SKIPPED`. `--no-probe`
   measures the full 270-phrase matrix instead (used for re-shots).
5. **Contamination control** - an external CPU hog hit the box repeatedly
   during the runs. Countermeasures: a quiet-machine gate (10 consecutive
   seconds of CPU busy < 40% from /proc/stat before every engine),
   atop recordings (1 s precision first, 5 s later - 1 s itself costs
   visible CPU), and a per-stage audit (`tools/audit_atop.py`) that replays
   atop for each stage window and flags any non-benchmark process holding
   >= 0.5 CPU core. Flagged stages were wiped and rerun; clean windows are
   recorded per phrase in the result cache (`at` wall-clock stamps).
6. **Caching** - every result lands in
   `tmp/bench/results/<engine>/<source>-<target>.json` keyed by source
   phrase, so any interrupted or invalidated run resumes without redoing
   completed pairs. `--report` renders `report.md`/`report.html`
   side-by-side tables plus a latency summary.

## Model inventory

| Model | HF repo (weights used) | License verdict | Size (quant) | Benchmark verdict |
|---|---|---|---|---|
| Qwen3.6-35B-A3B | LAN llama server (`/models/Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf`) | Apache-2.0 family | Q4_K_XL MoE (3B active) | **in budget, best quality** |
| HY-MT1.5-1.8B | `tencent/HY-MT1.5-1.8B-GGUF` Q4_K_M | Tencent HY Community (EU/UK/KR ban, 100M-MAU clause) - restricted | 1.06 GB | over budget, best local candidate |
| GemmaX2-28-2B-v0.1 | `mradermacher/GemmaX2-28-2B-v0.1-i1-GGUF` | Gemma Terms - restricted | 1.59 GB | over budget |
| Hunyuan-MT-7B | `mradermacher/Hunyuan-MT-7B-GGUF` Q4_K_M | Tencent Hunyuan Community - restricted | 4.31 GB | over budget (probe) |
| HY-MT1.5-7B | `tencent/HY-MT1.5-7B-GGUF` Q4_K_M | Tencent HY Community - restricted | 4.31 GB | over budget (probe) |
| Seed-X-Instruct-7B | `DevQuasar/ByteDance-Seed.Seed-X-Instruct-7B-GGUF` Q4_K_M | OpenMDW (OSI review pending) | 4.25 GB | over budget (probe) |
| Tower+ 9B | `mradermacher/Tower-Plus-9B-GGUF` Q4_K_M | CC-BY-NC-SA - restricted, no Thai | 5.37 GB | over budget (probe) |
| MiLMMT-46-12B-v1.0 | `mradermacher/MiLMMT-46-12B-v1.0-GGUF` Q4_K_M | Gemma Terms - restricted | 6.80 GB | over budget (probe) |
| MADLAD-400-3B-MT | `Nextcloud-AI/madlad400-3b-mt-ct2-int8` (CTranslate2) | Apache-2.0 | int8 2.77 GB | over budget (probe) |
| Qwen3-4B-Instruct-2507 | `unsloth/Qwen3-4B-Instruct-2507-GGUF` Q4_K_M | Apache-2.0 | 2.33 GB | over budget (probe) |
| Typhoon Translate 1.5 4B | `typhoon-ai/typhoon-translate1.5-4b-gguf` Q4_K_M | apache-2.0 tag, card prose still says "Gemma License" (stale from v1) - resolve before shipping | 2.33 GB | over budget, en-th only |
| gemma-3-4b-it | `mradermacher/gemma-3-4b-it-GGUF` Q4_K_M | Gemma Terms - restricted | 2.32 GB | over budget; cache invalidated by a harness prompt bug, not rerun |
| NLLB-200-distilled-600M | `data/models/nllb-600m-ct2` (CTranslate2) | CC-BY-NC-4.0 - restricted | int8 ~1.2 GB | in budget, quality baseline being replaced |
| GemmaX2 9B / MiLMMT 4B / Qwen3-MT / Cohere North | - | various | - | not benchmarked (no GGUF / closed / huge) |

Notes: CTranslate2's `drama3` support is Fish Audio's TTS model, not MT.
MADLAD under CTranslate2 needs its `<2xx>` target token prepended to the
*source*; CT2 conversions of it require converter >= 3.22 (decoder_start
fix). GemmaX2/MiLMMT/Tower+ need llama.cpp Gemma2/Gemma3 builds (b4676+);
Hunyuan/HY-MT dense support landed Aug 2025; the 2025 GGUF conversion bug
for Hunyuan (issue #15726) is fixed.

## Results (final, atop-audited windows only)

| Engine | Phrases | Median s/phrase | Mean | Budget (3 s) |
|---|---|---|---|---|
| Qwen3.6-35B remote, collapsed prompt | 270 | **1.03** | 1.14 (p90 1.66) | **pass** |
| NLLB-600M baseline (CT2, beam 4) | 270 | 1.30 | 1.50 | pass (quality failed) |
| HY-MT1.5-1.8B | 270 | 3.88 | 4.22 (p90 7.70) | fail (+29%) |
| GemmaX2-28-2B | 270 | 3.88 | 3.95 (p90 5.68) | fail (+29%) |
| Qwen3-4B | probe | 7.5 | - | fail (skipped) |
| Typhoon Translate 1.5 (eng-th only) | 30 | 7.80 | 8.80 | fail |
| Hunyuan-MT-7B / HY-MT1.5-7B / Seed-X / Tower+ / MiLMMT / MADLAD-3B | probe | 6.6 - 23.7 | - | fail (skipped) |

Earlier invalidated measurements, kept out of the tables: the first
remote/local passes overlapped the CPU hog (atop audit flagged the
madlad and seed-x windows, 5.5% and 0.4% external core-time); qwen3-4b
and gemma3-4b full runs used a harness prompt without the target
language (wrong-language outputs - caught by the trace tool, fixed, and
qwen3-4b retested); the dictionary-gloss engines were dropped by product
decision after working end-to-end (remote gloss: 2.1 s median, glossary
terms respected).

## Findings

1. **Only the LAN Qwen3.6-35B satisfies the latency budget**, with 3x
   headroom, and it is also the strongest translator in the field. The
   collapsed prompt made it faster (p90 2.7 -> 1.66 s) than the earlier
   system-prompt variant.
2. **No local model fits the budget on this hardware** (4c/8t Zen1 laptop,
   AVX2, CPU-only): the closest are HY-MT1.5-1.8B and GemmaX2-2B at
   ~3.9 s (+29%). An offline fallback is therefore either "none" (503
   `translation_unavailable`, dictionary tooltips keep working - the
   existing graceful path) or a deliberately over-budget engine.
3. **Thinking mode**: Qwen3.6 thinks *by default*; `enable_thinking: false`
   is mandatory and verified differentially. The 1 s atop precision was
   itself a measurable CPU cost - 5 s is enough for stage audits.
4. **Licenses**: the strongest local engines (HY-MT/Hunyuan family, GemmaX2,
   MiLMMT) are open-weights-restricted; acceptable for this non-commercial
   project only in the end-user-downloads-weights flow. Genuinely open
   (Apache) locals: Qwen3-4B, MADLAD-3B - both over budget. Typhoon
   Translate 1.5 is Apache-tagged but its card prose contradicts the tag
   (stale Gemma license from v1) - get written confirmation before use.
5. **POE metadata**: injecting lemma/POS tags into the prompt was rejected
   (distribution shift, no training signal); the dictionary-gloss term list
   variant works mechanically (terms respected at +1 s latency) but was
   dropped from the plan. The annotations' productive role remains the
   per-word tooltip/dictionary layer.
6. **Literal dictionary column** (product experiment): a pure-algorithm
   word-by-word glossing engine - surface form first, then lemma,
   POS-disambiguated among target-locale translations, transliteration
   fallback - runs in ~1 ms/phrase and needs no model. It is kept in the
   benchmark report as the pedagogical "how the idiom is built" view
   (e.g. rus-en: "Твою мать!" -> "your mother !"), not as a translation
   quality contender. Dictionary forms carry Wiktionary stress marks and
   stay uninflected, which is a feature for a student, noise for fluency.
   Hardening after the first pass exposed a dictionary *build* bug: the
   dumps carry several entries per (word, pos) and `INSERT OR IGNORE` was
   first-writer-wins, freezing hollow rows - the pronoun "I" appeared in
   the dump with 663 translations including Russian "я", but an earlier
   abbreviation entry with an empty translation dict kept the slot. The
   build now keeps the field-wise richer row of every conflicting pair and
   the dictionary was rebuilt. The lookup matches POS case-insensitively
   (wiktextract keeps raw codes like "intj", so "Well" used to fall through
   to the adjective "здоровый"); the literal engine adds pymorphy3
   normal-form candidates for Cyrillic words (вам -> вы -> "you",
   нехорошо -> нехороший -> "not good"), prefers non-transliteration
   translations (мужик -> "man", not "muzhik"), transliterates
   case-preserving (Ч -> Ch), and keeps a reverse index for single-word
   data gaps.
7. **Fallback decision**: HY-MT1.5-1.8B (~3.9 s median, audited clean,
   Thai-capable, license workable in the end-user-download flow) is the
   accepted offline fallback for the production provider.

## Reproducing

    poetry install --with web,tools
    poetry run python tools/benchmark_translation.py --extract   # phrase sets
    poetry run python tools/benchmark_translation.py --list      # engine keys
    poetry run python tools/benchmark_translation.py --engine <key> [--no-probe]
    poetry run python tools/benchmark_translation.py --report    # md + html
    sudo atop -w /var/log/atop/atop_bench 5 &                    # recording
    poetry run python tools/audit_atop.py <atop-log-copy>        # stage audit
    poetry run python tools/trace_thinking.py                    # call traces

Engine registry (GGUF paths, prompt templates, sampling) lives in
`build_engines()` of `tools/benchmark_translation.py`; llama.cpp binaries in
`tmp/bench/bin/` (b12651, CPU); driver scripts of the original sweep in
`tmp/bench/*.sh`; raw per-phrase results and `report.html` in
`tmp/bench/results/` (gitignored). The committed report snapshot lives in
`docs/offline-translation-benchmark-report.md`.
