{# 取得した発言 (data/minutes/<地方公共団体コード>/<年>.ndjson.gz)。pipelines が書いた項目をそのまま読む #}

select *
from read_json(
    'data/minutes/*/*.ndjson.gz',
    format = 'newline_delimited',
    columns = {
        lg_code: 'VARCHAR', assembly: 'VARCHAR', file_name: 'VARCHAR', session: 'VARCHAR',
        meeting_name: 'VARCHAR', date: 'DATE', speech_order: 'INTEGER', speaker: 'VARCHAR',
        speech: 'VARCHAR', speech_url: 'VARCHAR', fetched_at: 'TIMESTAMPTZ'
    }
)
