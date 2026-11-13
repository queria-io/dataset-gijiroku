"""会議録検索システム VOICES から、議会の会議録を発言ごとに取得する。

年ごとの会議の一覧（voiweb.exe の ACT=100）を、会議の種類（KGTP: 1 定例会、2 臨時会、3 委員会）ごとに
取り、会議の日ごとの会議録の本文（ACT=203）を 1 回で受け取る。本文は発言ごとに
<A NAME="HUID<発言 ID>"> で区切られている。

出力: data/minutes/<地方公共団体コード>/<西暦年>.ndjson.gz（1 行 = 1 発言）

取得するのは今年から VOICES_YEARS 年分（0 なら会議の無い年が 3 年続くまでさかのぼる）。
直近 2 年より前の年は、ファイルが既にあれば飛ばす（手元で全年を取る途中で止まったときに続きから取るため）。
"""

import gzip
import html
import json
import logging
import os
import re
import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request
from zoneinfo import ZoneInfo

from shared.fetch import replacing, request

logger = logging.getLogger("pipelines")

USER_AGENT = "dataset-voices (+https://github.com/queria-io/dataset-voices)"
OUTPUT = Path("data/minutes")
YEARS = int(os.environ.get("VOICES_YEARS", "2"))
INTERVAL_SECONDS = 1.0
# 会議の種類。1 定例会、2 臨時会、3 委員会
KINDS = (1, 2, 3)
EMPTY_YEARS_TO_STOP = 3


@dataclass(frozen=True)
class Assembly:
    lg_code: str
    name: str
    cgi: str
    # 発言の先頭で発言者を表す語の数。世田谷区は「○石川ナオミ　議長　本文」のように名前と役職を分けて書く
    speaker_words: int = 1


ASSEMBLIES = [
    Assembly("131121", "世田谷区議会", "http://kugi.city.setagaya.tokyo.jp/voices/cgi/voiweb.exe", speaker_words=2),
    Assembly("131156", "杉並区議会", "https://suginami.gijiroku.com/voices/voices/cgi/voiweb.exe"),
]


@dataclass(frozen=True)
class Document:
    kind: int
    year: int
    fino: str
    kgno: str
    title: str
    label: str


def get(a: Assembly, **params: str | int) -> str:
    time.sleep(INTERVAL_SECONDS)
    url = f"{a.cgi}?{urlencode(params, safe=',')}"
    return request(Request(url, headers={"User-Agent": USER_AGENT}), lambda r: r.read()).decode("cp932", "replace")


def text(fragment: str) -> str:
    fragment = re.sub(r"<SCRIPT.*?</SCRIPT>", "", fragment, flags=re.S | re.I)
    fragment = re.sub(r"<BR\s*/?>", "\n", fragment, flags=re.I)
    return html.unescape(re.sub(r"<[^>]+>", "", fragment))


ROW = re.compile(
    r"ACT=100[^\"]*[?&]FINO=(\d+)[^\"]*\"[^>]*>.*?</A>\s*([^<]*?),<A[^>]*winopen\('[^']*KGNO=(\d+)&FINO=\d+[^']*'\);\">([^<]*)</A>",
    re.S,
)


def documents(a: Assembly, year: int, kind: int) -> list[Document]:
    page = get(a, ACT=100, KTYP="0,1,2,3", SORT=0, FYY=year, FMM="", FDD="", TYY=year, TMM="", TDD="", KGTP=kind)
    # 「目次」は会議録の目次だけの文書なので除く
    return [
        Document(kind, year, fino, kgno, title.strip(), label.strip())
        for fino, title, kgno, label in ROW.findall(page)
        if not label.strip().endswith("目次")
    ]


def meeting_date(d: Document) -> date:
    m = re.search(r"(\d+)月\s*(\d+)日", d.label) or re.search(r"([０-９\d]+)月\s*([０-９\d]+)日", d.title)
    if not m:
        raise ValueError(f"開会日が読めない: {d.title} {d.label}")
    to_int = lambda s: int(s.translate(str.maketrans("０１２３４５６７８９", "0123456789")))
    return date(d.year, to_int(m[1]), to_int(m[2]))


