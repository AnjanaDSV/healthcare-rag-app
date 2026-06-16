with raw as (
    select * from read_csv_auto('../data/raw/encounters.csv', header=true)
)

select
    trim("PATIENT")                             as patient_id,
    trim("Id")                                  as encounter_id,
    try_cast("START" as timestamp)              as encounter_start,
    try_cast("STOP"  as timestamp)              as encounter_stop,
    upper(trim("ENCOUNTERCLASS"))               as encounter_class,
    trim("DESCRIPTION")                         as encounter_description,
    trim("REASONDESCRIPTION")                   as reason,
    try_cast("TOTAL_CLAIM_COST" as double)      as total_claim_cost
from raw
where "PATIENT" is not null
