-- Why is the 2009 readmission rate half of 2008's?
-- If the drop is only in late 2009, the cause is thin 2010 data.
-- If it is low all year, the cause is in the 2009 data itself.

select
    date_trunc('month', discharge_date)                                  as discharge_month,
    count(*)                                                             as stays,
    count_if(is_readmitted_30d)                                          as readmitted,
    round(avg(case when is_readmitted_30d then 1.0 else 0.0 end) * 100, 2) as readmission_rate_pct
from {{ ref('fct_inpatient_stays') }}
where discharge_date between date '2008-01-01' and date '2009-12-31'
group by 1
order by 1