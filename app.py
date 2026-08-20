import random

import streamlit as st

from conjugation_quiz import (
    AUXILIARIES,
    COMPOUND_TENSES,
    PRONOUNS,
    TENSES,
    get_verb_blocks,
    get_verbs_for_tense,
    load_conjugations,
    load_verb_meanings,
    normalize,
    strip_accents,
    strip_pronoun,
)
from history import get_review_verbs, get_stats, record_result
from quiz import POS_LABELS, load_words, make_choices
from styles import inject_custom_css, render_conjugation_table_html, render_hero, render_ring

CATEGORIES = ["verbe", "nom", "adjectif", "adverbe"]

st.set_page_config(page_title="フランス語学習アプリ", page_icon="🇫🇷", layout="centered")
inject_custom_css()

defaults = {
    "screen": "home",
    "word_list": [],
    "word_index": 0,
    "word_score": 0,
    "word_choices": None,
    "word_answered": False,
    "conj_tense": "présent",
    "conj_verbs": [],
    "conj_index": 0,
    "conj_score": 0,
    "conj_graded": False,
    "conj_results": None,
    "conj_wrong_verbs": [],
    "history_data": {},
}
for key, value in defaults.items():
    st.session_state.setdefault(key, value)


def go(screen):
    st.session_state.screen = screen
    st.rerun()


def start_conj_session(tense, verbs):
    st.session_state.conj_verbs = verbs
    st.session_state.conj_tense = tense
    st.session_state.conj_index = 0
    st.session_state.conj_score = 0
    st.session_state.conj_graded = False
    st.session_state.conj_results = None
    st.session_state.conj_wrong_verbs = []
    go("conj_quiz")


with st.sidebar:
    if st.button("🏠 ホームに戻る", use_container_width=True):
        go("home")

if st.session_state.screen == "home":
    render_hero("🇫🇷 フランス語学習アプリ", "動詞の活用を、練習・クイズ・復習でしっかり身につける")
else:
    st.markdown("##### 🇫🇷 フランス語学習アプリ")

# ---------- ホーム ----------
if st.session_state.screen == "home":
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown('<div class="card-icon">📝</div>', unsafe_allow_html=True)
            st.markdown('<div class="card-title">動詞活用</div>', unsafe_allow_html=True)
            st.markdown('<div class="card-caption">練習・クイズ・復習で活用をマスター</div>', unsafe_allow_html=True)
            if st.button("動詞活用（練習・クイズ）", use_container_width=True):
                go("conj_setup")
    with col2:
        with st.container(border=True):
            st.markdown('<div class="card-icon">🔤</div>', unsafe_allow_html=True)
            st.markdown('<div class="card-title">単語クイズ</div>', unsafe_allow_html=True)
            st.markdown('<div class="card-caption">名詞・形容詞などは今後追加予定</div>', unsafe_allow_html=True)
            st.button("単語クイズ（準備中）", use_container_width=True, disabled=True)

    col3, col4 = st.columns(2)
    with col3:
        with st.container(border=True):
            st.markdown('<div class="card-icon">📖</div>', unsafe_allow_html=True)
            st.markdown('<div class="card-title">動詞一覧</div>', unsafe_allow_html=True)
            st.markdown('<div class="card-caption">登録済みの動詞と活用表を検索・閲覧</div>', unsafe_allow_html=True)
            if st.button("登録されている動詞一覧を見る", use_container_width=True):
                go("verb_list")
    with col4:
        with st.container(border=True):
            st.markdown('<div class="card-icon">📊</div>', unsafe_allow_html=True)
            st.markdown('<div class="card-title">学習記録</div>', unsafe_allow_html=True)
            st.markdown('<div class="card-caption">正答率と復習リストを確認</div>', unsafe_allow_html=True)
            if st.button("学習記録を見る", use_container_width=True):
                go("history_view")


