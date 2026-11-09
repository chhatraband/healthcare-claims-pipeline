-- Fails (returns rows) if staging row counts or paid totals
-- differ from data/raw/answer_key.txt

with actual as (

    select 'inpatient' as dataset, count(*) as row_count, sum(paid_amount) as paid
    from {{ ref('stg_inpatient_claims') }}

    union all

    select 'outpatient', count(*), sum(paid_amount)
    from {{ ref('stg_outpatient_claims') }}

    union all

    select 'beneficiary_2008', count(*), cast(null as decimal(38,2))
    from {{ ref('stg_beneficiary') }}
    where coverage_year = 2008

    union all

    select 'beneficiary_2009', count(*), cast(null as decimal(38,2))
    from {{ ref('stg_beneficiary') }}
    where coverage_year = 2009

),

expected as (

    select * from (
        values
            ('inpatient',        66773,  cast(639260180.00 as decimal(38,2))),
            ('outpatient',       790790, cast(224524710.00 as decimal(38,2))),
            ('beneficiary_2008', 116352, cast(null as decimal(38,2))),
            ('beneficiary_2009', 114538, cast(null as decimal(38,2)))
    ) as t (dataset, row_count, paid)

)

select
    e.dataset,
    e.row_count  as expected_rows,
    a.row_count  as actual_rows,
    e.paid       as expected_paid,
    a.paid       as actual_paid
from expected e
left join actual a
    on a.dataset = e.dataset
where a.row_count is distinct from e.row_count
   or (e.paid is not null and a.paid is distinct from e.paid)