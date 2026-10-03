"""Notebookへ必要な定義だけを通常のPythonセルとして配置する（制作時専用）。

学生の実行時には本スクリプトもsrcも不要。操作セルと記入欄は書き換えない。
--check は埋込みと検証済み共通処理のずれを検出する。
"""
from __future__ import annotations
import argparse
import ast
from copy import deepcopy
import json
from pathlib import Path
import pprint
import re
import symtable
import nbformat
import yaml

ROOT = Path(__file__).resolve().parents[1]
MODULES = ['config', 'records', 'inputs', 'client', 'connection', 'ui', 'open_weight']
LABELS = {'config': '資料・設定を確認する関数', 'records': '記録を作り、保存・再読込みする関数',
          'inputs': '送る文章・画像・PDFを準備する関数', 'client': 'APIへの送信と会話を管理する関数',
          'connection': '教員の接続設定を読む関数', 'ui': '入力の表示と保存先を作る関数',
          'open_weight': '公開モデルの読込み・生成・保存の関数'}


def global_reads(source: str) -> set[str]:
    """関数内のローカル変数を、必要なimportや定義と取り違えない。"""
    def collect(table):
        names = {s.get_name() for s in table.get_symbols() if s.is_referenced() and s.is_global()}
        for child in table.get_children():
            names |= collect(child)
        return names
    return collect(symtable.symtable(source, '<notebook>', 'exec'))


def strip_local_imports(source: str) -> str:
    """リポジトリ内importのみ除き、定義本体とコメントをそのまま残す。"""
    lines = source.splitlines(keepends=True)
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and (node.level or (node.module or '').startswith('seminar_lab')):
            for i in range(node.lineno - 1, node.end_lineno):
                lines[i] = ''
    return ''.join(lines).strip()


def catalog() -> tuple[dict, dict]:
    definitions, imports = {}, {}
    for module in MODULES:
        source = (ROOT / 'src/seminar_lab' / f'{module}.py').read_text()
        lines = source.splitlines()
        for node in ast.parse(source).body:
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Assign, ast.AnnAssign)):
                names = [node.name] if hasattr(node, 'name') else [n.id for n in ast.walk(node.targets[0] if isinstance(node, ast.Assign) else node.target) if isinstance(n, ast.Name)]
                start = min([node.lineno] + [d.lineno for d in getattr(node, 'decorator_list', [])]) - 1
                text = strip_local_imports('\n'.join(lines[start:node.end_lineno]))
                for name in names:
                    if name in definitions:
                        raise ValueError(f'Duplicate definition: {name}')
                    definitions[name] = (module, text)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom) and (node.level or node.module == '__future__'):
                    continue
                for alias in node.names:
                    name = alias.asname or (alias.name.split('.')[0] if isinstance(node, ast.Import) else alias.name)
                    statement = ast.unparse(ast.Import(names=[alias]) if isinstance(node, ast.Import) else ast.ImportFrom(module=node.module, names=[alias], level=0))
                    if name in imports and imports[name] != statement:
                        raise ValueError(f'Duplicate import: {name}')
                    imports[name] = statement
    return definitions, imports


def data_cell() -> str:
    """実行時に必要な公開設定だけをPythonの辞書として収める。"""
    course = yaml.safe_load((ROOT / 'config/course.yaml').read_text())
    course = {k: course[k] for k in ('common_paper_id', 'day1_source_paper_id', 'common_reading', 'homework_policy', 'activities', 'question_sets')}
    course['activities'] = {aid: {k: v for k, v in a.items() if k in {'reading_ref', 'material_choice', 'material_id', 'phase'}} for aid, a in course['activities'].items()}
    keep = {'id', 'role', 'source_ref', 'bibliography', 'doi', 'source_url', 'source_version', 'assigned_scope',
            'question_set_id', 'adoption', 'rights', 'ai_input_review', 'file_hash', 'publication_status', 'article_type', 'open_access', 'license'}
    manifest = yaml.safe_load((ROOT / 'materials/manifest.yaml').read_text())
    manifest = {'materials': [{k: v for k, v in m.items() if k in keep} for m in manifest['materials']]}
    course['activities']['PRACTICE'] = {'material_choice': False, 'material_id': 'PRACTICE', 'phase': 'practice'}
    manifest['materials'].append({
        'id': 'PRACTICE', 'role': 'practice', 'adoption': 'adopted',
        'bibliography': {'title': 'Notebookの操作練習（自作例。原論文ではない）'},
        'source_version': 'notebook-practice-2026-10-02',
        'assigned_scope': {'text_sections': ['このNotebookの入力例']},
        'rights': {'ai_input': 'confirmed'},
    })
    # 一項目ずつ読めるPythonリテラル。JSON文字列のevalや別ファイルの読込みを使わない。
    return 'course = ' + pprint.pformat(course, width=115, sort_dicts=False) + '\n\nmanifest = ' + pprint.pformat(manifest, width=115, sort_dicts=False)


