import json
import random
import unicodedata

from history import load_history, record_result, save_history

TENSES = {
    "présent": "現在形",
    "imparfait": "半過去",
}

# 複合過去・大過去は「助動詞(avoir/être) + 過去分詞」の2問構成。
# どちらも動詞ごとの participe_passé データ（助動詞と男性単数形の過去分詞）を共有する。
COMPOUND_TENSES = {
    "passé_composé": "複合過去",
    "plus_que_parfait": "大過去",
}

AUXILIARIES = ["avoir", "être"]

BLOCK_SIZE = 10  # 動詞が増えてきたら100などに変更する

PRONOUNS = [
    ("je", "Je"),
    ("tu", "Tu"),
    ("il_elle", "Il/Elle"),
    ("nous", "Nous"),
    ("vous", "Vous"),
    ("ils", "Ils"),
]

PRONOUN_PREFIXES = {
    "je": ["j'", "je "],
    "tu": ["tu "],
    "il_elle": ["il/elle ", "il ", "elle "],
    "nous": ["nous "],
    "vous": ["vous "],
    "ils": ["ils ", "elles "],
}


def load_conjugations(path="conjugations.json"):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_verb_meanings(path="words.json"):
    with open(path, encoding="utf-8") as f:
        words = json.load(f)
    return {w["fr"]: w["ja"] for w in words if w["pos"] == "verbe"}


def normalize(text):
    return text.strip().lower().replace("’", "'")


def strip_accents(text):
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def strip_pronoun(text, key):
    for prefix in PRONOUN_PREFIXES.get(key, []):
        if text.startswith(prefix):
            return text[len(prefix):]
    return text


def ask_conjugation_question(verb, correct_forms, meaning=None, tense="présent"):
    answers = {key: None for key, _ in PRONOUNS}
    title = f"『{verb}』({meaning})" if meaning else f"『{verb}』"
    tense_label = TENSES.get(tense, tense)

    while True:
        print(f"\n{title} を{tense_label}で活用してください")
        for i, (key, label) in enumerate(PRONOUNS, start=1):
            shown = answers[key] if answers[key] is not None else "(未入力)"
            print(f"  {i}. {label:<7}: {shown}")

        choice = input("番号(1-6)を選んで入力、全部埋まったら 0 で採点: ").strip()

        if choice == "0":
            if all(answers[key] is not None for key, _ in PRONOUNS):
                break
            print("→ すべての人称を入力してから採点してください。\n")
            continue

        if choice in ("1", "2", "3", "4", "5", "6"):
            key, label = PRONOUNS[int(choice) - 1]
            answers[key] = input(f"  {label}: ")
        else:
            print("→ 1〜6の番号か、採点する場合は 0 を入力してください。\n")

    print("  --- 採点結果 ---")
    all_correct = True
    for key, label in PRONOUNS:
        user_answer = answers[key]
        user_norm = strip_pronoun(normalize(user_answer), key)
        correct_norm = normalize(correct_forms[key])
        if user_norm == correct_norm:
            print(f"  ○ {label}: {user_answer}")
        elif strip_accents(user_norm) == strip_accents(correct_norm):
            all_correct = False
            print(f"  △ {label}: {user_answer}   → おしい！アクセント記号が違います。正解は「{correct_forms[key]}」")
        else:
            all_correct = False
            print(f"  × {label}: {user_answer}   → 正解は「{correct_forms[key]}」")

    return all_correct


def ask_compound_question(verb, info, meaning=None, tense="passé_composé"):
    fields = [("auxiliaire", "助動詞 (avoir/être)"), ("participe", "過去分詞")]
    answers = {key: None for key, _ in fields}
    title = f"『{verb}』({meaning})" if meaning else f"『{verb}』"
    tense_label = COMPOUND_TENSES.get(tense, tense)

    while True:
        print(f"\n{title} を{tense_label}で活用してください（être の場合は男性形で答えてください）")
        for i, (key, label) in enumerate(fields, start=1):
            shown = answers[key] if answers[key] is not None else "(未入力)"
            print(f"  {i}. {label:<16}: {shown}")

        choice = input("番号(1-2)を選んで入力、全部埋まったら 0 で採点: ").strip()

        if choice == "0":
            if all(answers[key] is not None for key, _ in fields):
                break
            print("→ すべて入力してから採点してください。\n")
            continue

        if choice in ("1", "2"):
            key, label = fields[int(choice) - 1]
            answers[key] = input(f"  {label}: ")
        else:
            print("→ 1〜2の番号か、採点する場合は 0 を入力してください。\n")

    print("  --- 採点結果 ---")
    all_correct = True

    aux_user = answers["auxiliaire"]
    if strip_accents(normalize(aux_user)) == strip_accents(normalize(info["auxiliaire"])):
        print(f"  ○ 助動詞: {aux_user}")
    else:
        all_correct = False
        print(f"  × 助動詞: {aux_user}   → 正解は「{info['auxiliaire']}」")

    part_user = answers["participe"]
    part_norm = normalize(part_user)
    part_correct_norm = normalize(info["participe"])
    if part_norm == part_correct_norm:
        print(f"  ○ 過去分詞: {part_user}")
    elif strip_accents(part_norm) == strip_accents(part_correct_norm):
        all_correct = False
        print(f"  △ 過去分詞: {part_user}   → おしい！アクセント記号が違います。正解は「{info['participe']}」")
    else:
        all_correct = False
        print(f"  × 過去分詞: {part_user}   → 正解は「{info['participe']}」")

    return all_correct


def get_verbs_for_tense(tense, conjugations=None):
    conjugations = conjugations or load_conjugations()
    if tense in COMPOUND_TENSES:
        return [v for v in conjugations if "participe_passé" in conjugations[v]]
    return [v for v in conjugations if tense in conjugations[v]]


def ask_and_record(verb, conjugations, meanings, tense, history):
    if tense in COMPOUND_TENSES:
        correct = ask_compound_question(verb, conjugations[verb]["participe_passé"], meanings.get(verb), tense)
    else:
        correct = ask_conjugation_question(verb, conjugations[verb][tense], meanings.get(verb), tense)
    record_result(history, verb, tense, correct)
    save_history(history)
    return correct


def run_conjugation_quiz(count=10, tense="présent"):
    conjugations = load_conjugations()
    meanings = load_verb_meanings()
    history = load_history()
    verbs = get_verbs_for_tense(tense, conjugations)
    count = min(count, len(verbs))
    chosen = random.sample(verbs, count)

    score = 0
    for verb in chosen:
        if ask_and_record(verb, conjugations, meanings, tense, history):
            score += 1

    print(f"\n結果: {count}問中 {score}問全問正解！")


def get_verb_blocks(tense="présent", block_size=BLOCK_SIZE):
    verbs = get_verbs_for_tense(tense)
    return [verbs[i:i + block_size] for i in range(0, len(verbs), block_size)]


def run_conjugation_practice(verbs, tense="présent"):
    conjugations = load_conjugations()
    meanings = load_verb_meanings()
    history = load_history()

    score = 0
    for verb in verbs:
        if ask_and_record(verb, conjugations, meanings, tense, history):
            score += 1

    print(f"\n結果: {len(verbs)}問中 {score}問全問正解！")
