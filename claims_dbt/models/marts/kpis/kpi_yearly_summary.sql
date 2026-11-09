with member_months as (

    select
        coverage_year                                                   as year,
        count(*)                                                        as members,
        sum(greatest(coalesce(part_a_months, 0),
                     coalesce(part_b_months, 0)))                       as member_months
    from {{ ref('stg_beneficiary') }}
    group by coverage_year

),

claims as (

    select
        service_year                                                    as year,
        sum(paid_amount)                                                as total_paid,
        sum(case when claim_type = 'inpatient'  then paid_amount end)   as inpatient_paid,
        sum(case when claim_type = 'outpatient' then paid_amount end)   as outpatient_paid
    from {{ ref('fct_claims') }}
    where not is_missing_service_date
    group by service_year

),

stays as (

    select
        admission_year                                                  as year,
        count(*)                                                        as admissions,
        avg(length_of_stay_days)                                        as avg_length_of_stay_days,
        avg(case when is_readmitted_30d then 1.0 else 0.0 end)          as readmission_rate
    from {{ ref('fct_inpatient_stays') }}
    group by admission_year

)

select
    m.year,
    m.members,
    m.member_months,
    c.total_paid,
    round(c.total_paid      / m.member_months, 2)                       as pmpm_total,
    round(c.inpatient_paid  / m.member_months, 2)                       as pmpm_inpatient,
    round(c.outpatient_paid / m.member_months, 2)                       as pmpm_outpatient,
    s.admissions,
    round(s.admissions * 12000.0 / m.member_months, 1)                  as admits_per_1000,
    round(s.avg_length_of_stay_days, 2)                                 as alos_days,
    round(s.readmission_rate * 100, 2)                                  as readmission_rate_pct
from member_months m
left join claims c on c.year = m.year
left join stays  s on s.year = m.year