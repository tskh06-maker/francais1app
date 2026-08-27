"""ブラウザ内蔵の音声合成（Web Speech API）を使って、フランス語のテキストを
読み上げる機能を提供するモジュール。

音声ファイルの事前生成は行わない。表示中のテキストをその場で読み上げる方式なので、
動詞・名詞・形容詞など、今後どんな単語データが増えても追加コストなしで対応できる。

st.markdown(unsafe_allow_html=True) は onclick 等のイベント属性を取り除いてしまうため、
ボタン自体は通常の st.button として描画し、押されたテキストを session_state に記録する。
実際の読み上げ（JS実行）は render_speech_player() が画面に1回だけ置くiframeで行う。
これにより、動詞が何百語あってもiframeは常に1つで済む。
"""

import json

import streamlit as st
import streamlit.components.v1 as components

_PENDING_KEY = "_pending_speech_text"


def speak_button(text, button_key=None, label="▶️ 発音を聞く", use_container_width=False):
    """textを読み上げるボタンを描画する。押されたら実際の読み上げを予約する。"""
    if st.button(label, key=button_key or f"speak_{text}", use_container_width=use_container_width):
        st.session_state[_PENDING_KEY] = text


def render_speech_player(lang="fr-FR"):
    """画面（1スクリプト実行）につき1回だけ呼び出すこと。
    speak_button が予約したテキストがあれば、それを読み上げるiframeを描画する。"""
    text = st.session_state.pop(_PENDING_KEY, None)
    if not text:
        return

    safe_text = json.dumps(text)
    safe_lang = json.dumps(lang)
    html = f"""
    <script>
      if ("speechSynthesis" in window) {{
          var u = new SpeechSynthesisUtterance({safe_text});
          u.lang = {safe_lang};
          window.speechSynthesis.cancel();
          window.speechSynthesis.speak(u);
      }}
    </script>
    """
    components.html(html, height=0)
