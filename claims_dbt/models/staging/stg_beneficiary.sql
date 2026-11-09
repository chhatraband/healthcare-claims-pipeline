with source as (

    select * from {{ source('claims_raw', 'raw_beneficiary') }}

),

renamed as (

    select
        -- keys
        desynpuf_id                                    as member_id,
        cast("year" as integer)                        as coverage_year,
        desynpuf_id || '-' || "year"                   as member_year_key,

        -- demographics
        {{ parse_date('bene_birth_dt') }}              as birth_date,
        {{ parse_date('bene_death_dt') }}              as death_date,
        case bene_sex_ident_cd
            when '1' then 'Male'
            when '2' then 'Female'
            else 'Unknown'
        end                                            as sex,
        sp_state_code                                  as state_code,
        bene_county_cd                                 as county_code,

        -- months of coverage in the year (0-12)
        try_cast(bene_hi_cvrage_tot_mons as integer)   as part_a_months,
        try_cast(bene_smi_cvrage_tot_mons as integer)  as part_b_months,
        try_cast(bene_hmo_cvrage_tot_mons as integer)  as hmo_months,
        try_cast(plan_cvrg_mos_num as integer)         as part_d_months,

        -- chronic conditions: CMS codes 1 = yes, 2 = no
        bene_esrd_ind = 'Y'                            as has_esrd,
        sp_alzhdmta  = '1'                             as has_alzheimers,
        sp_chf       = '1'                             as has_heart_failure,
        sp_chrnkidn  = '1'                             as has_kidney_disease,
        sp_cncr      = '1'                             as has_cancer,
        sp_copd      = '1'                             as has_copd,
        sp_depressn  = '1'                             as has_depression,
        sp_diabetes  = '1'                             as has_diabetes,
        sp_ischmcht  = '1'                             as has_ischemic_heart_disease,
        sp_osteoprs  = '1'                             as has_osteoporosis,
        sp_ra_oa     = '1'                             as has_arthritis,
        sp_strketia  = '1'                             as has_stroke_tia,

        -- yearly Medicare payments per member
        {{ to_amount('medreimb_ip') }}                 as inpatient_paid_amount,
        {{ to_amount('medreimb_op') }}                 as outpatient_paid_amount,
        {{ to_amount('medreimb_car') }}                as carrier_paid_amount

    from source

)

select * from renamed