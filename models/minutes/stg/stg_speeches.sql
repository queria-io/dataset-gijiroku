{# 発言 1 件 1 行。会議録と発言の ID を付ける。同じ発言が取り直しで 2 回入ったときは、後に取った方を残す #}

select
    lg_code || ':' || file_name as meeting_id,
    lg_code || ':' || file_name || ':' || speech_order as speech_id,
    *
from {{ ref('raw_speeches') }}
qualify row_number() over (partition by lg_code, file_name, speech_order order by fetched_at desc) = 1
