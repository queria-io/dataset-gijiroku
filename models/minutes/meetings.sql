{# 会議録 1 件（会議の 1 日分）1 行。まだ無い会議録だけを追記する #}
{{ config(materialized='incremental', incremental_strategy='append') }}

select distinct on (meeting_id)
    meeting_id,
    lg_code,
    assembly,
    session,
    meeting_name,
    date,
    count(*) over (partition by meeting_id) as speeches,
    regexp_replace(speech_url, '&HUID=\d+', '') as meeting_url,
    fetched_at
from {{ ref('raw_speeches') }}
{% if is_incremental() %}
where meeting_id not in (select meeting_id from {{ this }})
{% endif %}
order by meeting_id, fetched_at desc
