"""公開重みでトークン・埋め込み・次トークン予測を観察する補助教材。"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from uuid import uuid4
import os

MODEL_ID = 'Qwen/Qwen3-0.6B'
REVISION = 'c1899de289a04d12100db370d81485cdf75e47ca'
MAX_INPUT_TOKENS = 2048
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
    if type(allow_download) is not bool:
        raise ValueError('allow_downloadはTrueまたはFalseで明示してください。')
    if os.environ.get('PYTORCH_ENABLE_MPS_FALLBACK') == '1':
        raise ValueError('MPSからCPUへの自動フォールバックを無効にしてください。')
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from huggingface_hub import snapshot_download
    if device == 'cuda' and not torch.cuda.is_available():
        raise RuntimeError('GPUを利用できません。Colabのランタイムを確認してください。')
    if device == 'mps' and not torch.backends.mps.is_available():
        raise RuntimeError('この実行環境ではMac GPUを利用できません。')
    # local_files_onlyでもTransformersのモデル名判定が通信する版がある。
    # 固定snapshotを先に解決し、読込みにはローカルのパスだけを渡す。
    snapshot = snapshot_download(MODEL_ID, revision=REVISION, local_files_only=not allow_download,
        token=False, allow_patterns=['*.json', '*.safetensors', 'merges.txt', 'vocab.*', 'tokenizer.model'])
    options = dict(local_files_only=True, trust_remote_code=False, token=False)
    tokenizer = AutoTokenizer.from_pretrained(snapshot, **options)
    model = AutoModelForCausalLM.from_pretrained(
        snapshot, **options, use_safetensors=True,
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
    response = tokenizer.decode(ids, skip_special_tokens=True)
    status = _generation_status(ids, response, eos_ids, max_new_tokens)
    return {'run_id': str(uuid4()), 'timestamp': datetime.now(timezone.utc).isoformat(),
        'model': MODEL_ID, 'revision': REVISION, 'route': 'open_weight_local',
        'device': str(model.device), 'dtype': str(model.dtype), 'prompt': prompt,
        'visible_template': visible, 'conversation_mode': 'new', 'seed': seed,
        'parameters': {'temperature': 0.7, 'top_p': 0.8, 'top_k': 20,
                       'max_new_tokens': max_new_tokens, 'enable_thinking': False},
        'input_tokens': int(inputs.input_ids.shape[1]), 'output_tokens': len(ids),
        'response_raw': response,
        'status': status,
        'elapsed_seconds': round(monotonic() - start, 3), 'api_cost_usd': 0,
        'student_explanation': None, 'unresolved_point': None}


def _generation_status(ids: list[int], response: str, eos_ids: list[int], limit: int) -> str:
    """終了トークンか出力上限による終了だけを受け付ける。空の回答はエラー。"""
    if not ids or not response.strip():
        raise RuntimeError('モデルが空の回答を返しました。成功として保存せず、入力と出力上限を確認してください。')
    if len(ids) > limit:
        raise RuntimeError('指定した出力上限を超えています。モデルの設定を確認してください。')
    if ids[-1] in eos_ids:
        return 'completed'
    if len(ids) == limit:
        return 'output_limit'
    raise RuntimeError('想定した終了条件に達せず停止しました。モデルの設定を確認してください。')


def reading_record(result: dict, context: dict, source_location: str) -> dict:
    """公開重みの実行をAPIと同じ読解記録へ変換。生の結果と追加項目も保持する。"""
    from copy import deepcopy
    from .records import new_record, validate_record
    if result.get('model') != MODEL_ID or result.get('revision') != REVISION:
        raise ValueError('記録するモデルと固定版が一致しません。')
    if result.get('status') not in {'completed', 'output_limit'} or not result.get('response_raw'):
        raise ValueError('保存する生成結果がありません。')
    record = new_record(context)
    record.update(run_id=result['run_id'], timestamp=result['timestamp'],
        service='Transformers', access_route='open_weight_local', requested_model=MODEL_ID,
        reported_model=MODEL_ID, conversation_mode='new', prior_turn_count=0,
        prompt=result['prompt'], input_kind=['text'], input_scope=source_location,
        request_input=result['visible_template'], visible_system_instructions=[],
        parameters_requested=deepcopy(result['parameters']), parameters_confirmed=deepcopy(result['parameters']),
        response_raw=result['response_raw'], status=result['status'], elapsed_seconds=result['elapsed_seconds'],
        usage={'input_tokens': result['input_tokens'], 'output_tokens': result['output_tokens']},
        cost_kind='not_applicable', cost_value=None, open_weight_result=deepcopy(result))
    record['cost_note'] = '外部API呼出しなし。計算機・Colabの利用料金を推定していない。'
    validate_record(record)
    return record


def save_result(result: dict, annotations: dict, root: Path) -> tuple[dict, list[Path]]:
    """生の生成結果と本人の説明を一度で保存する。既存ファイルは上書きしない。"""
    from copy import deepcopy
    from .records import record_json, validate_record
    from .ui import save_pair

    if (not isinstance(result, dict) or not isinstance(result.get('run_id'), str)
            or not result['run_id'].strip()):
        raise ValueError('保存する生成結果がありません。')
    if (result.get('model') != MODEL_ID or result.get('revision') != REVISION
            or result.get('route') != 'open_weight_local'):
        raise ValueError('このNotebookの固定モデルで生成した結果だけを保存してください。')
    if (result.get('status') not in {'completed', 'output_limit'}
            or not isinstance(result.get('response_raw'), str) or not result['response_raw'].strip()):
        raise ValueError('保存する生成結果がありません。終了状態と生回答を確認してください。')
    allowed = {'student_explanation', 'evidence_location', 'unresolved_point'}
    if (not isinstance(annotations, dict) or set(annotations) - allowed
            or any(v is not None and not isinstance(v, str) for v in annotations.values())):
        raise ValueError('記入欄は本人の説明・根拠・不明点の文字列かNoneにしてください。')
    saved = {**deepcopy(result), **{k: v for k, v in annotations.items() if v is not None}}
    record = None
    if saved.get('reading_context') is not None:
        record = reading_record(saved, saved['reading_context'], saved.get('source_location', ''))
        record.update({k: saved[k] for k in allowed if k in saved})
        validate_record(record)
    root = root.resolve()
    folder = root / 'outputs/open-weight'
    if not folder.resolve().is_relative_to(root):
        raise ValueError('保存先は教材フォルダ内にしてください。')
    destination = folder / (saved['run_id'] + '-' + uuid4().hex[:8] + '.json')
    if destination.resolve().parent != folder.resolve():
        raise ValueError('保存する実行番号に不正なパスが含まれています。')
    content = record_json(saved, indent=2)
    folder.mkdir(parents=True, exist_ok=True)
    with destination.open('x', encoding='utf-8') as handle:
        handle.write(content)
    paths = [destination]
    if record is not None:
        paths.extend(save_pair([record], root / 'outputs'))
    return saved, paths
