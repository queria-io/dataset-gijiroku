{# 発言 1 件 1 行。まだ無い会議録の発言だけを追記する。会議録は登録後に書き換えない前提で、前回の行は残す #}
{{ config(materialized='incremental', incremental_strategy='append') }}

select
    speech_id,
    meeting_id,
    lg_code,
    assembly,
    date,
    meeting_name,
    speech_order,
    speaker,
    speech,
    speech_url,
    fetched_at
from {{ ref('raw_speeches') }}
{% if is_incremental() %}
where meeting_id not in (select meeting_id from {{ this }})
{% endif %}
order by lg_code, date, meeting_id, speech_order
