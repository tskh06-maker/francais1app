import json
import random

POS_LABELS = {
    "verbe": "動詞",
    "nom": "名詞",
    "adjectif": "形容詞",
    "adverbe": "副詞",
}


def load_words(path="words.json"):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def make_choices(correct_word, category_words):
    others = [w["ja"] for w in category_words if w["ja"] != correct_word["ja"]]
    wrong_choices = random.sample(others, 3)
    choices = wrong_choices + [correct_word["ja"]]
    random.shuffle(choices)
    return choices


def ask_question(word, category_words):
    choices = make_choices(word, category_words)
    print(f"\n『{word['fr']}』の意味は？")
    for i, choice in enumerate(choices, start=1):
        print(f"  {i}. {choice}")

    answer_index = choices.index(word["ja"]) + 1

    while True:
        user_input = input("番号を入力してください (1-4): ")
        if user_input in ("1", "2", "3", "4"):
            break
        print("1〜4の数字で入力してください。")

    if int(user_input) == answer_index:
        print("正解！")
        return True
    else:
        print(f"不正解… 正解は {answer_index}. {word['ja']} でした。")
        return False


def run_quiz(pos=None, count=10):
    all_words = load_words()
    available = [w for w in all_words if pos is None or w["pos"] == pos]
    count = min(count, len(available))
    words = random.sample(available, count)

    score = 0
    for word in words:
        # 選択肢は同じ品詞の単語だけから作る（動詞の問題に名詞の意味が混ざらないように）
        category_words = [w for w in all_words if w["pos"] == word["pos"]]
        if ask_question(word, category_words):
            score += 1

    print(f"\n結果: {len(words)}問中 {score}問正解！")
