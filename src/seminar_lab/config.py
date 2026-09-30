"""授業・素材・実行設定の検証。採用前の構造検査と配布判定を分離する。"""
from __future__ import annotations

from copy import deepcopy
from math import isfinite
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse

import yaml

COMMON = {"P0", "P1", "P2a", "P2b", "P3", "L1", "L2"}
PHASES = {"P0": "R0", "P1": "R1", "P2a": "R2", "P2b": "R3", "P3": "R3"}


class ValidationError(ValueError):
    """送信・配布前に修正が必要な設定。"""


def load_yaml(path: str | Path) -> dict[str, Any]:
    """実行や環境変数展開を行わずYAMLを読む。"""
    value = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValidationError("設定はキーと値の形式で記入してください。")
    return value


def minutes(clock: str) -> int:
    """時刻を日内の分へ変換する。"""
    if not isinstance(clock, str) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", clock):
        raise ValidationError("時刻はHH:MM形式です。")
    h, m = map(int, clock.split(":"))
    return h * 60 + m


def plan_timetable(plan: str, day: int) -> list[tuple[str, str, str]]:
    """PLANの時間割表から時刻・内容を照合用に読む。"""
    section = plan.split(f"## {3 if day == 1 else 5}. ", 1)[1].split("\n## ", 1)[0]
    return re.findall(r"^\| (\d\d:\d\d)–(\d\d:\d\d) \| ([^|]+?) \|", section, re.M)


def resolve_material(course: dict, manifest: dict, material_id: str) -> dict:
    """図の活動IDから原論文の版・権利を解決する。別論文への置換や循環を拒否。"""
    items = {m['id']: m for m in manifest['materials']}
    if material_id not in items:
        raise ValidationError('素材が登録されていません。')
    m = deepcopy(items[material_id])
    source_id = m.get('source_ref', material_id)
    if source_id != material_id:
        if source_id != course.get('day1_source_paper_id') or source_id not in items or items[source_id].get('source_ref'):
            raise ValidationError('第1日の図はP01を直接参照してください。')
        forbidden = {'bibliography', 'doi', 'source_url', 'source_version', 'file_hash', 'rights', 'adoption',
                     'pdf_url', 'pdf_page_count', 'license', 'open_access', 'publication_status', 'article_type'}
        if forbidden & m.keys():
            raise ValidationError('図の出典・版・権利・採用はP01から継承し、上書きしないでください。')
        m = {**deepcopy(items[source_id]), **m}
    if source_id == course['common_paper_id']:
        m['source_version'] = course['common_reading']['source_version']
        if material_id == source_id:
            m.update(deepcopy(course['common_reading']))
    m['source_material_id'] = source_id
    return m


def validate_homework_material(course: dict, material: dict) -> None:
    """掲載版・対象誌・OAの本人確認を検査。教員採用や科学的正しさは認定しない。"""
    policy = course.get('homework_policy', {})
    if policy.get('status') != 'confirmed':
        raise ValidationError('Homeworkの対象誌条件は教員確認待ちです。')
    doi_value = material.get('doi')
    doi = doi_value.strip().lower() if isinstance(doi_value, str) else ''
    common_doi = policy.get('common_doi', '').lower()
    if not common_doi:
        raise ValidationError('共通論文のDOI照合設定が必要です。')
    if material.get('id') == course['common_paper_id'] or doi == common_doi:
        raise ValidationError('HW1はP01と別論文を選んでください。P01継続はP01_REVIEWで記録できます。')
    bib = material.get('bibliography')
    if not isinstance(bib, dict) or not bib.get('title') or not bib.get('authors'):
        raise ValidationError('題名・著者・掲載誌を構造化した書誌に記入してください。')
    journal = bib.get('journal')
    if journal not in policy.get('journal_titles', []):
        raise ValidationError('Homeworkの対象誌リストに含まれていません。')
    if not re.fullmatch(r'10\.\d{4,9}/\S+', doi):
        raise ValidationError('掲載論文のDOIが必要です。')
    url = urlparse(material.get('source_url', ''))
    if url.scheme != 'https' or url.hostname not in {'www.nature.com', 'www.science.org'} or url.username or url.password:
        raise ValidationError('出版社の掲載論文ページを確認してください。')
    publisher = {'Nature': 'www.nature.com', 'Science': 'www.science.org'}
    if journal in publisher and url.hostname != publisher[journal]:
        raise ValidationError('掲載誌と出版社ページが一致しません。')
    if material.get('publication_status') != 'published' or material.get('article_type') != 'research':
        raise ValidationError('掲載済みの原著論文を選んでください。プレプリント・会議・ニュース等は対象外です。')
    if material.get('open_access') is not True:
        raise ValidationError('Open Access表示と利用条件を確認してください。')
    review = material.get('eligibility_review', {})
    if review.get('status') != 'confirmed' or not review.get('reviewer'):
        raise ValidationError('対象誌・原著・版・OAの確認状態と確認者を記録してください。')


