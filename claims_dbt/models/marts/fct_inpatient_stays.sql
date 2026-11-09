with segments as (

    select *
    from {{ ref('fct_claims') }}
    where claim_type = 'inpatient'

),

stays as (

    select
        claim_id                                            as stay_id,
        member_id,
        min_by(provider_id, segment)                        as provider_id,
        min_by(drg_code, segment)                           as drg_code,
        min_by(primary_diagnosis_code, segment)             as primary_diagnosis_code,
        coalesce(min(admission_date), min(service_date))    as admission_date,
        max(discharge_date)                                 as discharge_date,
        count(*)                                            as segment_count,
        sum(paid_amount)                                    as paid_amount
    from segments
    group by claim_id, member_id

),

with_next as (

    select
        *,
        date_diff('day', admission_date, discharge_date)    as length_of_stay_days,
        lead(admission_date) over (
            partition by member_id
            order by admission_date, stay_id
        )                                                   as next_admission_date
    from stays

)

select
    *,
    year(admission_date)                                    as admission_year,
    date_diff('day', discharge_date, next_admission_date)   as days_to_next_admission,
    coalesce(
        date_diff('day', discharge_date, next_admission_date) between 0 and 30,
        false
    )                                                       as is_readmitted_30d
from with_next