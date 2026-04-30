import os

import google.auth
from googleapiclient.discovery import build

TEST_USER_EMAIL = os.environ["TEST_USER_EMAIL"]
AUTHORIZED_GROUP_EMAIL = os.environ["AUTHORIZED_GROUP_EMAIL"]


def check_user_in_group_adc(user_email, group_email):
    # 1. ADCから認証情報とプロジェクトIDを自動取得
    # スコープはAdmin SDKの読み取り専用を指定
    scopes = ['https://www.googleapis.com/auth/admin.directory.group.member.readonly']
    creds, project = google.auth.default(scopes=scopes)

    # 2. APIクライアントの構築
    service = build('admin', 'directory_v1', credentials=creds)

    try:
        # 3. hasMemberを実行
        response = service.members().hasMember(
            groupKey=group_email,
            memberKey=user_email
        ).execute()

        return response.get('isMember', False)

    except Exception as e:
        # 権限不足やグループが存在しない場合のエラーハンドリング
        print(f"Error checking group membership: {e}")
        return False

# --- 実行例 ---
if __name__ == "__main__":
    target_user = TEST_USER_EMAIL
    target_group = AUTHORIZED_GROUP_EMAIL

    if check_user_in_group_adc(target_user, target_group):
        print("メンバーであることが確認されました。")
    else:
        print("メンバーではない、あるいは確認できませんでした。")
