"""
Healthcare Claims Dashboard (Streamlit).

Reads the tables dbt built in Athena (database claims_marts) and shows
payer KPIs: PMPM, admits per 1,000, ALOS, 30-day readmissions,
cost by chronic condition and cost by DRG.
"""
import pandas as pd
import streamlit as st
from pyathena import connect
from pyathena.pandas.cursor import PandasCursor

# ---------------------------------------------------------------- settings
AWS_PROFILE = "claims"                      # the least-privilege IAM user, never root
AWS_REGION = "us-east-2"
S3_STAGING_DIR = "s3://chhatraband-claims-pipeline/athena-results/"
DATABASE = "claims_marts"                   # the dbt marts and KPI tables

# chart colours (bright enough to read on both dark and light backgrounds)
INPATIENT_COLOR = "#14B8A6"                 # teal
OUTPATIENT_COLOR = "#F59E0B"                # amber
CONDITION_COLOR = "#A78BFA"                 # violet
READMISSION_COLOR = "#FB7185"               # rose

st.set_page_config(page_title="Healthcare Claims Dashboard", page_icon="🏥", layout="wide")


# ---------------------------------------------------------------- Athena helpers
@st.cache_resource
def get_connection():
    """One Athena connection, created once and reused by every query."""
    return connect(
        s3_staging_dir=S3_STAGING_DIR,
        region_name=AWS_REGION,
        profile_name=AWS_PROFILE,
        schema_name=DATABASE,
        work_group="primary",
        cursor_class=PandasCursor,
    )


@st.cache_data(ttl=3600, show_spinner="Querying Athena...")
def run_query(sql: str) -> pd.DataFrame:
    """Run SQL in Athena and return a DataFrame. Each result is cached for 1 hour."""
    return get_connection().cursor().execute(sql).as_pandas()


# ---------------------------------------------------------------- load data
yearly = run_query("""
    select
        year,
        members,
        member_months,
        cast(pmpm_total      as double) as pmpm_total,
        cast(pmpm_inpatient  as double) as pmpm_inpatient,
        cast(pmpm_outpatient as double) as pmpm_outpatient,
        admissions,
        cast(admits_per_1000      as double) as admits_per_1000,
        cast(alos_days            as double) as alos_days,
        cast(readmission_rate_pct as double) as readmission_rate_pct
    from kpi_yearly_summary
    order by year
""")

monthly_paid = run_query("""
    select
        service_month,
        claim_type,
        cast(sum(paid_amount) as double) as paid
    from fct_claims
    where service_year in (2008, 2009)
    group by service_month, claim_type
    order by service_month
""")

monthly_readmissions = run_query("""
    select
        date_trunc('month', discharge_date)                                      as discharge_month,
        cast(avg(case when is_readmitted_30d then 1.0 else 0.0 end) * 100 as double) as readmission_rate_pct
    from fct_inpatient_stays
    where discharge_date between date '2008-01-01' and date '2009-12-31'
    group by 1
    order by 1
""")

conditions = run_query("""
    select
        year,
        condition_name,
        members_with_condition,
        cast(prevalence_pct         as double) as prevalence_pct,
        cast(pmpm_with_condition    as double) as pmpm_with_condition,
        cast(pmpm_without_condition as double) as pmpm_without_condition,
        cast(cost_multiplier        as double) as cost_multiplier
    from kpi_cost_by_condition
""")

top_drgs = run_query("""
    select
        cost_rank,
        drg_code,
        stays,
        cast(total_paid            as double) as total_paid,
        cast(avg_paid_per_stay     as double) as avg_paid_per_stay,
        cast(alos_days             as double) as alos_days,
        cast(pct_of_inpatient_paid as double) as pct_of_inpatient_paid
    from kpi_cost_by_drg
    where cost_rank <= 10
    order by cost_rank
""")

quality = run_query("""
    select
        count(*)                                                                as claims,
        cast(sum(paid_amount) as double)                                        as paid,
        count_if(is_missing_service_date)                                       as undated_claims,
        cast(sum(case when is_missing_service_date then paid_amount end) as double) as undated_paid
    from fct_claims
""").iloc[0]


# ---------------------------------------------------------------- sidebar
st.sidebar.title("🏥 Claims Dashboard")
year = st.sidebar.selectbox("Year", options=[2009, 2008])
st.sidebar.markdown(
    "**Data:** CMS DE-SynPUF Sample 1 (synthetic Medicare claims)  \n"
    "**Pipeline:** S3 → Athena → dbt → Airflow  \n"
    "**Scope:** inpatient + outpatient facility claims"
)

this_year = yearly[yearly["year"] == year].iloc[0]
prior = yearly[yearly["year"] == year - 1]
last_year = prior.iloc[0] if not prior.empty else None


def change(column: str, kind: str = "number", decimals: int = 1):
    """Year-over-year change for st.metric, or None when there is no prior year."""
    if last_year is None:
        return None
    diff = this_year[column] - last_year[column]
    if kind == "money":
        return f"{'-' if diff < 0 else '+'}${abs(diff):,.2f}"
    if kind == "points":
        return f"{diff:+.2f} pts"
    if kind == "count":
        return f"{int(diff):+,}"
    return f"{diff:+,.{decimals}f}"


