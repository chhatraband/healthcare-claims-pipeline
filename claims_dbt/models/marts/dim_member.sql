with members as (

    select * from {{ ref('stg_beneficiary') }}

),

latest_year as (

    select *
    from (
        select
            *,
            coverage_year - year(birth_date)                            as age,
            row_number() over (
                partition by member_id
                order by coverage_year desc
            )                                                           as row_num
        from members
    ) as ranked
    where row_num = 1

),

conditions as (

    select
        member_id,
        count(*)                          as years_enrolled,
        bool_or(has_esrd)                 as has_esrd,
        bool_or(has_alzheimers)           as has_alzheimers,
        bool_or(has_heart_failure)        as has_heart_failure,
        bool_or(has_kidney_disease)       as has_kidney_disease,
        bool_or(has_cancer)               as has_cancer,
        bool_or(has_copd)                 as has_copd,
        bool_or(has_depression)           as has_depression,
        bool_or(has_diabetes)             as has_diabetes,
        bool_or(has_ischemic_heart_disease) as has_ischemic_heart_disease,
        bool_or(has_osteoporosis)         as has_osteoporosis,
        bool_or(has_arthritis)            as has_arthritis,
        bool_or(has_stroke_tia)           as has_stroke_tia
    from members
    group by member_id

)

select
    l.member_id,
    l.sex,
    l.birth_date,
    l.death_date,
    l.age,
    case
        when l.age is null then 'Unknown'
        when l.age < 65    then 'Under 65'
        when l.age < 75    then '65-74'
        when l.age < 85    then '75-84'
        else '85+'
    end                                   as age_group,
    l.state_code,
    l.county_code,
    l.coverage_year                       as last_coverage_year,
    c.years_enrolled,
    c.has_esrd,
    c.has_alzheimers,
    c.has_heart_failure,
    c.has_kidney_disease,
    c.has_cancer,
    c.has_copd,
    c.has_depression,
    c.has_diabetes,
    c.has_ischemic_heart_disease,
    c.has_osteoporosis,
    c.has_arthritis,
    c.has_stroke_tia,
    cast(c.has_alzheimers as integer)
      + cast(c.has_heart_failure as integer)
      + cast(c.has_kidney_disease as integer)
      + cast(c.has_cancer as integer)
      + cast(c.has_copd as integer)
      + cast(c.has_depression as integer)
      + cast(c.has_diabetes as integer)
      + cast(c.has_ischemic_heart_disease as integer)
      + cast(c.has_osteoporosis as integer)
      + cast(c.has_arthritis as integer)
      + cast(c.has_stroke_tia as integer)  as chronic_condition_count
from latest_year l
join conditions c
    on c.member_id = l.member_id