# ---------- 動詞一覧 ----------
elif st.session_state.screen == "verb_list":
    verbs = [w["fr"] for w in load_words() if w["pos"] == "verbe"]
    meanings = load_verb_meanings()
    conjugations = load_conjugations()
    st.subheader(f"登録されている動詞一覧（{len(verbs)}語）")
    st.caption("動詞をクリックすると活用表が開きます。être動詞の複合過去・大過去は、主語の性・数による過去分詞の一致を省略し、男性単数形で表示しています。")

    query = st.text_input("動詞を検索（原形または意味）", placeholder="例: aller、行く")

    pronoun_words = {"je": "je", "tu": "tu", "il_elle": "il/elle", "nous": "nous", "vous": "vous", "ils": "ils"}
    vowels = "aeiouyàâäéèêëîïôöùûüh"

    def compound_form(aux_forms, key, participe):
        aux_form = aux_forms[key]
        if key == "je":
            pronoun = "j’" if aux_form[:1].lower() in vowels else "je "
        else:
            pronoun = pronoun_words[key] + " "
        return f"{pronoun}{aux_form} {participe}"

    if query.strip():
        q_norm = strip_accents(query.strip().lower())
        matched = [
            v for v in verbs if q_norm in strip_accents(v.lower()) or query.strip() in meanings.get(v, "")
        ]
        st.caption(f"検索結果: {len(matched)}件")
    else:
        matched = verbs

    for verb in matched:
        info = conjugations[verb]
        with st.expander(f"{verb} — {meanings.get(verb, '')}"):
            présent = info["présent"]
            imparfait = info["imparfait"]
            participe_info = info["participe_passé"]
            aux = participe_info["auxiliaire"]
            participe = participe_info["participe"]
            aux_présent = conjugations[aux]["présent"]
            aux_imparfait = conjugations[aux]["imparfait"]

            st.markdown(
                f'<span class="badge">助動詞: {aux}</span><span class="badge">過去分詞: {participe}</span>',
                unsafe_allow_html=True,
            )

            pronoun_rows = [
                (
                    label,
                    présent[key],
                    imparfait[key],
                    compound_form(aux_présent, key, participe),
                    compound_form(aux_imparfait, key, participe),
                )
                for key, label in PRONOUNS
            ]
            st.markdown(render_conjugation_table_html(pronoun_rows), unsafe_allow_html=True)


# ---------- 学習記録 ----------
elif st.session_state.screen == "history_view":
    st.subheader("学習記録")
    history = st.session_state.history_data
    stats = get_stats(history)

    if stats["total_attempts"] == 0:
        st.info("まだ記録がありません。動詞活用を練習・クイズしてみましょう。")
    else:
        accuracy = 100 * (stats["total_attempts"] - stats["total_wrong"]) / stats["total_attempts"]
        col1, col2, col3 = st.columns(3)
        with col1:
            with st.container(border=True):
                st.markdown(
                    render_ring(accuracy, "正答率", f"{stats['total_attempts']}回中"),
                    unsafe_allow_html=True,
                )
        with col2:
            with st.container(border=True):
                st.metric("挑戦回数", stats["total_attempts"])
        with col3:
            with st.container(border=True):
                st.metric("要復習", stats["review_count"])

        st.markdown("#### 時制ごとの復習リスト")
        meanings = load_verb_meanings()
        all_tense_labels = {**TENSES, **COMPOUND_TENSES}
        for tense, label in all_tense_labels.items():
            review_verbs = get_review_verbs(history, tense, get_verbs_for_tense(tense))
            with st.expander(f"{label}（{len(review_verbs)}語）"):
                if not review_verbs:
                    st.caption("復習が必要な動詞はありません。")
                else:
                    for verb in review_verbs:
                        st.markdown(f"- {verb}（{meanings.get(verb, '')}）")
                    if len(review_verbs) <= 10:
                        if st.button(f"{label}を復習する", key=f"review_start_{tense}", type="primary"):
                            start_conj_session(tense, review_verbs)
                    else:
                        review_count = st.segmented_control(
                            "問題数", [10, 20], format_func=lambda c: f"{c}問",
                            default=10, key=f"review_count_{tense}", label_visibility="collapsed",
                        ) or 10
                        if st.button(f"{label}を復習する", key=f"review_start_{tense}", type="primary"):
                            n = min(review_count, len(review_verbs))
                            start_conj_session(tense, random.sample(review_verbs, n))


