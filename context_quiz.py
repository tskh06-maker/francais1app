"""動詞×人称の例文を使った、活用形4択の穴埋めクイズ用ロジック。

sentences.json に事前生成された例文があればそれを使った文脈付きの問題を、
無ければ活用形だけを答えるシンプルな4択問題（文脈なしフォールバック）を作る。
"""

import random

from conjugation_quiz import PRONOUNS, build_full_form, get_verbs_for_tense

SENTENCES_PATH = "sentences.json"

BLANK = "（　　　）"


def load_sentences(path=SENTENCES_PATH):
    import json
    import os

    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {(e["verb"], e["person"], e.get("tense", "présent")): e for e in data}


def blank_out(sentence, form):
    idx = sentence.lower().find(form.lower())
    if idx == -1:
        return None
    return sentence[:idx] + BLANK + sentence[idx + len(form):]


def make_choices(verb, key, tense, correct_form, conjugations, count=4):
    """誤答選択肢を優先度順に集める: ①同じ動詞の別人称 → ②同じグループの別動詞 → ③ランダムな動詞。"""
    group = conjugations[verb].get("conjugationGroup")
    seen = {correct_form}
    distractors = []

    def add(form):
        if form not in seen:
            seen.add(form)
            distractors.append(form)

    other_keys = [k for k, _ in PRONOUNS if k != key]
    random.shuffle(other_keys)
    for k in other_keys:
        if len(distractors) >= count - 1:
            break
        add(build_full_form(verb, k, tense, conjugations))

    if len(distractors) < count - 1:
        same_group = [
            v for v in conjugations
            if v != verb and conjugations[v].get("conjugationGroup") == group and tense in conjugations[v]
        ]
        random.shuffle(same_group)
        for v in same_group:
            if len(distractors) >= count - 1:
                break
            add(build_full_form(v, key, tense, conjugations))

    if len(distractors) < count - 1:
        others = [v for v in conjugations if v != verb and tense in conjugations[v]]
        random.shuffle(others)
        for v in others:
            if len(distractors) >= count - 1:
                break
            add(build_full_form(v, key, tense, conjugations))

    choices = distractors[: count - 1] + [correct_form]
    random.shuffle(choices)
    return choices


def build_question(verb, key, tense, conjugations, sentences_index):
    correct_form = build_full_form(verb, key, tense, conjugations)
    choices = make_choices(verb, key, tense, correct_form, conjugations)

    entry = sentences_index.get((verb, key, tense))
    blanked = blank_out(entry["sentence"], correct_form) if entry else None

    return {
        "verb": verb,
        "key": key,
        "tense": tense,
        "correct_form": correct_form,
        "choices": choices,
        "context": entry is not None and blanked is not None,
        "blanked_sentence": blanked,
        "translation": entry["translation"] if entry else None,
    }


def get_question_pool(tense, level, conjugations):
    verbs = get_verbs_for_tense(tense, conjugations, level)
    return [(v, key) for v in verbs for key, _ in PRONOUNS]


def build_quiz(tense, level, count, conjugations, sentences_index=None):
    if sentences_index is None:
        sentences_index = load_sentences()
    pool = get_question_pool(tense, level, conjugations)
    n = min(count, len(pool))
    chosen = random.sample(pool, n)
    return [build_question(verb, key, tense, conjugations, sentences_index) for verb, key in chosen]
