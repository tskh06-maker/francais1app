import random

import requests
import streamlit as st

from conjugation_quiz import (
    AUXILIARIES,
    COMPOUND_TENSES,
    GROUP_LABELS,
    GROUP_ORDER,
    LEVEL_LABELS,
    LEVELS,
    PRONOUNS,
    REFLEXIVE_PRONOUNS,
    TENSES,
    get_verb_blocks,
    get_verbs_for_tense,
    grade_pronoun_answer,
    load_conjugations,
    load_verb_meanings,
    normalize,
    strip_accents,
)
import cloud_history
from context_quiz import build_quiz as build_context_quiz
from context_quiz import load_sentences
from history import get_review_verbs, get_stats, record_result
from quiz import load_words, make_choices
from settings import DEFAULT_STRICT_ACCENT, STRICT_ACCENT_LABELS
from styles import inject_custom_css, render_conjugation_table_html, render_hero, render_ring

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
    "strict_accent": DEFAULT_STRICT_ACCENT,
    "context_questions": [],
    "context_index": 0,
    "context_score": 0,
    "context_selected": None,
    "context_answered": False,
    "context_wrong_verbs": [],
    "auth_uid": None,
    "auth_email": None,
    "auth_id_token": None,
    "auth_refresh_token": None,
}
for key, value in defaults.items():
    st.session_state.setdefault(key, value)


def go(screen):
    st.session_state.screen = screen
    st.rerun()


def sync_history_if_logged_in():
    """ログイン中ならFirestoreへ学習記録を保存する。失敗してもクイズは止めない。"""
    if not st.session_state.auth_uid:
        return
    try:
        id_token, refresh_token = cloud_history.save_history(
            st.session_state.auth_uid,
            st.session_state.auth_id_token,
            st.session_state.auth_refresh_token,
            st.session_state.history_data,
        )
        st.session_state.auth_id_token = id_token
        st.session_state.auth_refresh_token = refresh_token
    except cloud_history.CloudAuthError:
        st.toast("学習記録のクラウド保存に失敗しました。次回の回答時に再度お試しします。", icon="⚠️")


def logout():
    st.session_state.auth_uid = None
    st.session_state.auth_email = None
    st.session_state.auth_id_token = None
    st.session_state.auth_refresh_token = None
    st.session_state.history_data = {}


def start_conj_session(tense, verbs):
    st.session_state.conj_verbs = verbs
    st.session_state.conj_tense = tense
    st.session_state.conj_index = 0
    st.session_state.conj_score = 0
    st.session_state.conj_graded = False
    st.session_state.conj_results = None
    st.session_state.conj_wrong_verbs = []
    go("conj_quiz")


def start_context_quiz_session(tense, level, count):
    conjugations = load_conjugations()
    sentences_index = load_sentences()
    questions = build_context_quiz(tense, level, count, conjugations, sentences_index)
    st.session_state.context_questions = questions
    st.session_state.context_index = 0
    st.session_state.context_score = 0
    st.session_state.context_selected = None
    st.session_state.context_answered = False
    st.session_state.context_wrong_verbs = []
    go("context_quiz")


def get_formspree_url():
    try:
        return st.secrets.get("formspree_url")
    except Exception:
        return None


with st.sidebar:
    if st.button("🏠 ホームに戻る", use_container_width=True):
        go("home")
    if st.button("📝 動詞活用", use_container_width=True):
        go("conj_setup")
    if st.button("🔤 単語クイズ", use_container_width=True):
        go("word_setup")
    if st.button("📖 動詞一覧", use_container_width=True):
        go("verb_list")
    if st.button("📊 学習記録", use_container_width=True):
        go("history_view")
    if st.button("⚙️ 設定", use_container_width=True):
        go("settings")

    st.divider()
    if st.session_state.auth_uid:
        st.caption(f"ログイン中: {st.session_state.auth_email}")
        if st.button("ログアウト", use_container_width=True):
            logout()
            go("home")
    else:
        if st.button("🔐 ログイン", use_container_width=True):
            go("account")

