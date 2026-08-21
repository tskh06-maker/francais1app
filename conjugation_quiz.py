import json
import random
import unicodedata

from history import load_history, record_result, save_history
from settings import DEFAULT_STRICT_ACCENT

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

LEVELS = ["A1", "A2", "B1", "B2"]
LEVEL_LABELS = {"A1": "A1", "A2": "A2", "B1": "B1", "B2": "B2〜"}

# 活用グループの表示順とラベル
GROUP_ORDER = ["G7", "G6", "G5", "G4", "G1", "G1b", "G2", "G3a", "G3b", "G3c", "G3d", "G8"]
GROUP_LABELS = {
    "G1": "-er規則動詞",
    "G1b": "-er綴り変化動詞",
    "G2": "-ir規則動詞（issons型）",
    "G3a": "-ir不規則（dormir型）",
    "G3b": "venir/tenir系",
    "G3c": "ouvrir系",
    "G3d": "courir/mourir/acquérir系",
    "G4": "-re規則動詞",
    "G5": "-re不規則動詞",
    "G6": "-oir系動詞",
    "G7": "完全不規則動詞",
    "G8": "再帰動詞",
}

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

# 再帰動詞(G8)用: 主語代名詞ごとの再帰代名詞と母音の前のエリジオン形
REFLEXIVE_PRONOUNS = {
    "je": "me",
    "tu": "te",
    "il_elle": "se",
    "nous": "nous",
    "vous": "vous",
    "ils": "se",
}
REFLEXIVE_ELISIONS = {"me": "m'", "te": "t'", "se": "s'"}

VOWEL_START = tuple("aeiouâàéèêëîïôùûühAEIOUÂÀÉÈÊËÎÏÔÙÛÜH")


def build_full_form(verb, key, tense, conjugations):
    """実際に文中に現れるべき活用形を返す（再帰動詞は再帰代名詞込み）。"""
    base_form = conjugations[verb][tense][key]
    if not conjugations[verb].get("reflexive", False):
        return base_form
    pronoun = REFLEXIVE_PRONOUNS[key]
    if base_form.startswith(VOWEL_START) and pronoun in REFLEXIVE_ELISIONS:
        return f"{REFLEXIVE_ELISIONS[pronoun]}{base_form}"
    return f"{pronoun} {base_form}"


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


def strip_reflexive(text, key):
    """再帰代名詞(me/te/se/nous/vous/se)を取り除く。見つかったかどうかも返す。"""
    pronoun = REFLEXIVE_PRONOUNS[key]
    prefixes = [pronoun + " "]
    if pronoun in REFLEXIVE_ELISIONS:
        prefixes.append(REFLEXIVE_ELISIONS[pronoun])
    for prefix in prefixes:
        if text.startswith(prefix):
            return text[len(prefix):], True
    return text, False


def grade_pronoun_answer(user_answer, key, correct_form, reflexive=False):
    """1人称分の解答を採点し、'○'/'△'/'×' を返す。"""
    normalized = normalize(user_answer)
    if reflexive:
        # nous/vousは主語代名詞と再帰代名詞が同じ綴りなので、まず再帰代名詞だけの
        # 表記("nous lavons")を試し、だめなら主語代名詞つき("je me lave")を試す。
        text, has_reflexive = strip_reflexive(normalized, key)
        if not has_reflexive:
            text, has_reflexive = strip_reflexive(strip_pronoun(normalized, key), key)
        if not has_reflexive:
            return "×"
    else:
        text = strip_pronoun(normalized, key)
    correct_norm = normalize(correct_form)
    if text == correct_norm:
        return "○"
    if strip_accents(text) == strip_accents(correct_norm):
        return "△"
    return "×"


def ask_conjugation_question(
    verb, correct_forms, meaning=None, tense="présent", reflexive=False, strict_accent=DEFAULT_STRICT_ACCENT
):
    answers = {key: None for key, _ in PRONOUNS}
    title = f"『{verb}』({meaning})" if meaning else f"『{verb}』"
    tense_label = TENSES.get(tense, tense)

    while True:
        print(f"\n{title} を{tense_label}で活用してください")
        if reflexive:
            print("  （再帰代名詞 me/te/se/nous/vous/se も含めて答えてください）")
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
        status = grade_pronoun_answer(user_answer, key, correct_forms[key], reflexive)
        if status == "○":
            print(f"  ○ {label}: {user_answer}")
        elif status == "△":
            if strict_accent:
                all_correct = False
            print(f"  △ {label}: {user_answer}   → おしい！アクセント記号が違います。正解は「{correct_forms[key]}」")
        else:
            all_correct = False
            expected = f"{REFLEXIVE_PRONOUNS[key]} {correct_forms[key]}" if reflexive else correct_forms[key]
            print(f"  × {label}: {user_answer}   → 正解は「{expected}」")

    return all_correct


def ask_compound_question(verb, info, meaning=None, tense="passé_composé", strict_accent=DEFAULT_STRICT_ACCENT):
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
        if strict_accent:
            all_correct = False
        print(f"  △ 過去分詞: {part_user}   → おしい！アクセント記号が違います。正解は「{info['participe']}」")
    else:
        all_correct = False
        print(f"  × 過去分詞: {part_user}   → 正解は「{info['participe']}」")

    return all_correct


def get_verbs_for_tense(tense, conjugations=None, level=None):
    conjugations = conjugations or load_conjugations()
    if tense in COMPOUND_TENSES:
        verbs = [v for v in conjugations if "participe_passé" in conjugations[v]]
    else:
        verbs = [v for v in conjugations if tense in conjugations[v]]
    if level:
        verbs = [v for v in verbs if conjugations[v].get("level") == level]
    return verbs


def ask_and_record(verb, conjugations, meanings, tense, history, strict_accent=DEFAULT_STRICT_ACCENT):
    if tense in COMPOUND_TENSES:
        correct = ask_compound_question(
            verb, conjugations[verb]["participe_passé"], meanings.get(verb), tense, strict_accent
        )
    else:
        reflexive = conjugations[verb].get("reflexive", False)
        correct = ask_conjugation_question(
            verb, conjugations[verb][tense], meanings.get(verb), tense, reflexive, strict_accent
        )
    record_result(history, verb, tense, correct)
    save_history(history)
    return correct


def run_conjugation_quiz(count=10, tense="présent", level=None, strict_accent=DEFAULT_STRICT_ACCENT):
    conjugations = load_conjugations()
    meanings = load_verb_meanings()
    history = load_history()
    verbs = get_verbs_for_tense(tense, conjugations, level)
    count = min(count, len(verbs))
    chosen = random.sample(verbs, count)

    score = 0
    for verb in chosen:
        if ask_and_record(verb, conjugations, meanings, tense, history, strict_accent):
            score += 1

    print(f"\n結果: {count}問中 {score}問全問正解！")


def get_verb_blocks(tense="présent", level=None, block_size=BLOCK_SIZE):
    verbs = get_verbs_for_tense(tense, level=level)
    return [verbs[i:i + block_size] for i in range(0, len(verbs), block_size)]


def run_conjugation_practice(verbs, tense="présent", strict_accent=DEFAULT_STRICT_ACCENT):
    conjugations = load_conjugations()
    meanings = load_verb_meanings()
    history = load_history()

    score = 0
    for verb in verbs:
        if ask_and_record(verb, conjugations, meanings, tense, history, strict_accent):
            score += 1

    print(f"\n結果: {len(verbs)}問中 {score}問全問正解！")
