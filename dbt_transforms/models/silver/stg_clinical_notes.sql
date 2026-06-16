-- Generates one note per MRN-based patient from the masked patients.csv.
-- UUID-based patients (conditions/medications/encounters/observations) are handled
-- in the richer gold/clinical_summary model.
with patients as (
    select * from {{ ref('stg_patients') }}
)

select
    patient_id,
    patient_name,
    primary_diagnosis                               as condition_name,
    null::date                                      as onset_date,
    null::varchar                                   as snomed_code,
    address,
    'Patient ' || patient_name
        || ' (MRN: ' || patient_id || ')'
        || coalesce(', born ' || date_of_birth::varchar, '')
        || ', primary diagnosis: ' || primary_diagnosis
        || coalesce('. Address: ' || address, '')
        || '.'
                                                    as note_text
from patients
