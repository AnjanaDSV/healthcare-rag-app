with raw as (
    select * from read_csv_auto('../data/raw/conditions.csv', header=true)
)

select
    "PATIENT"                       as patient_id,
    trim("DESCRIPTION")             as condition_name,
    cast("START" as date)           as onset_date,
    cast("CODE" as varchar)         as snomed_code
from raw
where "PATIENT" is not null
  and "DESCRIPTION" is not null
