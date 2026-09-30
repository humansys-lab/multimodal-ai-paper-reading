"""公開重みでトークン・埋め込み・次トークン予測を観察する補助教材。"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from uuid import uuid4
import os

MODEL_ID = 'Qwen/Qwen3-0.6B'
REVISION = 'c1899de289a04d12100db370d81485cdf75e47ca'
MAX_INPUT_TOKENS = 512
MAX_NEW_TOKENS = 128


def configure_cache(root: Path) -> Path:
    """教材フォルダ内へキャッシュを固定する。HFの自動認証・telemetryを使わない。"""
    root = root.resolve()
    cache = root / 'build/open-weight-cache'
    if not cache.resolve().is_relative_to(root):
        raise ValueError('キャッシュの実体は教材フォルダ内に置いてください。')
    cache.mkdir(parents=True, exist_ok=True)
    os.environ.update(HF_HOME=str(cache / 'huggingface'), TORCH_HOME=str(cache / 'torch'),
                      XDG_CACHE_HOME=str(cache), HF_HUB_DISABLE_TELEMETRY='1',
                      HF_HUB_DISABLE_IMPLICIT_TOKEN='1', TOKENIZERS_PARALLELISM='false')
    return cache


def load_model(device: str, allow_download: bool = False):
    """指定した計算機だけで読み込む。失敗時の別モデル・CPUへの切替は行わない。"""
    if device not in {'cuda', 'mps', 'cpu'}:
        raise ValueError('deviceはcuda（Colab GPU）、mps（Mac）、cpuから明示してください。')
    if os.environ.get('PYTORCH_ENABLE_MPS_FALLBACK') == '1':
        raise ValueError('MPSからCPUへの自動フォールバックを無効にしてください。')
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    if device == 'cuda' and not torch.cuda.is_available():
        raise RuntimeError('GPUを利用できません。Colabのランタイムを確認してください。')
    if device == 'mps' and not torch.backends.mps.is_available():
        raise RuntimeError('この実行環境ではMac GPUを利用できません。')
    options = dict(revision=REVISION, local_files_only=not allow_download,
                   trust_remote_code=False, token=False)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, **options)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID, **options, use_safetensors=True,
        dtype=torch.float32 if device == 'cpu' else torch.float16,
        attn_implementation='eager').to(device).eval()
    return tokenizer, model


def encode_prompt(tokenizer, prompt: str):
    """画面で確認できる会話テンプレートを適用。質問の追加・履歴切捨てはしない。"""
    if not prompt.strip():
        raise ValueError('質問を自分で記入してください。')
    text = tokenizer.apply_chat_template([{'role': 'user', 'content': prompt}],
        tokenize=False, add_generation_prompt=True, enable_thinking=False)
    encoded = tokenizer(text, return_tensors='pt', add_special_tokens=False)
    if encoded.input_ids.shape[1] > MAX_INPUT_TOKENS:
        raise ValueError(f'入力が{MAX_INPUT_TOKENS}トークンを超えています。自分で範囲を見直してください。')
    return text, encoded


def token_observation(tokenizer, model, text: str) -> dict:
    """実際のトークンIDと入力埋め込みの先頭4要素を返す。"""
    import torch
    if not text.strip():
        raise ValueError('観察する文字列が空です。')
    ids = tokenizer.encode(text, add_special_tokens=False)
    if len(ids) > 64:
        raise ValueError('観察用は64トークンまで。短い文を選んでください。')
    with torch.inference_mode():
        vectors = model.get_input_embeddings()(torch.tensor(ids, device=model.device)).float().cpu()
    return {'text': text, 'ids': ids, 'tokens': tokenizer.convert_ids_to_tokens(ids),
            'decoded_tokens': [tokenizer.decode([i]) for i in ids],
            'embedding_shape': list(vectors.shape), 'embedding_first4': vectors[:, :4].tolist(),
            'note': '文脈を処理する前の入力埋め込み。先頭4要素だけから意味は判断できない。'}


def next_token_predictions(tokenizer, model, text: str) -> list[dict]:
    """続きを生成する前の確率上位5件。正しさの確率ではない。"""
    import torch
    inputs = tokenizer(text, return_tensors='pt', add_special_tokens=False)
    if not 0 < inputs.input_ids.shape[1] <= MAX_INPUT_TOKENS:
        raise ValueError('空でない短い文を指定してください。')
    with torch.inference_mode():
        logits = model(**inputs.to(model.device)).logits[0, -1].float()
        values, ids = logits.softmax(-1).topk(5)
    return [{'token_id': int(i), 'text': tokenizer.decode([int(i)]),
             'probability': float(v)} for v, i in zip(values.cpu(), ids.cpu())]


def generate(tokenizer, model, prompt: str, max_new_tokens: int = 96, seed: int = 42) -> dict:
    """新規会話を1回実行。生回答・入力テンプレート・計算機・所要時間を保存可能にする。"""
    if type(max_new_tokens) is not int or not 1 <= max_new_tokens <= MAX_NEW_TOKENS:
        raise ValueError(f'出力上限は1〜{MAX_NEW_TOKENS}にしてください。')
    import torch
    from transformers import set_seed
    visible, encoded = encode_prompt(tokenizer, prompt)
    set_seed(seed)
    inputs = encoded.to(model.device)
    start = monotonic()
    with torch.inference_mode():
        result = model.generate(**inputs, max_new_tokens=max_new_tokens,
            do_sample=True, temperature=0.7, top_p=0.8, top_k=20,
            pad_token_id=tokenizer.eos_token_id)
    if model.device.type == 'mps':
        torch.mps.synchronize()
    elif model.device.type == 'cuda':
        torch.cuda.synchronize()
    ids = result[0, inputs.input_ids.shape[1]:].tolist()
    eos = model.generation_config.eos_token_id
    eos_ids = eos if isinstance(eos, list) else [eos]
    return {'run_id': str(uuid4()), 'timestamp': datetime.now(timezone.utc).isoformat(),
        'model': MODEL_ID, 'revision': REVISION, 'route': 'open_weight_local',
        'device': str(model.device), 'dtype': str(model.dtype), 'prompt': prompt,
        'visible_template': visible, 'conversation_mode': 'new', 'seed': seed,
        'parameters': {'temperature': 0.7, 'top_p': 0.8, 'top_k': 20,
                       'max_new_tokens': max_new_tokens, 'enable_thinking': False},
        'input_tokens': int(inputs.input_ids.shape[1]), 'output_tokens': len(ids),
        'response_raw': tokenizer.decode(ids, skip_special_tokens=True),
        'status': 'completed' if ids and ids[-1] in eos_ids else 'output_limit',
        'elapsed_seconds': round(monotonic() - start, 3), 'api_cost_usd': 0,
        'student_explanation': None, 'unresolved_point': None}