def evidence_review_accepted(material: dict) -> bool:
    """教員確認、または明示的に委任されたF1/F2の原文照合だけを受理する。"""
    if material.get("evidence_status") == "human_verified":
        return True
    if material.get("evidence_status") != "agent_verified_user_delegated":
        return False
    required = {"V01": ["F2"], "V02": ["F1", "F2"]}.get(material.get("id"))
    review = material.get("evidence_review")
    if required is None or not isinstance(review, dict):
        return False
    return (
        review.get("rows") == required
        and review.get("decision_id") == "Q4_F1_F2_2026_09_30"
        and review.get("reviewer") == "agent"
        and review.get("result") == "pass"
        and bool(review.get("reviewed_at"))
        and bool(review.get("report_id"))
        and bool(material.get("file_hash"))
        and review.get("source_file_hash") == material.get("file_hash")
        and bool(material.get("source_version"))
        and review.get("source_version") == material.get("source_version")
    )


def check_course(course: dict, manifest: dict, root: Path, mode: str = "structure") -> list[str]:
    """APIを呼ばず、構造または配布準備の不足を列挙する。"""
    errors: list[str] = []
    if mode not in {"structure", "readiness"}:
        raise ValidationError("検査モードが不正です。")
    if len(course.get("days", [])) != 2 or [d.get("date") for d in course.get("days", [])] != ["2026-10-03", "2026-10-31"]:
        errors.append("授業日・2日分の時間割がPLANと異なります。")
    if course.get("common_paper_id") != "P01":
        errors.append("共通論文は単一のP01です。")
    contract = course.get("common_reading", {})
    if contract.get("material_id") != "P01" or contract.get("question_set_id") != "Q_COMMON_3":
        errors.append("共通読解契約が不正です。")
    questions = course.get("question_sets", {}).get("Q_COMMON_3", [])
    if len(questions) != 3:
        errors.append("共通設問は3問です。")
    plan = (root / "PLAN.md").read_text(encoding="utf-8")
    expected_questions = ["この研究の主要な主張は何か。", "それを支える根拠は何か。指定した本文・図と対応付けて説明する。", "まだ理解できていない点、追加で確認したい点は何か。"]
    if questions != expected_questions:
        errors.append("共通3問がPLAN第6.2節と異なります。")
    items = manifest.get("materials", [])
    ids = [m.get("id") for m in items]
    if len(ids) != len(set(ids)):
        errors.append("素材IDが重複しています。")
    if sum(m.get("role") == "common_paper" for m in items) != 1 or "P01" not in ids:
        errors.append("共通論文の枠はP01の1件です。")
    for material in items:
        if not (root / material.get("guide", "missing")).is_file():
            errors.append(f"素材ガイド欠落: {material.get('id')}")
    if course.get('day1_source_paper_id') != 'P01':
        errors.append('第1日の題材はP01の1報です。')
    common = next((m for m in items if m.get('id') == 'P01'), {})
    if course.get('homework_policy', {}).get('common_doi') != common.get('doi'):
        errors.append('Homeworkの除外DOIが共通P01と一致しません。')
    for mid in ('V01', 'V02'):
        try:
            raw = next((m for m in items if m['id'] == mid), {})
            if raw.get('source_ref') != 'P01':
                raise ValidationError('V01/V02はP01内の図を参照します。')
            resolve_material(course, manifest, mid)
        except ValidationError as exc:
            errors.append(str(exc))
    activities = course.get("activities", {})
    for aid in COMMON:
        a = activities.get(aid, {})
        if a.get("reading_ref") != "common_reading" or a.get("material_choice") is not False:
            errors.append(f"{aid}: P01の固定参照が必要です。")
        if any(k in a for k in ("material_id", "source_version", "assigned_scope", "question_set_id")):
            errors.append(f"{aid}: 共通契約の重複・上書きを禁止します。")
    for aid, a in activities.items():
        if a.get("kind") == "exercise" and a.get("segments_minutes") != [5, 5, 5]:
            errors.append(f"{aid}: 演習は5＋5＋5です。")
        if a.get("phase") != PHASES.get(aid) and aid in PHASES:
            errors.append(f"{aid}: 記録段階がPLANと異なります。")
        if a.get("material_id") and a["material_id"] not in ids:
            errors.append(f"{aid}: 素材参照がありません。")
    for day in course.get("days", []):
        blocks = day["blocks"]
        actual = [(b["start"], b["end"], b["title"]) for b in blocks]
        if actual != plan_timetable(plan, day["day"]):
            errors.append(f"第{day['day']}日: 時間割がPLANと異なります。")
        cursor = minutes(day["start"])
        teaching = 0
        for b in blocks:
            start, end = minutes(b["start"]), minutes(b["end"])
            if start != cursor or end <= start:
                errors.append("時間割に空白・重複・逆転があります。")
            cursor = end
            if b["kind"] not in {"break", "lunch", "consultation"}:
                teaching += end - start
        if cursor != minutes(day["end"]) or teaching != day["teaching_minutes"]:
            errors.append("終了時刻または正味時間が不正です。")
        timeline = day["timeline"]
        cursor = minutes(day["start"])
        seen: set[str] = set()
        for event in timeline:
            start, end = minutes(event["start"]), minutes(event["end"])
            if start != cursor or end <= start:
                errors.append("詳細進行に空白・重複があります。")
            cursor = end
            aid = event.get("activity_id")
            if aid:
                if aid in seen or aid not in activities:
                    errors.append("詳細進行の活動IDが不正です。")
                    continue
                seen.add(aid)
                a = activities[aid]
                if end - start != a["duration_minutes"]:
                    errors.append(f"{aid}: 活動時間が不正です。")
        if cursor != minutes(day["end"]):
            errors.append("詳細進行の終了時刻が不正です。")
        expected = {k for k, v in activities.items() if v.get("day") == day["day"]}
        if seen != expected:
            errors.append("詳細進行に活動の不足があります。")
        anchors = ({"P0": "10:15", "P1": "10:25", "L1": "11:30", "L2": "12:05", "V1": "13:30", "V2": "14:00",
                    "V3": "15:00", "V4": "15:35", "P2a": "16:00", "P2b": "16:15", "P3": "16:30"}
                   if day["day"] == 1 else {"D2T1": "14:20", "D2T2": "14:50", "D2W1": "15:30", "D2W2": "16:10"})
        for event in timeline:
            if event.get("activity_id") and anchors.get(event["activity_id"]) != event["start"]:
                errors.append("演習開始時刻がPLANの内訳と異なります。")
    for ref in course.get("entry_files", []):
        if not (root / ref).is_file():
            errors.append(f"入口ファイル欠落: {ref}")
    if mode == "readiness":
        adopted = [m for m in items if m.get("role") == "common_paper" and m.get("adoption") == "adopted"]
        if len(adopted) != 1:
            errors.append("配布未準備: 共通論文の採用数が1ではありません。")
        for mid in ("P01", "V01", "V02"):
            try:
                m = resolve_material(course, manifest, mid)
            except ValidationError:
                continue
            if m.get("adoption") != "adopted":
                errors.append(f"配布未準備: {mid}の採用が未完了です。")
            if not evidence_review_accepted(m):
                errors.append(f"配布未準備: {mid}の根拠表の教員確認または明示委任による確認が未完了です。")
            if not m.get("bibliography"):
                errors.append(f"配布未準備: {mid}の書誌がありません。")
            if m.get("rights", {}).get("ai_input") != "confirmed":
                errors.append(f"配布未準備: {mid}のAI入力権利が未確認です。")
            scope = contract if mid == "P01" else m
            if not scope.get("source_version") or not scope.get("assigned_scope"):
                errors.append(f"配布未準備: {mid}の版・指定範囲が未確定です。")
            if scope.get('scope_status') != 'confirmed':
                errors.append(f'配布未準備: {mid}の指定範囲は提案段階です。')
        if course.get('homework_policy', {}).get('status') != 'confirmed':
            errors.append('配布未準備: Homeworkの対象誌が未確定です。')
        for key, value in course.get("readiness", {}).items():
            if value != "pass":
                errors.append(f"配布未準備: {key}={value}")
    return errors


