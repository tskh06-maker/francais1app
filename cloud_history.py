"""Firebase Authentication（メール/パスワード）とFirestoreをREST APIで直接叩き、
学習記録（history_data）をユーザーごとにクラウド保存するためのモジュール。

firebase-admin等の重い依存は使わず、既存のrequestsライブラリのみで完結させている。
Firestoreへのアクセスはユーザー自身のidTokenで行うため、Firestoreセキュリティルール
（users/{uid}を本人のみ読み書き可）が実際の防御境界になる。
"""

import json

import requests
import streamlit as st

IDENTITY_BASE = "https://identitytoolkit.googleapis.com/v1"
TOKEN_REFRESH_URL = "https://securetoken.googleapis.com/v1/token"
FIRESTORE_BASE = "https://firestore.googleapis.com/v1"

_ERROR_MESSAGES = {
    "EMAIL_EXISTS": "このメールアドレスは既に登録されています。",
    "EMAIL_NOT_FOUND": "メールアドレスまたはパスワードが正しくありません。",
    "INVALID_PASSWORD": "メールアドレスまたはパスワードが正しくありません。",
    "INVALID_LOGIN_CREDENTIALS": "メールアドレスまたはパスワードが正しくありません。",
    "WEAK_PASSWORD": "パスワードは6文字以上にしてください。",
    "INVALID_EMAIL": "メールアドレスの形式が正しくありません。",
    "TOO_MANY_ATTEMPTS_TRY_LATER": "試行回数が多すぎます。しばらく待ってから再度お試しください。",
}


class CloudAuthError(Exception):
    """サインアップ・サインインに失敗した際に、日本語の分かりやすいメッセージを持たせる例外。"""


def _web_api_key():
    try:
        return st.secrets["firebase_web_api_key"]
    except Exception:
        return None


def _project_id():
    try:
        return st.secrets["firebase_project_id"]
    except Exception:
        return None


def _friendly_message(raw_message):
    for code, message in _ERROR_MESSAGES.items():
        if raw_message.startswith(code):
            return message
    return f"認証に失敗しました（{raw_message}）。"


def _auth_request(endpoint, email, password):
    api_key = _web_api_key()
    if not api_key:
        raise CloudAuthError("クラウド保存の設定が未完了です。管理者にお問い合わせください。")

    try:
        response = requests.post(
            f"{IDENTITY_BASE}/accounts:{endpoint}",
            params={"key": api_key},
            json={"email": email, "password": password, "returnSecureToken": True},
            timeout=10,
        )
    except requests.RequestException:
        raise CloudAuthError("通信に失敗しました。時間をおいて再度お試しください。")

    data = response.json()
    if not response.ok:
        raw_message = data.get("error", {}).get("message", "unknown_error")
        raise CloudAuthError(_friendly_message(raw_message))

    return {
        "uid": data["localId"],
        "email": data["email"],
        "id_token": data["idToken"],
        "refresh_token": data["refreshToken"],
    }


def sign_up(email, password):
    return _auth_request("signUp", email, password)


def sign_in(email, password):
    return _auth_request("signInWithPassword", email, password)


def _refresh_id_token(refresh_token):
    api_key = _web_api_key()
    if not api_key:
        raise CloudAuthError("クラウド保存の設定が未完了です。管理者にお問い合わせください。")

    try:
        response = requests.post(
            TOKEN_REFRESH_URL,
            params={"key": api_key},
            data={"grant_type": "refresh_token", "refresh_token": refresh_token},
            timeout=10,
        )
    except requests.RequestException:
        raise CloudAuthError("通信に失敗しました。時間をおいて再度お試しください。")

    if not response.ok:
        raise CloudAuthError("ログインの有効期限が切れました。再度ログインしてください。")

    data = response.json()
    return data["id_token"], data["refresh_token"]


def _doc_url(uid):
    project_id = _project_id()
    return f"{FIRESTORE_BASE}/projects/{project_id}/databases/(default)/documents/users/{uid}"


def load_history(uid, id_token, refresh_token):
    """Firestoreからhistory_jsonフィールドを読み込む。存在しなければ{}を返す。
    戻り値: (history_dict, 更新後のid_token, 更新後のrefresh_token)
    """
    response = requests.get(
        _doc_url(uid), headers={"Authorization": f"Bearer {id_token}"}, timeout=10
    )

    if response.status_code == 401:
        id_token, refresh_token = _refresh_id_token(refresh_token)
        response = requests.get(
            _doc_url(uid), headers={"Authorization": f"Bearer {id_token}"}, timeout=10
        )

    if response.status_code == 404:
        return {}, id_token, refresh_token

    if not response.ok:
        raise CloudAuthError("学習記録の読み込みに失敗しました。")

    data = response.json()
    raw = data.get("fields", {}).get("history_json", {}).get("stringValue")
    history = json.loads(raw) if raw else {}
    return history, id_token, refresh_token


def save_history(uid, id_token, refresh_token, history_dict):
    """history_dictをJSON文字列としてFirestoreに保存する。
    戻り値: (更新後のid_token, 更新後のrefresh_token)
    """
    body = {"fields": {"history_json": {"stringValue": json.dumps(history_dict, ensure_ascii=False)}}}
    params = {"updateMask.fieldPaths": "history_json"}

    def _do_patch(token):
        return requests.patch(
            _doc_url(uid),
            params=params,
            headers={"Authorization": f"Bearer {token}"},
            json=body,
            timeout=10,
        )

    response = _do_patch(id_token)
    if response.status_code == 401:
        id_token, refresh_token = _refresh_id_token(refresh_token)
        response = _do_patch(id_token)

    if not response.ok:
        raise CloudAuthError("学習記録の保存に失敗しました。")

    return id_token, refresh_token
