-- patients.csv is the masked/faker output from hipaa-phi-masking-engine.
-- Uses MRN-based IDs (not UUIDs), so it does not join to the other Synthea tables.
with raw as (
    select * from read_csv_auto('../data/raw/patients.csv', header=true)
)

select
    trim("mrn")                                                         as patient_id,
    trim("name")                                                        as patient_name,
    try_cast(strptime(nullif(trim("dob"), ''), '%m/%d/%Y') as date)    as date_of_birth,
    trim("diagnosis")                                                   as primary_diagnosis,
    trim("address")                                                     as address,
    trim("insurance_id")                                                as insurance_id
from raw
where "mrn" is not null
  and "name"  is not null