def material_context(course: dict, manifest: dict, activity_id: str,
                     selection: str | None = None, local_material: dict | None = None,
                     for_input: bool = True) -> dict[str, Any]:
    """共通課題はP01固定。Homeworkの学生選定だけ別のローカル定義を使う。"""
    if activity_id not in course["activities"]:
        raise ValidationError("活動IDを確認してください。")
    a = course["activities"][activity_id]
    if a.get("reading_ref") == "common_reading":
        mid = course["common_paper_id"]
        if selection is not None and selection != mid:
            raise ValidationError("共通課題の素材はP01に固定されています。")
    elif a.get("material_choice"):
        mid = selection
        if not mid:
            raise ValidationError("Homeworkの素材を明示してください。")
    else:
        mid = a.get("material_id")
        if selection is not None and selection != mid:
            raise ValidationError("この活動の素材は固定されています。")
    if mid and mid.startswith("U_"):
        if not a.get("material_choice") or not re.fullmatch(r"U_[A-Za-z0-9_-]+", mid):
            raise ValidationError("学生選定資料はHomework等で使用します。")
        m = deepcopy(local_material or {})
        if m.get("id") != mid or not all(m.get(k) for k in ("source_url", "bibliography", "source_version", "assigned_scope")):
            raise ValidationError("学生選定資料の出典・書誌・版・範囲を記入してください。")
        if for_input and (m.get("input_review", {}).get("status") != "confirmed" or not m.get("input_review", {}).get("reviewer")):
            raise ValidationError("入力の可否と確認者を記録してください。不明なら送らず教員へ相談してください。")
        m.update(role="student_paper", selection_origin="student", adoption="not_applicable", publication="not_granted")
    else:
        m = resolve_material(course, manifest, mid)
        if a.get("material_choice") and m["role"] not in {"common_paper", "extension_paper"}:
            raise ValidationError("HW1は条件を満たす教員の追加論文・学生選定論文を使います。")
        if for_input and (m.get("adoption") != "adopted" or m.get("rights", {}).get("ai_input") != "confirmed"):
            raise ValidationError("素材の採用またはAI入力の確認待ちです。")
        m["selection_origin"] = "common" if mid == "P01" else "instructor"
    if activity_id == 'HW1' and for_input:
        validate_homework_material(course, m)
    m["material_id"] = mid
    m["phase"] = a.get("phase")
    m["activity_id"] = activity_id
    return m