# ---------- 単語クイズ: 設定 ----------
elif st.session_state.screen == "word_setup":
    st.subheader("単語クイズの設定")
    pos_choice = st.radio(
        "分野を選んでください",
        CATEGORIES + [None],
        format_func=lambda p: POS_LABELS.get(p, "すべて"),
    )
    count_choice = st.radio("問題数を選んでください", [10, 20], format_func=lambda c: f"{c}問")

    if st.button("スタート", type="primary"):
        all_words = load_words()
        available = [w for w in all_words if pos_choice is None or w["pos"] == pos_choice]
        n = min(count_choice, len(available))
        st.session_state.word_list = random.sample(available, n)
        st.session_state.word_index = 0
        st.session_state.word_score = 0
        st.session_state.word_choices = None
        st.session_state.word_answered = False
        go("word_quiz")


# ---------- 単語クイズ: 出題 ----------
elif st.session_state.screen == "word_quiz":
    words = st.session_state.word_list
    idx = st.session_state.word_index

    if idx >= len(words):
        go("word_result")

    word = words[idx]
    st.progress(idx / len(words))
    st.caption(f"問題 {idx + 1} / {len(words)}")
    st.markdown(f"### 『{word['fr']}』の意味は？")

    if st.session_state.word_choices is None:
        all_words = load_words()
        category_words = [w for w in all_words if w["pos"] == word["pos"]]
        st.session_state.word_choices = make_choices(word, category_words)
    choices = st.session_state.word_choices

    selected = st.radio(
        "選択肢",
        choices,
        index=None,
        key=f"word_radio_{idx}",
        disabled=st.session_state.word_answered,
        label_visibility="collapsed",
    )

    if not st.session_state.word_answered:
        if st.button("回答する", type="primary", disabled=selected is None):
            st.session_state.word_answered = True
            if selected == word["ja"]:
                st.session_state.word_score += 1
            st.rerun()
    else:
        if selected == word["ja"]:
            st.success("正解！")
        else:
            st.error(f"不正解… 正解は「{word['ja']}」でした。")
        next_label = "次へ" if idx + 1 < len(words) else "結果を見る"
        if st.button(next_label, type="primary"):
            st.session_state.word_index += 1
            st.session_state.word_choices = None
            st.session_state.word_answered = False
            st.rerun()


# ---------- 単語クイズ: 結果 ----------
elif st.session_state.screen == "word_result":
    st.subheader("結果")
    total = len(st.session_state.word_list)
    score = st.session_state.word_score
    with st.container(border=True):
        st.markdown(
            render_ring(100 * score / total if total else 0, "正答率", f"{total}問中 {score}問正解"),
            unsafe_allow_html=True,
        )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("もう一度", use_container_width=True):
            go("word_setup")
    with col2:
        if st.button("ホームに戻る", use_container_width=True):
            go("home")


