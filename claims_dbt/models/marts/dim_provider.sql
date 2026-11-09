-- CMS SynPUF has no provider reference file, so the provider list
-- is built from the providers that appear on claims.

select
    provider_id,
    count_if(claim_type = 'inpatient')      as inpatient_claim_count,
    count_if(claim_type = 'outpatient')     as outpatient_claim_count,
    count(distinct member_id)               as members_served,
    min(service_date)                       as first_service_date,
    max(service_date)                       as last_service_date
from {{ ref('fct_claims') }}
where provider_id is not null
group by provider_id