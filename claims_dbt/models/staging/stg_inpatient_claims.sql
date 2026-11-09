with source as (

    select * from {{ source('claims_raw', 'raw_inpatient') }}

),

renamed as (

    select
        -- keys: one claim can be split into segments, so the grain is claim + segment
        clm_id || '-' || segment                         as claim_key,
        clm_id                                           as claim_id,
        cast(segment as integer)                         as segment,
        desynpuf_id                                      as member_id,
        prvdr_num                                        as provider_id,
        nullif(at_physn_npi, '')                         as attending_npi,
        'inpatient'                                      as claim_type,

        -- dates (some claims have none: see analyses/check_missing_from_dates.sql)
        {{ parse_date('clm_from_dt') }}                  as claim_from_date,
        {{ parse_date('clm_thru_dt') }}                  as claim_thru_date,
        {{ parse_date('clm_admsn_dt') }}                 as admission_date,
        {{ parse_date('nch_bene_dschrg_dt') }}           as discharge_date,

        -- money
        {{ to_amount('clm_pmt_amt') }}                   as paid_amount,
        {{ to_amount('nch_prmry_pyr_clm_pd_amt') }}      as other_payer_paid_amount,
        {{ to_amount('nch_bene_ip_ddctbl_amt') }}        as member_deductible_amount,
        {{ to_amount('nch_bene_pta_coinsrnc_lblty_am') }} as member_coinsurance_amount,

        -- utilization and clinical codes
        try_cast(clm_utlztn_day_cnt as integer)          as utilization_days,
        nullif(clm_drg_cd, '')                           as drg_code,
        nullif(admtng_icd9_dgns_cd, '')                  as admitting_diagnosis_code,
        nullif(icd9_dgns_cd_1, '')                       as primary_diagnosis_code,
        nullif(icd9_prcdr_cd_1, '')                      as primary_procedure_code

    from source

),

final as (

    select
        *,
        coalesce(claim_from_date, claim_thru_date, admission_date, discharge_date)          as service_date,
        year(coalesce(claim_from_date, claim_thru_date, admission_date, discharge_date))    as service_year,
        coalesce(claim_from_date, claim_thru_date, admission_date, discharge_date) is null  as is_missing_service_date
    from renamed

)

select * from final