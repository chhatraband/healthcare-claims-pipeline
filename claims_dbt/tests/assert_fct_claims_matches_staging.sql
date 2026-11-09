-- fct_claims must keep every staging claim and every dollar.
-- Staging is already tested against the answer key, so this
-- completes the chain: raw -> staging -> marts.

with staged as (

    select count(*) as row_count, sum(paid_amount) as paid
    from {{ ref('stg_inpatient_claims') }}

    union all

    select count(*), sum(paid_amount)
    from {{ ref('stg_outpatient_claims') }}

),

expected as (

    select sum(row_count) as row_count, sum(paid) as paid
    from staged

),

actual as (

    select count(*) as row_count, sum(paid_amount) as paid
    from {{ ref('fct_claims') }}

)

select
    e.row_count as expected_rows,
    a.row_count as actual_rows,
    e.paid      as expected_paid,
    a.paid      as actual_paid
from expected e
cross join actual a
where e.row_count <> a.row_count
   or e.paid <> a.paid