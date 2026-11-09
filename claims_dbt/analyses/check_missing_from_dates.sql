-- Why do some claims have no claim_from_date?
-- Reads RAW text so we see the original values.

select
    'inpatient'                                              as dataset,
    count(*)                                                 as bad_rows,
    count_if(trim(clm_from_dt) = '')                         as blank_from_date,
    count_if(trim(clm_thru_dt) = '')                         as blank_thru_date,
    max(clm_from_dt)                                         as sample_value,
    sum(try_cast(clm_pmt_amt as decimal(18,2)))              as paid_on_these
from {{ source('claims_raw', 'raw_inpatient') }}
where try(date_parse(nullif(trim(clm_from_dt), ''), '%Y%m%d')) is null

union all

select
    'outpatient',
    count(*),
    count_if(trim(clm_from_dt) = ''),
    count_if(trim(clm_thru_dt) = ''),
    max(clm_from_dt),
    sum(try_cast(clm_pmt_amt as decimal(18,2)))
from {{ source('claims_raw', 'raw_outpatient') }}
where try(date_parse(nullif(trim(clm_from_dt), ''), '%Y%m%d')) is null