# ---------- 動詞活用: 設定 ----------
elif st.session_state.screen == "conj_setup":
    st.subheader("動詞活用の設定")

    all_tense_labels = {**TENSES, **COMPOUND_TENSES}
    tense_keys = list(TENSES.keys()) + list(COMPOUND_TENSES.keys())

    MODE_LABELS = {"practice": "練習", "quiz": "クイズ", "review": "復習"}
    MODE_CAPTIONS = {
        "practice": "グループの動詞が順番に出ます",
        "quiz": "ランダムに出ます",
        "review": "間違えた動詞だけ出ます",
    }

    with st.container(border=True):
        st.markdown("**① 時制**")
        tense = st.segmented_control(
            "時制", tense_keys, format_func=lambda t: all_tense_labels[t],
            default=tense_keys[0], label_visibility="collapsed",
        ) or tense_keys[0]
        if tense in COMPOUND_TENSES:
            st.caption("助動詞（avoir/être）の選択と、過去分詞（être の場合は男性形）を答える形式です。")

    with st.container(border=True):
        st.markdown("**② モード**")
        mode = st.segmented_control(
            "モード", list(MODE_LABELS.keys()), format_func=lambda m: MODE_LABELS[m],
            default="practice", label_visibility="collapsed",
        ) or "practice"
        st.caption(MODE_CAPTIONS[mode])

    with st.container(border=True):
        st.markdown("**③ 内容を決めてスタート**")
        if mode == "quiz":
            count_choice = st.segmented_control(
                "問題数", [10, 20], format_func=lambda c: f"{c}問", default=10, label_visibility="collapsed",
            ) or 10
            if st.button("スタート", type="primary", use_container_width=True):
                verbs = get_verbs_for_tense(tense)
                n = min(count_choice, len(verbs))
                start_conj_session(tense, random.sample(verbs, n))
        elif mode == "review":
            history = st.session_state.history_data
            review_verbs = get_review_verbs(history, tense, get_verbs_for_tense(tense))
            if not review_verbs:
                st.info("復習する動詞はありません（間違えた記録がまだないか、すべて復習済みです）。")
            elif len(review_verbs) <= 10:
                st.caption(f"{len(review_verbs)}語が復習対象です。")
                if st.button("スタート", type="primary", use_container_width=True):
                    start_conj_session(tense, review_verbs)
            else:
                st.caption(f"{len(review_verbs)}語が復習対象です。問題数を選んでください。")
                review_count = st.segmented_control(
                    "問題数", [10, 20], format_func=lambda c: f"{c}問", default=10, label_visibility="collapsed",
                ) or 10
                if st.button("スタート", type="primary", use_container_width=True):
                    n = min(review_count, len(review_verbs))
                    start_conj_session(tense, random.sample(review_verbs, n))
        else:
            blocks = get_verb_blocks(tense)
            block_option_map = {}
            start = 1
            for block in blocks:
                end = start + len(block) - 1
                block_option_map[f"{start}〜{end}番目"] = (block, f"{block[0]} 〜 {block[-1]}")
                start = end + 1
            chosen_label = st.selectbox("練習する動詞のグループ", list(block_option_map.keys()))
            chosen_block, range_caption = block_option_map[chosen_label]
            st.caption(range_caption)
            if st.button("スタート", type="primary", use_container_width=True):
                start_conj_session(tense, chosen_block)