def support_cells(notebook) -> list:
    # 02は公式SDKを直接使う小さな実習。記録用の共通処理・授業設定は不要。
    if notebook.metadata.get('standalone_api_lesson'):
        return []
    definitions, imports = catalog()
    source = '\n'.join(c.source for c in notebook.cells if c.cell_type == 'code' and not c.metadata.get('embedded_support'))
    needed = global_reads(source) & definitions.keys()
    while True:
        expanded = needed | set().union(*(global_reads(definitions[name][1]) for name in needed)) & definitions.keys()
        if expanded == needed:
            break
        needed = expanded
    used = set().union(*(global_reads(definitions[name][1]) for name in needed))
    import_source = '\n'.join(sorted({imports[name] for name in used & imports.keys()}))
    blocks = [('imports', '準備：このNotebookで使うライブラリ', import_source), ('course', '準備：読む論文・範囲・設問の設定', data_cell())]
    # 小さな関数はまとめ、大きなクラスは独立したセルにする。
    for module in MODULES:
        entries = [(name, text) for name, (owner, text) in definitions.items() if owner == module and name in needed]
        chunk, names, length, group = [], [], 0, 0
        for name, text in entries:
            if chunk and length + len(text.splitlines()) > 95:
                blocks.append((f'{module}-{group}', LABELS[module] + '：' + ', '.join(names), '\n\n\n'.join(chunk)))
                chunk, names, length, group = [], [], 0, group + 1
            chunk.append(text); names.append(name); length += len(text.splitlines())
        if chunk:
            blocks.append((f'{module}-{group}', LABELS[module] + '：' + ', '.join(names), '\n\n\n'.join(chunk)))
    if notebook.metadata.get('compact_support'):
        code = '\n\n'.join('# ' + title + '\n' + body for _, title, body in blocks)
        cell = nbformat.v4.new_code_cell(
            '# @title 1b. 関数を準備する（▶を1回押す。コードは開いて読めます）\n'
            'from __future__ import annotations\n' + code + '\n\nprint("関数の準備ができました。2へ進んでください。")',
            metadata={'embedded_support': 'all', 'jupyter': {'source_hidden': True}, 'cellView': 'form'})
        cell.id = 'support-all'
        return [cell]
    guide = nbformat.v4.new_markdown_cell('### 準備用の関数を定義する\n\n以下も上から順に実行します。この段階ではAPI送信・モデル取得・回答の生成は行いません。折りたたみを開くと、記録、入力、送信などの関数を読めます。授業中に変更する欄は、この後の番号付きの手順にあります。', metadata={'embedded_support': 'guide'})
    guide.id = 'support-guide'
    cells = [guide]
    for key, title, code in blocks:
        c = nbformat.v4.new_code_cell('# @title ' + title + '\nfrom __future__ import annotations\n' + code,
            metadata={'embedded_support': key, 'jupyter': {'source_hidden': True}, 'cellView': 'form'})
        c.id = 'support-' + key
        cells.append(c)
    return cells


def refresh(path: Path, check: bool = False) -> bool:
    notebook = nbformat.read(path, as_version=4)
    actual = [c for c in notebook.cells if c.metadata.get('embedded_support')]
    base = deepcopy(notebook)
    base.cells = [c for c in base.cells if not c.metadata.get('embedded_support')]
    expected = support_cells(base)
    if [(c.id, c.source) for c in actual] == [(c.id, c.source) for c in expected]:
        return False
    if not check:
        # installセルの直後。実行順は上から下、操作セルの順序を保つ。
        index = next(i for i, c in enumerate(base.cells) if c.cell_type == 'code') + 1
        base.cells[index:index] = expected
        nbformat.write(base, path)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    changed = [p.name for p in sorted((ROOT / 'notebooks').glob('0*.ipynb')) if refresh(p, args.check)]
    print(('埋込みの更新が必要: ' if args.check and changed else '埋込み確認: ') + (', '.join(changed) or '一致'))
    return int(args.check and bool(changed))

if __name__ == '__main__':
    raise SystemExit(main())
