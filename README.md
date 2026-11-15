# dataset-gijiroku

Queria のデータセット `gijiroku`（地方議会の会議録（VOICES））のリポジトリです。データセットの説明は [docs/index.md](docs/index.md) にあります。

## ビルド

```bash
uv sync
scripts/build.sh
```

取得の間隔は 1 秒です。1 回のビルドで取得するのは各議会の今年から 2 年分（`GIJIROKU_YEARS`）です。すべての年を取得するときは手元で `GIJIROKU_YEARS=0 scripts/build.sh` を実行します。途中で止まったときは、直近 2 年より前の取得済みの年を飛ばして続きから取得します。
