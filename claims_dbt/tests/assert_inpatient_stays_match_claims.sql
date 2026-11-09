-- One row per unique inpatient claim_id (answer key: 66,705),
-- and no money lost when segments are combined.

with expected as (

    select
        count(distinct claim_id) as stay_count,
        sum(paid_amount)         as paid
    from {{ ref('fct_claims') }}
    where claim_type = 'inpatient'

),

actual as (

    select
        count(*)         as stay_count,
        sum(paid_amount) as paid
    from {{ ref('fct_inpatient_stays') }}

)

select *
from expected e
cross join actual a
where e.stay_count <> a.stay_count
   or e.paid <> a.paid