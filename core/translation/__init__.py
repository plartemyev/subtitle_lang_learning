"""Offline translation: remote model with a local fallback engine.

The primary engine is an OpenAI-compatible server on the LAN (Ollama or
llama.cpp serving a big multilingual model), the offline backup is
HY-MT1.5-1.8B under llama.cpp (:mod:`core.translation.local_hymt`); the
fallback chain lives in :mod:`core.translation.chain`. The replaced
NLLB/CTranslate2 engine and its modules are removed along with the
dependency. Per-word tooltips remain dictionary-first; the literal
word-by-word view is dictionary-only and lives in :mod:`core.literal`.
UI-library agnostic like the rest of ``core/``. Model artifacts are not
part of the repository - prepare them with ``tools/prepare_hymt15.py`` /
``tools/build_dictionary.py`` and configure the remote server with
OLLAMA_* variables in the gitignored ``.env`` (see README).
"""
from core.translation.cache import TranslationCache, cache_key
from core.translation.chain import FallbackProvider
from core.translation.local_hymt import LocalLlamaProvider
from core.translation.models import PhraseTranslation, WordTranslation
from core.translation.remote import OllamaProvider