# ---------- 動詞活用: 出題 ----------
elif st.session_state.screen == "conj_quiz":
    verbs = st.session_state.conj_verbs
    idx = st.session_state.conj_index

    if idx >= len(verbs):
        go("conj_result")

    verb = verbs[idx]
    tense = st.session_state.conj_tense
    conjugations = load_conjugations()
    meanings = load_verb_meanings()
    meaning = meanings.get(verb, "")
    compound = tense in COMPOUND_TENSES
    all_tense_labels = {**TENSES, **COMPOUND_TENSES}

    st.progress((idx) / len(verbs))
    st.caption(f"{idx + 1} / {len(verbs)}")

    with st.container(border=True):
        st.markdown(f"### 『{verb}』（{meaning}）")
        st.caption(f"{all_tense_labels.get(tense, tense)}で活用してください")

        if compound:
            info = conjugations[verb]["participe_passé"]
            st.caption("être の場合は男性形で答えてください。全部入力し終わったら「採点する」を押してください。")

            st.segmented_control(
                "助動詞",
                AUXILIARIES,
                key=f"conj_aux_{idx}",
                disabled=st.session_state.conj_graded,
            )
            st.text_input("過去分詞", key=f"conj_part_{idx}", disabled=st.session_state.conj_graded)
        else:
            correct_forms = conjugations[verb][tense]
            st.caption("好きな人称から自由に入力できます。全部入力し終わったら「採点する」を押してください。")

            for i in range(0, len(PRONOUNS), 2):
                col1, col2 = st.columns(2)
                key1, label1 = PRONOUNS[i]
                key2, label2 = PRONOUNS[i + 1]
                with col1:
                    st.text_input(label1, key=f"conj_{idx}_{key1}", disabled=st.session_state.conj_graded)
                with col2:
                    st.text_input(label2, key=f"conj_{idx}_{key2}", disabled=st.session_state.conj_graded)

    if not st.session_state.conj_graded:
        if st.button("採点する", type="primary"):
            results = []
            all_correct = True

            if compound:
                aux_user = st.session_state.get(f"conj_aux_{idx}") or ""
                if aux_user == info["auxiliaire"]:
                    results.append(("助動詞", aux_user, info["auxiliaire"], "○"))
                else:
                    all_correct = False
                    results.append(("助動詞", aux_user, info["auxiliaire"], "×"))

                part_user = st.session_state.get(f"conj_part_{idx}", "") or ""
                part_norm = normalize(part_user)
                part_correct_norm = normalize(info["participe"])
                if part_norm == part_correct_norm:
                    results.append(("過去分詞", part_user, info["participe"], "○"))
                elif strip_accents(part_norm) == strip_accents(part_correct_norm):
                    all_correct = False
                    results.append(("過去分詞", part_user, info["participe"], "△"))
                else:
                    all_correct = False
                    results.append(("過去分詞", part_user, info["participe"], "×"))
            else:
                for key, label in PRONOUNS:
                    user_answer = st.session_state.get(f"conj_{idx}_{key}", "") or ""
                    user_norm = strip_pronoun(normalize(user_answer), key)
                    correct_norm = normalize(correct_forms[key])
                    if user_norm == correct_norm:
                        status = "○"
                    elif strip_accents(user_norm) == strip_accents(correct_norm):
                        status = "△"
                        all_correct = False
                    else:
                        status = "×"
                        all_correct = False
                    results.append((label, user_answer, correct_forms[key], status))

            st.session_state.conj_results = results
            st.session_state.conj_graded = True
            if all_correct:
                st.session_state.conj_score += 1
            else:
                st.session_state.conj_wrong_verbs.append(verb)

            record_result(st.session_state.history_data, verb, tense, all_correct)
            st.rerun()
    else:
        st.markdown("#### 採点結果")
        for label, user_answer, correct, status in st.session_state.conj_results:
            shown = user_answer if user_answer else "(未入力)"
            if status == "○":
                st.success(f"○ {label}: {shown}")
            elif status == "△":
                st.warning(f"△ {label}: {shown} → おしい！アクセント記号が違います。正解は「{correct}」")
            else:
                st.error(f"× {label}: {shown} → 正解は「{correct}」")

        next_label = "次の動詞へ" if idx + 1 < len(verbs) else "結果を見る"
        if st.button(next_label, type="primary"):
            st.session_state.conj_index += 1
            st.session_state.conj_graded = False
            st.session_state.conj_results = None
            st.rerun()


# ---------- 動詞活用: 結果 ----------
elif st.session_state.screen == "conj_result":
    st.subheader("結果")
    total = len(st.session_state.conj_verbs)
    score = st.session_state.conj_score
    with st.container(border=True):
        st.markdown(
            render_ring(100 * score / total if total else 0, "全問正解率", f"{total}問中 {score}問が全問正解"),
            unsafe_allow_html=True,
        )

    wrong_verbs = st.session_state.conj_wrong_verbs
    if wrong_verbs:
        meanings = load_verb_meanings()
        st.markdown("##### 間違えた動詞（自動的に復習リストに追加されました）")
        badges = "".join(f'<span class="badge">{v}　{meanings.get(v, "")}</span>' for v in wrong_verbs)
        st.markdown(f'<div style="line-height:2.4;">{badges}</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("もう一度", use_container_width=True):
            go("conj_setup")
    with col2:
        if st.button("ホームに戻る", use_container_width=True):
            go("home")
