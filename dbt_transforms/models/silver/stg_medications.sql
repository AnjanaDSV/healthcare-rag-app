with raw as (
    select * from read_csv_auto('../data/raw/medications.csv', header=true)
)

select
    trim("PATIENT")                         as patient_id,
    trim("DESCRIPTION")                     as medication_name,
    try_cast("START" as date)               as start_date,
    try_cast("STOP"  as date)               as stop_date,
    trim("REASONDESCRIPTION")               as reason,
    try_cast("TOTALCOST" as double)         as total_cost
from raw
where "PATIENT"     is not null
  and "DESCRIPTION" is not null