def validate_runtime(runtime: dict, kinds: set[str], parameters: dict) -> None:
    """実測済み経路と明示した設定だけを受理する。公開の空設定は拒否する。"""
    allowed = {"schema_version", "route", "api", "model", "base_url", "allowed_base_urls", "sdk_version", "proxy_version", "timeout_seconds", "max_retries", "capabilities", "audit"}
    if not isinstance(runtime, dict) or set(runtime) - allowed:
        raise ValidationError("不明な実行設定があります。黙って無視しません。")
    if runtime.get("schema_version", 1) != 1:
        raise ValidationError("未対応の実行設定版です。")
    if runtime.get("route") not in {"course_proxy", "direct_openai"} or runtime.get("api") != "responses":
        raise ValidationError("経路とResponses APIを明示してください。")
    if not all(isinstance(runtime.get(k), str) and runtime[k].strip() for k in ("model", "sdk_version")):
        raise ValidationError("実測したモデルID・SDK版を設定してください。")
    if type(runtime.get("max_retries")) is not int or runtime["max_retries"] != 0:
        raise ValidationError("この実装の自動再試行は0回です。")
    timeout = runtime.get("timeout_seconds")
    if type(timeout) not in (int, float) or not 0 < timeout <= 60:
        raise ValidationError("タイムアウトは0秒より長く60秒以下で設定してください。")
    base = runtime.get("base_url")
    if not isinstance(base, str):
        raise ValidationError("接続先の設定が必要です。")
    url = urlparse(base)
    if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise ValidationError("認証情報を含まないHTTPS接続先を設定してください。")
    if runtime["route"] == "direct_openai" and base.rstrip("/") != "https://api.openai.com/v1":
        raise ValidationError("直接経路の接続先が不正です。")
    if runtime["route"] == "course_proxy" and base not in runtime.get("allowed_base_urls", []):
        raise ValidationError("講義で許可された接続先を指定してください。")
    audit = runtime.get("audit", {})
    if not isinstance(audit, dict) or set(audit) - {"verified_at", "evidence_id", "route_test", "retention_review", "budget_fail_closed"}:
        raise ValidationError("監査記録に未対応の項目があります。")
    if audit.get("route_test") != "pass" or audit.get("retention_review") != "pass" or not audit.get("verified_at") or not audit.get("evidence_id"):
        raise ValidationError("実行経路・保持方針の確認記録が必要です。")
    if runtime["route"] == "course_proxy" and (audit.get("budget_fail_closed") != "pass" or not runtime.get("proxy_version")):
        raise ValidationError("予算確認不能時の停止試験と中継版の確認待ちです。")
    cap = runtime.get("capabilities", {})
    if not isinstance(cap, dict) or set(cap) - {"input_kinds", "manual_history", "parameters"}:
        raise ValidationError("対応機能に未対応の項目があります。")
    input_kinds = cap.get("input_kinds")
    if not isinstance(input_kinds, list) or any(k not in {"text", "image", "pdf"} for k in input_kinds):
        raise ValidationError("対応入力形式をtext/image/pdfの配列で指定してください。")
    if not kinds <= set(cap.get("input_kinds", [])) or cap.get("manual_history") is not True:
        raise ValidationError("この経路では入力形式・会話履歴が未検証です。")
    supported = cap.get("parameters", {})
    known = {"max_output_tokens", "temperature", "top_p", "reasoning"}
    if not isinstance(parameters, dict) or not isinstance(supported, dict) or set(supported) - known:
        raise ValidationError("パラメータの対応表が不正です。")
    for key, rule in supported.items():
        if not isinstance(rule, dict) or set(rule) not in ({"min", "max"}, {"values"}):
            raise ValidationError("対応する設定値はmin/maxまたはvaluesで明示してください。")
        if "values" in rule and (not isinstance(rule["values"], list) or not rule["values"]):
            raise ValidationError("設定値の一覧を空にできません。")
        if "min" in rule and (not all(type(rule[k]) in (int, float) and isfinite(rule[k]) for k in ("min", "max")) or rule["min"] > rule["max"]):
            raise ValidationError("設定範囲が不正です。")
    if set(parameters) - {"max_output_tokens", "temperature", "top_p", "reasoning"} or set(parameters) - set(supported):
        raise ValidationError("未対応の設定です。設定を黙って変更することはありません。")
    if type(parameters.get("max_output_tokens")) is not int or parameters["max_output_tokens"] <= 0:
        raise ValidationError("正の出力token上限を設定してください。")
    for key, val in parameters.items():
        rule = supported[key]
        if "values" in rule and val not in rule["values"]:
            raise ValidationError("設定値が確認済みの範囲外です。")
        if "min" in rule and (type(val) not in (float, int) or not rule["min"] <= val <= rule["max"]):
            raise ValidationError("設定値が確認済みの範囲外です。")
