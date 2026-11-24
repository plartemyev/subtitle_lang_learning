"""Single-phrase thinking-mode verification with full call traces.

For each engine: dump the exact request payload and the raw response,
then check the output for <think> markers. The remote Qwen3.6 additionally
gets a differential test (no kwarg / enable_thinking false / true) to prove
the knob is honored by the server. Local chat engines get their served
Jinja chat template dumped (/props) - a template without a think branch
plus a clean output is the strongest local evidence.
"""
import json
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools.benchmark_translation import (  # noqa: E402
    SUBTITLE_SYSTEM, LlamaServerEngine, _post_json, build_engines,
    load_env, load_phrase_sets)


def _get_raw(url):
    with urllib.request.urlopen(url, timeout=10) as response:
        return response.read().decode('utf-8')

env = load_env()
engines = build_engines(env)
phrase = load_phrase_sets()['eng']['phrases'][0]
print(f"phrase: {phrase['text']!r}\n")


def show(title, request, result, latency_ms):
    content = (result['choices'][0]['message']['content']
               if 'choices' in result else result.get('content', ''))
    usage = result.get('usage', result.get('timings', {}))
    print(f'--- {title}')
    print(f'REQUEST  {json.dumps(request, ensure_ascii=False)[:900]}')
    print(f'RESPONSE {latency_ms:.0f} ms, usage/timings: '
          f'{json.dumps(usage, ensure_ascii=False)[:300]}')
    print(f'CONTENT  {content!r}'[:600])
    markers = [m for m in ('<think>', '</think>', '<|channel|>', 'reasoning')
               if m in str(content)]
    print(f'THINK MARKERS: {markers or "none"}\n')


# --- remote Qwen3.6-35B: differential test of the thinking knob ------------
base = env['LLAMA_TRANSLATE_BASE_URL'].rstrip('/')
headers = {'Authorization': f'Bearer {env["LLAMA_TRANSLATE_API_KEY"]}'}
messages = [{'role': 'system', 'content': SUBTITLE_SYSTEM},
            {'role': 'user',
             'content': f"Translate into Russian:\n{phrase['text']}"}]
variants = [
    ('remote default (no kwarg)', None),
    ('remote enable_thinking=false',
     {'chat_template_kwargs': {'enable_thinking': False}}),
    ('remote enable_thinking=true',
     {'chat_template_kwargs': {'enable_thinking': True}}),
]
for title, extra in variants:
    payload = {'model': env['LLAMA_TRANSLATE_MODEL'], 'messages': messages,
               'max_tokens': 512, 'temperature': 0.0, **(extra or {})}
    import time
    start = time.perf_counter()
    result = _post_json(f'{base}/chat/completions', payload, timeout=300,
                        headers=headers)
    show(title, payload, result, (time.perf_counter() - start) * 1000)

# --- local engines: template evidence + production-identical request ------
for key in ('qwen3-4b', 'hymt15-18b', 'gemmax2-2b'):
    engine = engines[key]
    assert isinstance(engine, LlamaServerEngine)
    engine.start()
    try:
        props = json.loads(_get_raw(f'{engine._base_url()}/props'))
        template = props.get('chat_template', '')
        print(f'--- {key}: served chat template '
              f'({len(template)} chars, think branch: '
              f'{"think" in template})')
        print(f'TEMPLATE {template[:300]!r}\n')
        instruction = engine._prompt(phrase['text'], 'eng', 'ru',
                                     phrase['words'])
        if engine.mode == 'chat':
            messages = []
            if engine.system:
                messages.append({'role': 'system', 'content': engine.system})
            messages.append({'role': 'user', 'content': instruction})
            payload = {'messages': messages, 'max_tokens': 256,
                       'cache_prompt': True, **engine.sampling}
            url = f'{engine._base_url()}/v1/chat/completions'
        else:
            payload = {'prompt': instruction, 'n_predict': 256,
                       'cache_prompt': True, **engine.sampling}
            if engine.stop_sequences:
                payload['stop'] = engine.stop_sequences
            url = f'{engine._base_url()}/completion'
        import time
        start = time.perf_counter()
        result = _post_json(url, payload, timeout=300)
        show(f'{key} ({engine.mode} mode, production payload)', payload,
             result, (time.perf_counter() - start) * 1000)
    finally:
        engine.stop()
