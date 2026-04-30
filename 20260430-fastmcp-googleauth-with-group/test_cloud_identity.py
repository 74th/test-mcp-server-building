import os

import google.auth
from googleapiclient.discovery import build

TEST_USER_EMAIL = os.environ["TEST_USER_EMAIL"]
AUTHORIZED_GROUP_EMAIL = os.environ["AUTHORIZED_GROUP_EMAIL"]


def check_user_in_group_adc(user_email, group_email):
    # 1. ADCから認証情報とプロジェクトIDを自動取得
    scopes = ['https://www.googleapis.com/auth/cloud-identity.groups.readonly']
    creds, project = google.auth.default(scopes=scopes)

    # 2. APIクライアントの構築
    service = build('cloudidentity', 'v1', credentials=creds)

    try:
        # 3. グループの ID (resource name) を取得
        # groupKey_id ではなく groupKey.id (辞書形式) で指定します
        lookup_res = service.groups().lookup(
            groupKey_id=group_email
        ).execute()
        # 上記でエラーが出る場合は以下を試してください：
        # lookup_res = service.groups().lookup().execute(groupKey_id=group_email)

        group_resource_name = lookup_res.get('name')

        # 4. 所属確認 (checkTransitiveMembership)
        # parent は "groups/..." という形式
        response = service.groups().memberships().checkTransitiveMembership(
            parent=group_resource_name,
            query=f"member_key_id == '{user_email}'"
        ).execute()

        if response.get('hasMembership'):
            print(f"✅ {user_email} は {group_email} のメンバーです。")
            return True
        else:
            print(f"❌ {user_email} はメンバーではありません。")
            return False

    except Exception as e:
        # 引数エラーが出る場合は、SDKのバージョンによって引数名が異なる可能性があります
        print(f"詳細なエラー内容: {e}")
        return False

# --- 実行例 ---
if __name__ == "__main__":
    target_user = TEST_USER_EMAIL
    target_group = AUTHORIZED_GROUP_EMAIL

    if check_user_in_group_adc(target_user, target_group):
        print("メンバーであることが確認されました。")
    else:
        print("メンバーではない、あるいは確認できませんでした。")
