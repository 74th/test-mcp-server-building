# FastMCP Google Auth + BigQuery template

`query()` ツールは、Google ログインで取得したユーザーの access token をそのまま使って BigQuery にアクセスします。

返す内容は CSV です。

- ヘッダー: `timestamp,co2_mhz19c`
- クエリ:
	- `SELECT timestamp, co2_mhz19c FROM `nnyn-dev.house_monitor.co2` WHERE TIMESTAMP_TRUNC(timestamp, DAY) = TIMESTAMP("2022-11-07") LIMIT 10`

注意点:

- Google OAuth の要求スコープに `https://www.googleapis.com/auth/bigquery` を追加しています
- `query()` はサービスアカウントではなく、ログインしたユーザーの access token 権限で実行されます
