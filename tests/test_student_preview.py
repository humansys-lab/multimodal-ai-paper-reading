"""送る内容の全体を、学生が省略なしで読めることを確認する。"""
from seminar_lab.ui import preview_text, activity_description


def test_preview_displays_literal_multiline_prompt_and_entire_history():
    payload = {'model': 'fixture-model', 'max_output_tokens': 512, 'input': [
        {'role': 'user', 'content': [{'type': 'input_text', 'text': '最初の問い\n次の行'}]},
        {'role': 'assistant', 'content': [{'type': 'output_text', 'text': '前の回答\nもう一行'}]},
        {'role': 'user', 'content': [{'type': 'input_text', 'text': '今回の問い' * 1000}]},
    ]}
    shown = preview_text(payload)
    assert '最初の問い\n次の行' in shown and '前の回答\nもう一行' in shown
    assert '今回の問い' * 1000 in shown
    assert shown.index('最初の問い') < shown.index('前の回答') < shown.index('今回の問い')


def test_preview_does_not_dump_image_bytes_or_change_request():
    image_url = 'data:image/png;base64,' + 'A' * 100
    payload = {'model': 'fixture-model', 'max_output_tokens': 512, 'input': [
        {'role': 'user', 'content': [{'type': 'input_image', 'image_url': image_url}]},
    ]}
    shown = preview_text(payload)
    assert '表示のみ省略' in shown and 'A' * 100 not in shown
    assert payload['input'][0]['content'][0]['image_url'] == image_url


def test_activity_description_displays_fixed_scope_and_three_questions(course, manifest):
    text = activity_description(course, manifest, 'P0')
    assert '最初の読解（AIなし）' in text and 'PDFのページ: 1 / 2 / 3' in text
    assert 'We implemented Paper2Agent' in text
    assert all(question in text for question in course['question_sets']['Q_COMMON_3'])
    assert '選択' not in text
