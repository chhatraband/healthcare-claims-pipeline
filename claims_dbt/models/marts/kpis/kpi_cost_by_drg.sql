-- Which types of hospital stay (DRG) drive inpatient spending, 2008-2009.
-- SynPUF has DRG codes only, no DRG names.

select
    drg_code,
    count(*)                                                                 as stays,
    count(distinct member_id)                                                as members,
    sum(paid_amount)                                                         as total_paid,
    round(avg(paid_amount), 2)                                               as avg_paid_per_stay,
    round(avg(length_of_stay_days), 2)                                       as alos_days,
    round(avg(case when is_readmitted_30d then 1.0 else 0.0 end) * 100, 2)   as readmission_rate_pct,
    round(cast(sum(paid_amount) as double) * 100
        / sum(cast(sum(paid_amount) as double)) over (), 2)                  as pct_of_inpatient_paid,
    rank() over (order by sum(paid_amount) desc)                             as cost_rank
from {{ ref('fct_inpatient_stays') }}
where admission_year in (2008, 2009)
  and drg_code is not null
group by drg_code