def split_speaker(body: str, words: int = 1) -> tuple[str | None, str]:
    """「○議長（木梨もりよし議員）　これより…」を発言者と本文に分ける。

    括弧つきの発言者（「◆二十五番（中塚さちよ　議員）」）は括弧の終わりまでを発言者にし、括弧の中の
    空白を除く。括弧の無い発言者は words 語を発言者とし、半角スペースでつなぐ。
    """
    mark = r"[○◎◯◆]\s*"
    paren = re.match(mark + r"([^　\n（]*（[^）\n]*）)[　\n]?", body)
    if paren:
        return paren[1].replace("　", ""), body[paren.end():].strip("　 \n")
    m = re.match(mark + r"[　\n]".join([r"([^　\n]+)"] * words) + r"[　\n]", body)
    return (" ".join(m.groups()), body[m.end():].strip("　 \n")) if m else (None, body.strip("　 \n"))


def speeches(a: Assembly, d: Document) -> Iterator[dict]:
    page = get(a, ACT=203, KENSAKU=0, SORT=0, KTYP="0,1,2,3", KGTP=d.kind, FYY=d.year, TYY=d.year,
               FINO=d.fino, HATSUGENMODE=1, HYOUJIMODE=0, STYLE=0)
    parts = re.split(r'<A NAME="HUID(\d+)"></A>', page)
    held = meeting_date(d)
    for order, (huid, fragment) in enumerate(zip(parts[1::2], parts[2::2])):
        speaker, speech = split_speaker(text(fragment), a.speaker_words)
        yield {
            "lg_code": a.lg_code,
            "assembly": a.name,
            "file_name": d.fino,
            "session": d.title,
            "meeting_name": f"{d.title} {d.label}",
            "date": held.isoformat(),
            "speech_order": order,
            "speaker": speaker if order else None,
            "speech": speech,
            "speech_url": f"{a.cgi}?ACT=200&KENSAKU=0&SORT=0&KTYP=0,1,2,3&KGTP={d.kind}&FYY={d.year}&TYY={d.year}"
                          f"&HUID={huid}&KGNO={d.kgno}&FINO={d.fino}",
        }


def write(path: Path, rows: list[dict], fetched_at: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with replacing(path) as partial, gzip.open(partial, "wt", encoding="utf-8") as out:
        out.writelines(json.dumps({**r, "fetched_at": fetched_at}, ensure_ascii=False) + "\n" for r in rows)


def download_assembly(a: Assembly, output: Path, fetched_at: str, this_year: int) -> int:
    total, empty = 0, 0
    year = this_year
    while (YEARS == 0 and empty < EMPTY_YEARS_TO_STOP) or (YEARS and year > this_year - YEARS):
        path = output / a.lg_code / f"{year}.ndjson.gz"
        if year <= this_year - 2 and path.exists():
            year, empty = year - 1, 0
            continue
        docs = [d for kind in KINDS for d in documents(a, year, kind)]
        empty = 0 if docs else empty + 1
        if docs:
            rows = [row for d in docs for row in speeches(a, d)]
            write(path, rows, fetched_at)
            logger.info("  %s %d年: 会議録 %d 件、%d 発言", a.name, year, len(docs), len(rows))
            total += len(rows)
        year -= 1
    return total


def check_assembly(a: Assembly, output: Path, fetched_at: str, this_year: int) -> int:
    """PR のビルド確認用。最新の会議録の 1 件だけを取る。"""
    for year in (this_year, this_year - 1):
        docs = [d for kind in KINDS for d in documents(a, year, kind)]
        if docs:
            rows = list(speeches(a, docs[0]))
            write(output / a.lg_code / f"{year}.ndjson.gz", rows, fetched_at)
            logger.info("  %s %s %s: %d 発言", a.name, docs[0].title, docs[0].label, len(rows))
            return len(rows)
    return 0


def download_voices(output: Path = OUTPUT) -> int:
    fetched_at = datetime.now(UTC).isoformat()
    this_year = datetime.now(ZoneInfo("Asia/Tokyo")).year
    # FDL_WORKING が無いのは PR のビルド確認。公開しないので各議会の最新の 1 件だけを取る
    run = download_assembly if os.environ.get("FDL_WORKING") else check_assembly
    total = sum(run(a, output, fetched_at, this_year) for a in ASSEMBLIES)
    if total == 0:
        raise SystemExit("1 件も取得できない（会議録検索システムの形が変わった？）")
    return total