# ---------------------------------------------------------------- header + KPIs
st.title("Healthcare Claims: Payer KPIs")
st.caption(f"Medicare members, {year}" + ("" if last_year is None else f" · change vs {year - 1}"))

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Members", f"{int(this_year['members']):,}", change("members", kind="count"))
c2.metric("PMPM (facility)", f"${this_year['pmpm_total']:,.2f}",
          change("pmpm_total", kind="money"), delta_color="inverse",
          help="Paid per member per month: inpatient + outpatient facility claims only.")
c3.metric("Admits per 1,000", f"{this_year['admits_per_1000']:,.1f}",
          change("admits_per_1000"), delta_color="inverse",
          help="Hospital admissions per 1,000 members per year.")
c4.metric("ALOS (days)", f"{this_year['alos_days']:.2f}",
          change("alos_days", decimals=2), delta_color="inverse",
          help="Average length of a hospital stay.")
c5.metric("30-day readmission", f"{this_year['readmission_rate_pct']:.2f}%",
          change("readmission_rate_pct", kind="points"), delta_color="inverse",
          help="Share of stays followed by another admission within 30 days of discharge.")

st.divider()

# ---------------------------------------------------------------- cost trends
left, right = st.columns(2)

with left:
    st.subheader("PMPM by claim type")
    pmpm_by_type = yearly[["year", "pmpm_inpatient", "pmpm_outpatient"]].rename(
        columns={"pmpm_inpatient": "inpatient", "pmpm_outpatient": "outpatient"}
    )
    pmpm_by_type["year"] = pmpm_by_type["year"].astype(str)
    st.bar_chart(pmpm_by_type, x="year", y=["inpatient", "outpatient"],
                 color=[INPATIENT_COLOR, OUTPATIENT_COLOR],
                 x_label="Year", y_label="PMPM ($)")

with right:
    st.subheader("Monthly paid amount")
    paid_by_type = (
        monthly_paid
        .pivot(index="service_month", columns="claim_type", values="paid")
        .reset_index()
    )
    st.line_chart(paid_by_type, x="service_month", y=["inpatient", "outpatient"],
                  color=[INPATIENT_COLOR, OUTPATIENT_COLOR],
                  x_label="Month", y_label="Paid ($)")

# ---------------------------------------------------------------- chronic conditions
st.subheader(f"Cost by chronic condition, {year}")
st.caption("Members with each condition vs members without it. "
           "Conditions overlap, so multipliers show association, not cause.")

year_conditions = conditions[conditions["year"] == year].sort_values("cost_multiplier", ascending=False)

left, right = st.columns([2, 3])
with left:
    st.bar_chart(year_conditions, x="condition_name", y="cost_multiplier",
                 horizontal=True, sort="-cost_multiplier", color=CONDITION_COLOR,
                 x_label="Times more expensive", y_label="")
with right:
    st.dataframe(
        year_conditions.drop(columns="year"),
        hide_index=True,
        column_config={
            "condition_name": "Condition",
            "members_with_condition": st.column_config.NumberColumn("Members", format="localized"),
            "prevalence_pct": st.column_config.NumberColumn("Prevalence", format="%.1f%%"),
            "pmpm_with_condition": st.column_config.NumberColumn("PMPM with", format="$%.2f"),
            "pmpm_without_condition": st.column_config.NumberColumn("PMPM without", format="$%.2f"),
            "cost_multiplier": st.column_config.NumberColumn("× more", format="%.2f"),
        },
    )

st.divider()

# ---------------------------------------------------------------- readmissions + DRGs
left, right = st.columns(2)

with left:
    st.subheader("30-day readmission rate by month")
    st.line_chart(monthly_readmissions, x="discharge_month", y="readmission_rate_pct",
                  color=READMISSION_COLOR,
                  x_label="Discharge month", y_label="Readmission rate (%)")
    st.info("The steady slide from about 17% to about 5% while admissions stay flat "
            "comes from the CMS synthetic data, not from the pipeline. See "
            "`analyses/readmission_by_month.sql`.")

with right:
    st.subheader("Top 10 DRGs by inpatient spend, 2008-2009")
    st.dataframe(
        top_drgs,
        hide_index=True,
        column_config={
            "cost_rank": "Rank",
            "drg_code": "DRG",
            "stays": st.column_config.NumberColumn("Stays", format="localized"),
            "total_paid": st.column_config.NumberColumn("Total paid", format="dollar"),
            "avg_paid_per_stay": st.column_config.NumberColumn("Avg per stay", format="dollar"),
            "alos_days": st.column_config.NumberColumn("ALOS", format="%.1f"),
            "pct_of_inpatient_paid": st.column_config.NumberColumn("% of spend", format="%.2f%%"),
        },
    )
    st.info("CMS scrambles DRG codes in the synthetic data, so spend is nearly flat "
            "across DRGs. The model is correct; this ranking is not meaningful on SynPUF.")

st.divider()

# ---------------------------------------------------------------- data quality
st.subheader("Data quality and reconciliation")
q1, q2, q3 = st.columns(3)
q1.metric("Claims in fct_claims", f"{int(quality['claims']):,}",
          help="Matches the CMS source files: 66,773 inpatient + 790,790 outpatient.")
q2.metric("Total paid", f"${quality['paid']:,.2f}",
          help="Matches the answer key to the cent: $639,260,180 + $224,524,710.")
q3.metric("Claims with no service date", f"{int(quality['undated_claims']):,}",
          help=f"${quality['undated_paid']:,.0f} paid. Kept so totals reconcile, "
               "excluded from yearly and monthly KPIs.")
st.caption("Every layer (raw → staging → marts → stays) is reconciled by dbt tests "
           "on each pipeline run.")