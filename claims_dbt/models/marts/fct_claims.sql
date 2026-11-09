with inpatient as (

    select
        claim_key,
        claim_id,
        segment,
        claim_type,
        member_id,
        nullif(provider_id, '')                             as provider_id,
        service_date,
        service_year,
        is_missing_service_date,
        admission_date,
        discharge_date,
        date_diff('day', admission_date, discharge_date)    as length_of_stay_days,
        utilization_days,
        drg_code,
        primary_diagnosis_code,
        paid_amount,
        other_payer_paid_amount,
        member_deductible_amount,
        member_coinsurance_amount
    from {{ ref('stg_inpatient_claims') }}

),

outpatient as (

    select
        claim_key,
        claim_id,
        segment,
        claim_type,
        member_id,
        nullif(provider_id, '')                             as provider_id,
        service_date,
        service_year,
        is_missing_service_date,
        cast(null as date)                                  as admission_date,
        cast(null as date)                                  as discharge_date,
        cast(null as bigint)                                as length_of_stay_days,
        cast(null as integer)                               as utilization_days,
        cast(null as varchar)                               as drg_code,
        primary_diagnosis_code,
        paid_amount,
        other_payer_paid_amount,
        member_deductible_amount,
        member_coinsurance_amount
    from {{ ref('stg_outpatient_claims') }}

),

unioned as (

    select * from inpatient
    union all
    select * from outpatient

)

select
    *,
    claim_type || '-' || claim_key                         as claim_sk,
    date_trunc('month', service_date)                      as service_month,
    coalesce(member_deductible_amount, 0)
        + coalesce(member_coinsurance_amount, 0)           as member_liability_amount
from unioned