if st.session_state.screen == "home":
    render_hero("🇫🇷 フランス語学習アプリ", "動詞の活用を、練習・クイズ・復習でしっかり身につける")
else:
    top_col1, top_col2 = st.columns([1, 4])
    with top_col1:
        if st.button("← ホーム", key="top_home_button"):
            go("home")
    with top_col2:
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
            st.markdown('<div class="card-caption">動詞の意味を4択で確認（名詞・形容詞などは今後追加予定）</div>', unsafe_allow_html=True)
            if st.button("単語クイズ（動詞）", use_container_width=True):
                go("word_setup")

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

    with st.expander("💬 ご意見・ご感想"):
        with st.form("feedback_form", clear_on_submit=True):
            feedback_message = st.text_area("メッセージ", height=80, label_visibility="collapsed", placeholder="バグ報告やご要望など")
            feedback_submitted = st.form_submit_button("送信する", type="primary")

        if feedback_submitted:
            message_clean = feedback_message.strip()
            if not message_clean:
                st.warning("メッセージを入力してください。")
            else:
                endpoint = get_formspree_url()
                if not endpoint:
                    st.error("送信先が未設定です。管理者にお問い合わせください。")
                else:
                    try:
                        response = requests.post(
                            endpoint,
                            data={"message": message_clean},
                            headers={"Accept": "application/json"},
                            timeout=10,
                        )
                        if response.ok:
                            st.success("送信しました。ありがとうございます！")
                        else:
                            st.error("送信に失敗しました。時間をおいて再度お試しください。")
                    except requests.RequestException:
                        st.error("送信に失敗しました。時間をおいて再度お試しください。")


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
    reflexive_elisions = {"me": "m’", "te": "t’", "se": "s’"}

    def reflexive_prefix(key, next_word):
        pronoun = REFLEXIVE_PRONOUNS[key]
        if pronoun in reflexive_elisions and next_word[:1].lower() in vowels:
            return reflexive_elisions[pronoun]
        return pronoun + " "

    def tense_form_display(forms, key, reflexive):
        form = forms[key]
        return (reflexive_prefix(key, form) + form) if reflexive else form

    def compound_form(aux_forms, key, participe, reflexive=False):
        aux_form = aux_forms[key]
        if key == "je":
            # 再帰動詞では je の直後は常に me/m'（子音扱い）なので je はエリジオンしない
            if reflexive:
                pronoun = "je "
            else:
                pronoun = "j’" if aux_form[:1].lower() in vowels else "je "
        else:
            pronoun = pronoun_words[key] + " "
        reflexive_part = reflexive_prefix(key, aux_form) if reflexive else ""
        return f"{pronoun}{reflexive_part}{aux_form} {participe}"

    if query.strip():
        q_norm = strip_accents(query.strip().lower())
        matched = [
            v for v in verbs if q_norm in strip_accents(v.lower()) or query.strip() in meanings.get(v, "")
        ]
        st.caption(f"検索結果: {len(matched)}件")
        grouped = False
    else:
        matched = sorted(verbs, key=lambda v: GROUP_ORDER.index(conjugations[v]["conjugationGroup"]))
        grouped = True

    previous_group = None
    for verb in matched:
        info = conjugations[verb]
        group = info.get("conjugationGroup")

        if grouped and group != previous_group:
            group_count = sum(1 for v in matched if conjugations[v].get("conjugationGroup") == group)
            if previous_group is not None:
                st.divider()
            st.markdown(f"##### {GROUP_LABELS.get(group, group)}（{group_count}語）")
            previous_group = group

        reflexive = info.get("reflexive", False)
        with st.expander(f"{verb} — {meanings.get(verb, '')}"):
            présent = info["présent"]
            imparfait = info["imparfait"]
            participe_info = info["participe_passé"]
            aux = participe_info["auxiliaire"]
            participe = participe_info["participe"]
            aux_présent = conjugations[aux]["présent"]
            aux_imparfait = conjugations[aux]["imparfait"]

            st.markdown(
                f'<span class="badge">{GROUP_LABELS.get(group, group)}</span>'
                f'<span class="badge">助動詞: {aux}</span><span class="badge">過去分詞: {participe}</span>',
                unsafe_allow_html=True,
            )

            pronoun_rows = [
                (
                    label,
                    tense_form_display(présent, key, reflexive),
                    tense_form_display(imparfait, key, reflexive),
                    compound_form(aux_présent, key, participe, reflexive),
                    compound_form(aux_imparfait, key, participe, reflexive),
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


# ---------- 設定 ----------
elif st.session_state.screen == "settings":
    st.subheader("設定")

    with st.container(border=True):
        st.markdown("**アクセント記号の採点基準**")
        st.caption("動詞活用の採点で、アクセント記号だけが間違っている場合（例: e → é）の扱いを選べます。")
        accent_options = list(STRICT_ACCENT_LABELS.keys())
        current_index = accent_options.index(st.session_state.strict_accent)
        choice = st.radio(
            "アクセント記号の採点基準",
            accent_options,
            index=current_index,
            format_func=lambda v: STRICT_ACCENT_LABELS[v],
            label_visibility="collapsed",
        )
        if choice != st.session_state.strict_accent:
            st.session_state.strict_accent = choice
            st.rerun()
        st.caption("※ 「厳しめ」にすると、アクセント抜けも間違い扱いになり復習リストに追加されます。この設定はブラウザのセッション内でのみ有効です。")


# ---------- アカウント ----------
elif st.session_state.screen == "account":
    st.subheader("ログイン / 新規登録")
    st.caption("ログインすると学習記録がクラウドに保存され、ブラウザを閉じたり別の端末からでも記録を引き継げます。ログインしなくても今まで通り利用できます。")
    st.caption("※ 自動ログイン保持はしていません。ブラウザを閉じた場合は再度ログインが必要です。")

    def _apply_login(result):
        st.session_state.auth_uid = result["uid"]
        st.session_state.auth_email = result["email"]
        st.session_state.auth_id_token = result["id_token"]
        st.session_state.auth_refresh_token = result["refresh_token"]

        cloud_data, id_token, refresh_token = cloud_history.load_history(
            result["uid"], result["id_token"], result["refresh_token"]
        )
        st.session_state.auth_id_token = id_token
        st.session_state.auth_refresh_token = refresh_token

        if cloud_data:
            st.session_state.history_data = cloud_data
            st.info("クラウドに保存されていた学習記録を読み込みました。")
        elif st.session_state.history_data:
            sync_history_if_logged_in()
            st.info("これまでの学習記録をこのアカウントに保存しました。")

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("**ログイン**")
            with st.form("login_form"):
                login_email = st.text_input("メールアドレス", key="login_email")
                login_password = st.text_input("パスワード", type="password", key="login_password")
                login_submitted = st.form_submit_button("ログイン", type="primary", use_container_width=True)
            if login_submitted:
                try:
                    result = cloud_history.sign_in(login_email, login_password)
                    _apply_login(result)
                    go("home")
                except cloud_history.CloudAuthError as e:
                    st.error(str(e))

    with col2:
        with st.container(border=True):
            st.markdown("**新規登録**")
            with st.form("signup_form"):
                signup_email = st.text_input("メールアドレス", key="signup_email")
                signup_password = st.text_input(
                    "パスワード（6文字以上）", type="password", key="signup_password"
                )
                signup_submitted = st.form_submit_button("新規登録", type="primary", use_container_width=True)
            if signup_submitted:
                try:
                    result = cloud_history.sign_up(signup_email, signup_password)
                    _apply_login(result)
                    go("home")
                except cloud_history.CloudAuthError as e:
                    st.error(str(e))

    if st.button("ゲストとして続ける（ログインしない）"):
        go("home")


# ---------- 単語クイズ: 設定 ----------
elif st.session_state.screen == "word_setup":
    st.subheader("単語クイズの設定")
    st.caption("現在は動詞のみ対応しています（名詞・形容詞などは今後追加予定）。")
    pos_choice = "verbe"

    conjugations = load_conjugations()
    level_keys = [None] + LEVELS
    level = st.segmented_control(
        "レベル", level_keys, format_func=lambda lv: LEVEL_LABELS.get(lv, "すべて"), default=None,
    )
    available_preview = [
        w for w in load_words()
        if w["pos"] == pos_choice and (level is None or conjugations.get(w["fr"], {}).get("level") == level)
    ]
    st.caption(f"対象: {len(available_preview)}語")

    count_choice = st.segmented_control(
        "問題数", [10, 20], format_func=lambda c: f"{c}問", default=10, label_visibility="collapsed",
    ) or 10

    if st.button("スタート", type="primary", disabled=not available_preview):
        available = available_preview
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

    MODE_LABELS = {"practice": "練習", "quiz": "クイズ", "review": "復習", "context_quiz": "文脈クイズ"}
    MODE_CAPTIONS = {
        "practice": "グループの動詞が順番に出ます",
        "quiz": "ランダムに出ます",
        "review": "間違えた動詞だけ出ます",
        "context_quiz": "例文の穴埋めで活用形を4択から選びます（現在形・半過去のみ）",
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
        st.markdown("**② レベル**")
        level_keys = [None] + LEVELS
        level = st.segmented_control(
            "レベル", level_keys, format_func=lambda lv: LEVEL_LABELS.get(lv, "すべて"),
            default=None, label_visibility="collapsed",
        )
        level_verb_count = len(get_verbs_for_tense(tense, level=level))
        st.caption(f"対象: {level_verb_count}語")

    with st.container(border=True):
        st.markdown("**③ モード**")
        mode = st.segmented_control(
            "モード", list(MODE_LABELS.keys()), format_func=lambda m: MODE_LABELS[m],
            default="practice", label_visibility="collapsed",
        ) or "practice"
        st.caption(MODE_CAPTIONS[mode])

    with st.container(border=True):
        st.markdown("**④ 内容を決めてスタート**")
        if level_verb_count == 0:
            st.info("このレベル・時制の組み合わせに該当する動詞がありません。")
        elif mode == "quiz":
            count_choice = st.segmented_control(
                "問題数", [10, 20], format_func=lambda c: f"{c}問", default=10, label_visibility="collapsed",
            ) or 10
            if st.button("スタート", type="primary", use_container_width=True):
                verbs = get_verbs_for_tense(tense, level=level)
                n = min(count_choice, len(verbs))
                start_conj_session(tense, random.sample(verbs, n))
        elif mode == "review":
            history = st.session_state.history_data
            review_verbs = get_review_verbs(history, tense, get_verbs_for_tense(tense, level=level))
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
        elif mode == "context_quiz":
            if tense in COMPOUND_TENSES:
                st.info("文脈クイズは現在形・半過去のみ対応しています。①で時制を変更してください。")
            else:
                count_choice = st.segmented_control(
                    "問題数", [10, 20], format_func=lambda c: f"{c}問", default=10, label_visibility="collapsed",
                ) or 10
                if st.button("スタート", type="primary", use_container_width=True):
                    start_context_quiz_session(tense, level, count_choice)
        else:
            blocks = get_verb_blocks(tense, level=level)
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
    reflexive = conjugations[verb].get("reflexive", False)
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
            if reflexive:
                st.caption("再帰代名詞（me/te/se/nous/vous/se）も含めて答えてください。")

            for i in range(0, len(PRONOUNS), 2):
                col1, col2 = st.columns(2)
                key1, label1 = PRONOUNS[i]
                key2, label2 = PRONOUNS[i + 1]
                with col1:
                    placeholder1 = f"{REFLEXIVE_PRONOUNS[key1]} ..." if reflexive else ""
                    st.text_input(
                        label1, key=f"conj_{idx}_{key1}", disabled=st.session_state.conj_graded,
                        placeholder=placeholder1,
                    )
                with col2:
                    placeholder2 = f"{REFLEXIVE_PRONOUNS[key2]} ..." if reflexive else ""
                    st.text_input(
                        label2, key=f"conj_{idx}_{key2}", disabled=st.session_state.conj_graded,
                        placeholder=placeholder2,
                    )

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
                    if st.session_state.strict_accent:
                        all_correct = False
                    results.append(("過去分詞", part_user, info["participe"], "△"))
                else:
                    all_correct = False
                    results.append(("過去分詞", part_user, info["participe"], "×"))
            else:
                for key, label in PRONOUNS:
                    user_answer = st.session_state.get(f"conj_{idx}_{key}", "") or ""
                    status = grade_pronoun_answer(user_answer, key, correct_forms[key], reflexive)
                    if status == "×" or (status == "△" and st.session_state.strict_accent):
                        all_correct = False
                    expected = f"{REFLEXIVE_PRONOUNS[key]} {correct_forms[key]}" if reflexive else correct_forms[key]
                    results.append((label, user_answer, expected, status))

            st.session_state.conj_results = results
            st.session_state.conj_graded = True
            if all_correct:
                st.session_state.conj_score += 1
            else:
                st.session_state.conj_wrong_verbs.append(verb)

            record_result(st.session_state.history_data, verb, tense, all_correct)
            sync_history_if_logged_in()
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


# ---------- 動詞活用: 文脈クイズ ----------
elif st.session_state.screen == "context_quiz":
    questions = st.session_state.context_questions
    idx = st.session_state.context_index

    if idx >= len(questions):
        go("context_result")

    q = questions[idx]
    meanings = load_verb_meanings()
    meaning = meanings.get(q["verb"], "")
    person_label = dict(PRONOUNS)[q["key"]]

    st.progress(idx / len(questions))
    st.caption(f"問題 {idx + 1} / {len(questions)}")

    with st.container(border=True):
        st.markdown(f"### 『{q['verb']}』（{meaning}）")
        st.caption(f"{person_label} の活用形を選んでください")
        if q["context"]:
            st.markdown(f"#### {q['blanked_sentence']}")
            st.caption(f"訳: {q['translation']}")
        else:
            st.info("この組み合わせにはまだ例文がありません。活用形のみで出題します。")

    selected = st.radio(
        "選択肢",
        q["choices"],
        index=None,
        key=f"context_radio_{idx}",
        disabled=st.session_state.context_answered,
        label_visibility="collapsed",
    )

    if not st.session_state.context_answered:
        if st.button("回答する", type="primary", disabled=selected is None):
            st.session_state.context_answered = True
            st.session_state.context_selected = selected
            correct = selected == q["correct_form"]
            if correct:
                st.session_state.context_score += 1
            else:
                st.session_state.context_wrong_verbs.append(q["verb"])
            record_result(st.session_state.history_data, q["verb"], q["tense"], correct)
            sync_history_if_logged_in()
            st.rerun()
    else:
        if st.session_state.context_selected == q["correct_form"]:
            st.success("正解！")
        else:
            st.error(f"不正解… 正解は「{q['correct_form']}」でした。")
        next_label = "次へ" if idx + 1 < len(questions) else "結果を見る"
        if st.button(next_label, type="primary"):
            st.session_state.context_index += 1
            st.session_state.context_answered = False
            st.session_state.context_selected = None
            st.rerun()


# ---------- 動詞活用: 文脈クイズ結果 ----------
elif st.session_state.screen == "context_result":
    st.subheader("結果")
    total = len(st.session_state.context_questions)
    score = st.session_state.context_score
    with st.container(border=True):
        st.markdown(
            render_ring(100 * score / total if total else 0, "正答率", f"{total}問中 {score}問正解"),
            unsafe_allow_html=True,
        )

    wrong_verbs = list(dict.fromkeys(st.session_state.context_wrong_verbs))
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
