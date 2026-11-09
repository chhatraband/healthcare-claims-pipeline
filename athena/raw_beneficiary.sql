CREATE EXTERNAL TABLE claims_raw.raw_beneficiary (
  `desynpuf_id` STRING,
  `bene_birth_dt` STRING,
  `bene_death_dt` STRING,
  `bene_sex_ident_cd` STRING,
  `bene_race_cd` STRING,
  `bene_esrd_ind` STRING,
  `sp_state_code` STRING,
  `bene_county_cd` STRING,
  `bene_hi_cvrage_tot_mons` STRING,
  `bene_smi_cvrage_tot_mons` STRING,
  `bene_hmo_cvrage_tot_mons` STRING,
  `plan_cvrg_mos_num` STRING,
  `sp_alzhdmta` STRING,
  `sp_chf` STRING,
  `sp_chrnkidn` STRING,
  `sp_cncr` STRING,
  `sp_copd` STRING,
  `sp_depressn` STRING,
  `sp_diabetes` STRING,
  `sp_ischmcht` STRING,
  `sp_osteoprs` STRING,
  `sp_ra_oa` STRING,
  `sp_strketia` STRING,
  `medreimb_ip` STRING,
  `benres_ip` STRING,
  `pppymt_ip` STRING,
  `medreimb_op` STRING,
  `benres_op` STRING,
  `pppymt_op` STRING,
  `medreimb_car` STRING,
  `benres_car` STRING,
  `pppymt_car` STRING
)
PARTITIONED BY (`year` STRING)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES ('separatorChar' = ',', 'quoteChar' = '"')
LOCATION 's3://chhatraband-claims-pipeline/raw/beneficiary/'
TBLPROPERTIES ('skip.header.line.count' = '1');
