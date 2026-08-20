import random

from conjugation_quiz import (
    COMPOUND_TENSES,
    TENSES,
    get_verb_blocks,
    get_verbs_for_tense,
    run_conjugation_practice,
    run_conjugation_quiz,
)
from history import get_review_verbs, load_history
from quiz import POS_LABELS, run_quiz

CATEGORIES = ["verbe", "nom", "adjectif", "adverbe"]


def choose(prompt, options):
    """options: [(value, label), ...] を表示して選ばせ、選んだ value を返す"""
    print(prompt)
    for i, (_, label) in enumerate(options, start=1):
        print(f"  {i}. {label}")

    valid_inputs = [str(i) for i in range(1, len(options) + 1)]
    while True:
        choice = input("番号を入力してください: ")
        if choice in valid_inputs:
            return options[int(choice) - 1][0]
        print("有効な番号を入力してください。")


if __name__ == "__main__":
    mode = choose("モードを選んでください", [
        ("word", "単語クイズ（4択）"),
        ("conjugation", "動詞活用"),
    ])

    if mode == "word":
        pos = choose("\n分野を選んでください", [(p, POS_LABELS[p]) for p in CATEGORIES] + [(None, "すべて")])
        count = choose("\n問題数を選んでください", [(10, "10問"), (20, "20問")])
        run_quiz(pos, count)
    else:
        tense_options = list(TENSES.items()) + list(COMPOUND_TENSES.items())
        tense = choose("\n時制を選んでください", tense_options)

        practice_or_quiz = choose("\n練習・クイズ・復習を選んでください", [
            ("practice", "練習（グループの動詞が順番に出る）"),
            ("quiz", "クイズ（ランダムに出る）"),
            ("review", "復習（間違えた動詞だけ）"),
        ])

        if practice_or_quiz == "quiz":
            count = choose("\n問題数を選んでください", [(10, "10問"), (20, "20問")])
            run_conjugation_quiz(count, tense)
        elif practice_or_quiz == "review":
            history = load_history()
            review_verbs = get_review_verbs(history, tense, get_verbs_for_tense(tense))
            if not review_verbs:
                print("\n復習する動詞はありません（間違えた記録がまだないか、すべて復習済みです）。")
            elif len(review_verbs) <= 10:
                run_conjugation_practice(review_verbs, tense)
            else:
                count = choose(
                    f"\n{len(review_verbs)}語が復習対象です。問題数を選んでください",
                    [(10, "10問"), (20, "20問")],
                )
                n = min(count, len(review_verbs))
                run_conjugation_practice(random.sample(review_verbs, n), tense)
        else:
            blocks = get_verb_blocks(tense)
            block_options = []
            start = 1
            for block in blocks:
                end = start + len(block) - 1
                block_options.append((block, f"{start}〜{end}番目 ({block[0]}〜{block[-1]})"))
                start = end + 1
            chosen_block = choose("\n練習する動詞のグループを選んでください", block_options)
            run_conjugation_practice(chosen_block, tense)
