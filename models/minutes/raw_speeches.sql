{# 取得した発言 (data/minutes/<地方公共団体コード>/<年>.ndjson.gz) を型を付けて読む。
   同じ発言が取り直しで 2 回入ったときは、後に取った方を残す #}
{{ config(materialized='ephemeral') }}

select
    lg_code || ':' || file_name as meeting_id,
    lg_code || ':' || file_name || ':' || speech_order as speech_id,
    *
from read_json(
    'data/minutes/*/*.ndjson.gz',
    format = 'newline_delimited',
    columns = {
        lg_code: 'VARCHAR', assembly: 'VARCHAR', file_name: 'VARCHAR', session: 'VARCHAR',
        meeting_name: 'VARCHAR', date: 'DATE', speech_order: 'INTEGER', speaker: 'VARCHAR',
        speech: 'VARCHAR', speech_url: 'VARCHAR', fetched_at: 'TIMESTAMPTZ'
    }
)
qualify row_number() over (partition by lg_code, file_name, speech_order order by fetched_at desc) = 1
