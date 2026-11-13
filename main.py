"""地方議会の会議録のパイプライン。

1. voices: 会議録検索システム VOICES から発言を取り出す
2. dbt: まだ無い会議録と発言を追記する
"""

import logging

from dbt.cli.main import dbtRunner

from pipelines.voices import download_voices

# dbt を読み込むとルートロガーが先に設定されるので、force で上書きする
logging.basicConfig(level=logging.INFO, format="%(message)s", force=True)
logger = logging.getLogger("pipelines")


def dbt_build():
    dbt = dbtRunner()
    for command in (["deps"], ["build"], ["docs", "generate"]):
        if not dbt.invoke(command).success:
            raise SystemExit(f"dbt {' '.join(command)} failed")


def download() -> None:
    logger.info("1/2: voices (世田谷区・杉並区)")
    download_voices()


def main():
    download()
    logger.info("2/2: dbt build")
    dbt_build()


if __name__ == "__main__":
    main()
