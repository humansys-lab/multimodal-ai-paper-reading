"""学生用の共通配布ZIPを作る。秘密設定・キー・教員用原稿は含めない。

制作用依存: reportlab、Pillow。原資料は引数で指定し、公開Gitへ追加しない。
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import quote, unquote, urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PAPER_HASHES = {
    "Paper2Agent_Nature.pdf": "6727ef9ca72cfffb1e032a2f07c7b9a4a2b235154bdd779b135c3518433677bf",
    "ai_scientist_nature.pdf": "a75e0d93447f400179136bf18d909df29e0c8ccaeba076a1dfb1beeef0e0e10d",
}


def inline(text: str) -> str:
    """Markdownの短い強調とリンクだけをPDF用に変換する。"""
    text = escape(text)
    text = re.sub(r"\[([^\]]+)\]\((https://[^ )]+)\)", r'<link href="\2" color="#195B95">\1</link>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r'<b>\1</b>', text)
    return re.sub(r"`([^`]+)`", r'<font color="#224B69">\1</font>', text)


def make_guide(markdown: str, destination: Path, font: Path) -> None:
    """日本語フォントを埋め込んだ、3ページ想定の手順書を作る。"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

    pdfmetrics.registerFont(TTFont("GuideJP", str(font)))
    pdfmetrics.registerFontFamily("GuideJP", normal="GuideJP", bold="GuideJP", italic="GuideJP", boldItalic="GuideJP")
    common = dict(fontName="GuideJP", wordWrap="CJK", textColor=colors.HexColor("#17293C"))
    styles = {
        'body': ParagraphStyle('body', fontSize=9.5, leading=14, spaceAfter=5, **common),
        'cell': ParagraphStyle('cell', fontSize=8.4, leading=12.0, **common),
        'h1': ParagraphStyle('h1', fontSize=21, leading=27, spaceAfter=9, **common),
        'h2': ParagraphStyle('h2', fontSize=15, leading=20, spaceBefore=8, spaceAfter=8, **common),
        'h3': ParagraphStyle('h3', fontSize=11.5, leading=16, spaceBefore=7, spaceAfter=5, **common),
    }
    story = []
    lines = markdown.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line == '<!-- PAGEBREAK -->':
            story.append(PageBreak()); i += 1; continue
        if line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?', c) for c in cells):
                    rows.append([Paragraph(inline(c), styles['cell']) for c in cells])
                i += 1
            cols = len(rows[0]); width = A4[0] - 76
            ratios = {2: [.37, .63], 4: [.23, .15, .34, .28]}[cols]
            table = Table(rows, colWidths=[width * n for n in ratios], repeatRows=1, hAlign='LEFT')
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EAF1F7')),
                ('LINEBELOW', (0, 0), (-1, 0), .65, colors.HexColor('#8DA3B8')),
                ('LINEBELOW', (0, 1), (-1, -1), .25, colors.HexColor('#CBD6E0')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            story += [table, Spacer(1, 6)]
            continue
        level = len(line) - len(line.lstrip('#'))
        if level in {1, 2, 3} and line.startswith('#' * level + ' '):
            story.append(Paragraph(inline(line[level+1:]), styles[f'h{level}']))
        else:
            if line.startswith('- '): line = '・' + line[2:]
            story.append(Paragraph(inline(line), styles['body']))
        i += 1

    def footer(canvas, doc):
        canvas.setFont('GuideJP', 8)
        canvas.setFillColor(colors.HexColor('#536C83'))
        canvas.drawString(38, 23, '機械システム学セミナー 2026  |  当日の手順書')
        canvas.drawRightString(A4[0]-38, 23, str(doc.page))

    document = SimpleDocTemplate(str(destination), pagesize=A4, leftMargin=38, rightMargin=38,
                                 topMargin=33, bottomMargin=37, title='当日の手順書', author='京都大学 機械システム学セミナー')
    document.build(story, onFirstPage=footer, onLaterPages=footer)


def copy_notebook(source: Path, destination: Path, commit: str) -> None:
    """コードは変えず、ZIPの外の補足文書リンクだけ公開固定版へ向ける。"""
    book = json.loads(source.read_text())
    for cell in book['cells']:
        if cell['cell_type'] == 'code':
            if cell.get('outputs') or cell.get('execution_count') is not None:
                raise ValueError(f'出力付きNotebookは配布できません: {source.name}')
            continue
        def link(match):
            label, href = match.groups(); parts = urlsplit(href)
            if parts.scheme or parts.netloc or href.startswith('#'): return match.group(0)
            target = (source.parent / unquote(parts.path)).resolve()
            relative = target.relative_to(ROOT)
            if not target.is_file(): raise ValueError(f'参照先がありません: {relative}')
            if target.parent == ROOT / 'notebooks':
                new = target.name
            else:
                new = f'https://github.com/humansys-lab/multimodal-ai-paper-reading/blob/{commit}/' + quote(relative.as_posix())
            if parts.fragment: new += '#' + parts.fragment
            return f'[{label}]({new})'
        value = re.sub(r'\[([^\]]+)\]\(([^ )]+)\)', link, ''.join(cell['source']))
        cell['source'] = value.splitlines(keepends=True)
    destination.write_text(json.dumps(book, ensure_ascii=False, indent=1) + '\n')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ['slides', 'paper2agent', 'ai-scientist', 'font', 'output']:
        parser.add_argument('--' + flag, type=Path, required=True)
    parser.add_argument('--commit', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-f0-9]{40}', args.commit): raise ValueError('公開済みの固定コミットSHAを指定してください。')
    output = args.output.resolve()
    if not output.is_relative_to(ROOT) or output.exists():
        raise ValueError('出力はこの作業フォルダ内の未使用のディレクトリにしてください。')
    sources = {'Paper2Agent_Nature.pdf': args.paper2agent, 'ai_scientist_nature.pdf': args.ai_scientist}
    for name, path in sources.items():
        if sha256(path.read_bytes()).hexdigest() != PAPER_HASHES[name]:
            raise ValueError(f'授業で指定した掲載版と一致しません: {name}')
    output.mkdir(parents=True)
    materials = output / 'materials'; materials.mkdir()
    for name, path in sources.items(): shutil.copyfile(path, materials / name)
    shutil.copyfile(args.slides, output / 'day1_student_script_aligned.pdf')
    make_guide((ROOT / 'docs/student_quickstart.md').read_text(), output / '00_当日の手順書.pdf', args.font)
    for path in sorted((ROOT / 'notebooks').glob('0*.ipynb')):
        copy_notebook(path, output / path.name, args.commit)
    # 原ページ全体の形式・画素数だけを変更。図の追記・切り取りはしない。
    subprocess.run(['pdftoppm', '-f', '4', '-l', '4', '-singlefile', '-png',
                    '-scale-to-x', '1600', '-scale-to-y', '2126', str(args.paper2agent),
                    str(materials / 'fig2_full')], check=True)
    from PIL import Image
    with Image.open(materials / 'fig2_full.png') as original:
        original.resize((400, 532), Image.Resampling.LANCZOS).save(materials / 'fig2_quarter.png')
    paths = sorted(p for p in output.rglob('*') if p.is_file())
    if len(paths) != 10: raise ValueError('配布ファイル数が想定の10点と一致しません。')
    archive = output.with_suffix('.zip')
    if archive.exists(): raise ValueError('既存の配布ZIPは上書きしません。')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for path in paths: z.write(path, str(Path(output.name) / path.relative_to(output)))
    receipt = {'commit': args.commit, 'files': [
        {'name': p.relative_to(output).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha256(p.read_bytes()).hexdigest()} for p in paths],
        'slides_unchanged': sha256(args.slides.read_bytes()).hexdigest() == sha256((output / 'day1_student_script_aligned.pdf').read_bytes()).hexdigest(),
        'zip_sha256': sha256(archive.read_bytes()).hexdigest()}
    output.with_suffix('.receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2))
    print(json.dumps({'folder': str(output), 'zip': str(archive), 'file_count': len(paths)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
