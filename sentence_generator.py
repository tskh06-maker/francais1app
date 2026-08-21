"""
動詞×人称の文脈付き例文を Claude API で事前生成し、sentences.json に保存するバッチスクリプト。

使い方:
    python sentence_generator.py --groups G7               # G7グループのみ生成
    python sentence_generator.py --groups G7,G6            # 複数グループをまとめて生成
    python sentence_generator.py --groups G7 --dry-run     # 生成はせず対象件数のみ確認
    python sentence_generator.py --groups all               # 全動詞（必ず --dry-run で件数確認してから！）

必須設定:
    環境変数 ANTHROPIC_API_KEY か、.streamlit/secrets.toml に
        ANTHROPIC_API_KEY = "sk-ant-..."
    を設定しておくこと。APIキーはコード・gitに一切含めない。

方針:
    - 既に sentences.json にある (verb, person, tense) の組み合わせはスキップする（再実行しても重複生成しない）。
    - 生成した例文に、指定した活用形の文字列がそのまま含まれているか検証する。
      含まれていなければ最大2回リトライし、それでも失敗したら failed_sentences.json に記録してスキップする。
    - 一度に全件は生成しない。--groups で対象を絞り、グループ単位で段階的に実行すること。
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

try:
    import anthropic
except ImportError:
    print("エラー: anthropic パッケージがインストールされていません。")
    print("  venv/bin/pip install anthropic  を実行してください。")
    sys.exit(1)

from conjugation_quiz import (
    PRONOUNS,
    build_full_form,
    load_conjugations,
    load_verb_meanings,
)

MODEL = "claude-haiku-4-5"
DEFAULT_TENSE = "présent"
SENTENCES_PATH = "sentences.json"
FAILED_PATH = "failed_sentences.json"
MAX_ATTEMPTS = 3  # 初回 + リトライ2回
SLEEP_BETWEEN_CALLS = 0.4  # レート制限対策の簡易ウェイト（秒）
SAVE_EVERY = 10  # 何件ごとに途中保存するか

PERSON_LABELS = {
    "je": "私 (je) — 一人称単数",
    "tu": "あなた (tu) — 二人称単数、親しい間柄",
    "il_elle": "彼/彼女 (il / elle) — 三人称単数。人名や名詞に置き換えてもよい",
    "nous": "私たち (nous) — 一人称複数",
    "vous": "あなたたち、または丁寧な『あなた』(vous) — 二人称複数/敬称",
    "ils": "彼ら/彼女ら (ils / elles) — 三人称複数。人名や名詞に置き換えてもよい",
}

SYSTEM_PROMPT = (
    "あなたはフランス語学習教材の例文作成者です。"
    "指定された活用形を必ずそのまま含む、自然でシンプルなフランス語の例文と、"
    "その自然な日本語訳を生成します。"
)

SENTENCE_SCHEMA = {
    "type": "object",
    "properties": {
        "sentence": {"type": "string", "description": "指定の活用形を含むフランス語の例文"},
        "translation": {"type": "string", "description": "その例文の自然な日本語訳"},
    },
    "required": ["sentence", "translation"],
    "additionalProperties": False,
}


def get_api_key():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    secrets_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), ".streamlit", "secrets.toml"
    )
    if os.path.exists(secrets_path):
        text = open(secrets_path, encoding="utf-8").read()
        m = re.search(r'ANTHROPIC_API_KEY\s*=\s*"([^"]+)"', text)
        if m:
            return m.group(1)
    return None


def load_json(path):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_reflexive_ambiguous_person(key, full_form):
    """再帰動詞のnous/vousは主語代名詞と再帰代名詞の綴りが同じなため、
    『nous lavons』のような非再帰的な文でも活用形の文字列一致だけは通ってしまう。
    そのため生成・検証の両方で特別扱いが必要かどうかを判定する。"""
    return key in ("nous", "vous") and full_form.startswith(f"{key} ")


def build_prompt(verb, meaning, key, full_form):
    person_label = PERSON_LABELS[key]
    meaning_part = f"（意味: {meaning}）" if meaning else ""
    extra_condition = ""
    if is_reflexive_ambiguous_person(key, full_form):
        extra_condition = (
            f"- これは再帰動詞で、主語代名詞と再帰代名詞がどちらも「{key}」という同じ綴りになります。"
            f"「{key} {key} ...」のように「{key}」を2回使った再帰構文にしてください"
            f"（例: 「Nous nous lavons les mains avant de manger.」）。"
            f"「{key}」が1回だけの非再帰的な文（例: 「Nous lavons nos mains.」）にはしないこと。\n"
        )
    return (
        f"動詞: {verb}{meaning_part}\n"
        f"主語の人称: {person_label}\n"
        f"活用形: {full_form}\n\n"
        f"上記の活用形「{full_form}」をそのまま含む、自然なフランス語の例文を1文作成し、"
        f"その日本語訳も付けてください。\n"
        f"条件:\n"
        f"- 例文には「{full_form}」という文字列を一字一句そのまま含めること（大文字小文字はそのままでよい）。\n"
        f"{extra_condition}"
        f"- 主語は上記の人称に対応させること（代名詞そのものでも、対応する名詞・人名でもよい）。\n"
        f"- フランス語学習者(CEFR B1程度)が理解しやすい、日常的で自然な内容にすること。\n"
        f"- 日本語訳は自然で分かりやすい日本語にすること。"
    )


def generate_sentence(client, verb, meaning, key, full_form):
    prompt = build_prompt(verb, meaning, key, full_form)
    response = client.messages.create(
        model=MODEL,
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        output_config={"format": {"type": "json_schema", "schema": SENTENCE_SCHEMA}},
    )
    text = next(b.text for b in response.content if b.type == "text")
    data = json.loads(text)
    return data["sentence"].strip(), data["translation"].strip()


def validate(sentence, full_form, key=None):
    # 文頭で活用形が大文字になるケース（例: "Voyons ce film..."）を正しく許容するため大文字小文字を無視する
    sentence_l = sentence.lower()
    if full_form.lower() not in sentence_l:
        return False
    if is_reflexive_ambiguous_person(key, full_form):
        # 「nous lavons nos mains」のような非再帰的な文を弾くため、
        # 主語代名詞＋再帰代名詞で2回出現していることを要求する
        if sentence_l.count(key) < 2:
            return False
    return True


def already_done(existing, verb, key, tense):
    return any(
        e["verb"] == verb and e["person"] == key and e.get("tense", DEFAULT_TENSE) == tense
        for e in existing
    )


def remove_matching(items, verb, key, tense):
    items[:] = [
        e for e in items if not (e["verb"] == verb and e["person"] == key and e.get("tense", DEFAULT_TENSE) == tense)
    ]


def process_verb_person(client, verb, meaning, key, tense, conjugations, existing, failed):
    full_form = build_full_form(verb, key, tense, conjugations)
    last_sentence = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            sentence, translation = generate_sentence(client, verb, meaning, key, full_form)
        except anthropic.RateLimitError:
            wait = 5 * attempt
            print(f"    レート制限。{wait}秒待機してリトライします...")
            time.sleep(wait)
            continue
        except (anthropic.APIStatusError, anthropic.APIConnectionError) as e:
            print(f"    APIエラー(試行{attempt}/{MAX_ATTEMPTS}): {e}")
            time.sleep(2)
            continue
        except (json.JSONDecodeError, KeyError, StopIteration) as e:
            print(f"    応答の解析に失敗(試行{attempt}/{MAX_ATTEMPTS}): {e}")
            time.sleep(2)
            continue

        last_sentence = sentence
        if validate(sentence, full_form, key):
            remove_matching(existing, verb, key, tense)
            remove_matching(failed, verb, key, tense)
            existing.append(
                {
                    "verb": verb,
                    "person": key,
                    "tense": tense,
                    "conjugated_form": full_form,
                    "sentence": sentence,
                    "translation": translation,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "validated": True,
                }
            )
            return True

        time.sleep(SLEEP_BETWEEN_CALLS)

    remove_matching(failed, verb, key, tense)
    failed.append(
        {
            "verb": verb,
            "person": key,
            "tense": tense,
            "conjugated_form": full_form,
            "reason": (
                f"{MAX_ATTEMPTS}回試行しても活用形が例文に含まれなかった "
                f"(最後の出力: {last_sentence!r})"
            ),
        }
    )
    return False


def collect_target_verbs(conjugations, groups, tense):
    if groups == ["all"]:
        return [v for v in conjugations if tense in conjugations[v]]
    return [
        v
        for v in conjugations
        if conjugations[v].get("conjugationGroup") in groups and tense in conjugations[v]
    ]


def run(groups, tense, dry_run, force):
    conjugations = load_conjugations()
    meanings = load_verb_meanings()

    target_verbs = collect_target_verbs(conjugations, groups, tense)
    if not target_verbs:
        print("対象の動詞が見つかりませんでした。グループ名・時制を確認してください。")
        return

    existing = load_json(SENTENCES_PATH)
    failed = load_json(FAILED_PATH)

    todo = [
        (verb, key)
        for verb in target_verbs
        for key, _ in PRONOUNS
        if force or not already_done(existing, verb, key, tense)
    ]
    total = len(todo)

    print(f"対象グループ: {groups} / 時制: {tense}" + ("（--force: 既存分も再生成）" if force else ""))
    print(f"対象動詞数: {len(target_verbs)}語 / {'対象組み合わせ' if force else '未生成の組み合わせ'}: {total}件")

    if dry_run:
        print("(--dry-run のため実際の生成は行いません)")
        return
    if total == 0:
        print("すべて生成済みです。")
        return

    api_key = get_api_key()
    if not api_key:
        print(
            "エラー: ANTHROPIC_API_KEY が設定されていません。"
            "環境変数か .streamlit/secrets.toml に設定してください。"
        )
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    success_count = 0
    fail_count = 0
    for i, (verb, key) in enumerate(todo, start=1):
        ok = process_verb_person(client, verb, meanings.get(verb), key, tense, conjugations, existing, failed)
        if ok:
            success_count += 1
        else:
            fail_count += 1

        mark = "○" if ok else "×"
        group_label = conjugations[verb].get("conjugationGroup", "?")
        print(f"  [{i}/{total}] {mark} {verb} ({key}) [{group_label}]")

        if i % SAVE_EVERY == 0:
            save_json(SENTENCES_PATH, existing)
            save_json(FAILED_PATH, failed)

        time.sleep(SLEEP_BETWEEN_CALLS)

    save_json(SENTENCES_PATH, existing)
    save_json(FAILED_PATH, failed)

    print(f"\n{groups}: {total}/{total}件完了（成功 {success_count}件 / 失敗 {fail_count}件）")
    if fail_count:
        print(f"失敗した組み合わせは {FAILED_PATH} を参照してください。")


def main():
    parser = argparse.ArgumentParser(description="動詞×人称の例文をAPIで事前生成する")
    parser.add_argument(
        "--groups",
        type=str,
        default="",
        help="対象グループ（例: G7 または G7,G6）。全動詞対象なら 'all'",
    )
    parser.add_argument("--tense", type=str, default=DEFAULT_TENSE, help="対象の時制（デフォルト: présent）")
    parser.add_argument("--dry-run", action="store_true", help="対象件数のみ表示し、生成は行わない")
    parser.add_argument(
        "--force", action="store_true", help="既に生成済みの組み合わせも再生成して上書きする"
    )
    args = parser.parse_args()

    if not args.groups:
        print("エラー: --groups を指定してください（例: --groups G7 、全件なら --groups all）")
        sys.exit(1)

    groups = ["all"] if args.groups.strip().lower() == "all" else [g.strip() for g in args.groups.split(",")]
    run(groups, args.tense, args.dry_run, args.force)


if __name__ == "__main__":
    main()
