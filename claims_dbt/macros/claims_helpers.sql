{% macro parse_date(column_name) %}
    try(cast(date_parse(nullif(trim({{ column_name }}), ''), '%Y%m%d') as date))
{% endmacro %}


{% macro to_amount(column_name) %}
    try(cast(nullif(trim({{ column_name }}), '') as decimal(18,2)))
{% endmacro %}