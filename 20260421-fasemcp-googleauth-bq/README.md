# FastMCP Google Auth + BigQuery template

このテンプレートは、Google ログインで取得した**ユーザーの access token**を使って BigQuery にアクセスする `FastMCP` サーバです。

`query()` ツールは BigQuery の結果を CSV 文字列で返します。

## 現在の実装

- OAuth scope:
	- `https://www.googleapis.com/auth/bigquery.readonly`
- BigQuery 呼び出し方法:
	- `google-cloud-bigquery` の `client.query()` ではなく、BigQuery REST API の `jobs.query` を直接呼ぶ
- 実行主体:
	- サービスアカウントではなく、ログインしたユーザーの access token

## 返却内容

現在の `query()` は、以下の固定クエリを実行して CSV を返します。

`SELECT timestamp, co2_mhz19c FROM `nnyn-dev.house_monitor.co2` WHERE TIMESTAMP_TRUNC(timestamp, DAY) = TIMESTAMP("2022-11-07") LIMIT 10`

返却される CSV のヘッダーは以下です。

- `timestamp,co2_mhz19c`

## 今回の検証で確認できたこと

### 1. `client.query()` では `bigquery.readonly` だけだと失敗する

`google-cloud-bigquery` の `client.query()` は内部的に `jobs.insert` を使うため、`bigquery.readonly` スコープでは不足しました。

確認できたエラー:

- `ACCESS_TOKEN_SCOPE_INSUFFICIENT`
- `method: google.cloud.bigquery.v2.JobService.InsertJob`

つまり、**読み取りクエリであっても、実装が `jobs.insert` ベースだと readonly scope では通りません**。

### 2. `jobs.query` 直呼びなら `bigquery.readonly` で `SELECT` を実行できた

実装を BigQuery REST API の `jobs.query` 直接呼び出しに変更したところ、`bigquery.readonly` スコープのままで `SELECT` クエリを実行できることを確認しました。

確認できたこと:

- `jobs.query` + `bigquery.readonly` で結果取得に成功
- 返却形式は CSV
- サービスアカウントではなく、ログインユーザーの権限で実行

### 3. 最初の失敗原因は権限ではなく SSL 証明書不足だった

`jobs.query` 化した直後は以下のエラーで失敗しました。

- `ssl.SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED]`
- `urllib.error.URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] ...>`

原因は `debian:slim` ベースのコンテナに CA 証明書が入っていなかったことです。

対応:

- `Dockerfile` に `ca-certificates` を追加

これにより HTTPS 通信で BigQuery REST API を正常に呼べるようになりました。

## 検証結果の要約

このリポジトリで確認できたのは次の内容です。

- `bigquery.readonly` だけでは `client.query()` は使えない
- `jobs.query` を直接使えば、`bigquery.readonly` でも `SELECT` 系クエリは実行できる
- コンテナで REST API を叩く場合、CA 証明書が必要

## 注意点

- これは**すべての SQL が書き込み権限なしで実行できる**ことを意味しません
- 今回確認できたのは、少なくとも `SELECT` 系の読み取りクエリが `jobs.query` + `bigquery.readonly` で動くことです
- 実行可否は OAuth scope だけでなく、対象データセットやテーブルに対する IAM 権限にも依存します

## コンテナ実行時の補足

`debian:slim` ベースのコンテナでは HTTPS 呼び出しのために `ca-certificates` が必要です。

このリポジトリの `Dockerfile` ではそれをインストールしています。
