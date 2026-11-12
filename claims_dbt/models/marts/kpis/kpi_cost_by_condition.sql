with member_year as (

    select
        member_id,
        coverage_year                                                       as year,
        greatest(coalesce(part_a_months, 0), coalesce(part_b_months, 0))    as member_months,
        has_alzheimers,
        has_heart_failure,
        has_kidney_disease,
        has_cancer,
        has_copd,
        has_depression,
        has_diabetes,
        has_ischemic_heart_disease,
        has_osteoporosis,
        has_arthritis,
        has_stroke_tia
    from {{ ref('stg_beneficiary') }}

),

member_year_cost as (

    select
        member_id,
        service_year                                                        as year,
        sum(paid_amount)                                                    as paid_amount
    from {{ ref('fct_claims') }}
    where not is_missing_service_date
    group by member_id, service_year

),

joined as (

    select
        m.*,
        coalesce(c.paid_amount, 0)                                          as paid_amount
    from member_year m
    left join member_year_cost c
        on  c.member_id = m.member_id
        and c.year      = m.year

),

unpivoted as (

    select
        j.year,
        j.member_months,
        j.paid_amount,
        t.condition_name,
        t.has_condition
    from joined j
    cross join unnest(
        array['Alzheimers', 'Heart failure', 'Kidney disease', 'Cancer', 'COPD',
              'Depression', 'Diabetes', 'Ischemic heart disease', 'Osteoporosis',
              'Arthritis', 'Stroke / TIA'],
        array[j.has_alzheimers, j.has_heart_failure, j.has_kidney_disease, j.has_cancer, j.has_copd,
              j.has_depression, j.has_diabetes, j.has_ischemic_heart_disease, j.has_osteoporosis,
              j.has_arthritis, j.has_stroke_tia]
    ) as t (condition_name, has_condition)

),

summary as (

    select
        year,
        condition_name,
        count_if(has_condition)                                             as members_with_condition,
        round(count_if(has_condition) * 100.0 / count(*), 2)                as prevalence_pct,
        round(sum(case when has_condition then paid_amount end)
            / sum(case when has_condition then member_months end), 2)       as pmpm_with_condition,
        round(sum(case when not has_condition then paid_amount end)
            / sum(case when not has_condition then member_months end), 2)   as pmpm_without_condition
    from unpivoted
    group by year, condition_name

)

select
    cast(year as varchar) || '-' || condition_name                          as kpi_key,
    *,
    round(pmpm_with_condition / pmpm_without_condition, 2)                  as cost_multiplier
from summary