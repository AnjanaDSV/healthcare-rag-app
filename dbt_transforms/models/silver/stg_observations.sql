with raw as (
    select * from read_csv_auto('../data/raw/observations.csv', header=true)
)

select
    trim("PATIENT")                         as patient_id,
    try_cast("DATE" as timestamp)           as observation_date,
    trim("DESCRIPTION")                     as observation_name,
    trim("VALUE")                           as value,
    trim("UNITS")                           as units,
    trim("CATEGORY")                        as category,
    trim("CODE")                            as loinc_code
from raw
where "PATIENT"  is not null
  and "VALUE"    is not null
  and "CATEGORY" in ('vital-signs', 'laboratory')
