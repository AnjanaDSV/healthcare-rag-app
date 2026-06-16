-- Aggregates all 5 Synthea tables into one rich clinical narrative per patient UUID.
-- Patients here are UUID-keyed (conditions/medications/encounters/observations share the same key).
-- MRN-keyed patients from patients.csv appear in stg_clinical_notes instead.

with

conditions_agg as (
    select
        patient_id,
        count(*)                                                                        as condition_count,
        string_agg(condition_name, '; ' order by onset_date)                           as conditions_list,
        min(onset_date)                                                                 as first_condition_date,
        max(onset_date)                                                                 as latest_condition_date
    from {{ ref('stg_conditions') }}
    group by patient_id
),

-- deduplicate medication names before aggregating
medications_deduped as (
    select distinct patient_id, medication_name
    from {{ ref('stg_medications') }}
),
medications_agg as (
    select
        patient_id,
        count(*)                                                                        as unique_medication_count,
        string_agg(medication_name, '; ' order by medication_name)                     as medications_list
    from medications_deduped
    group by patient_id
),

encounters_agg as (
    select
        patient_id,
        count(*)                                                                        as total_encounters,
        string_agg(distinct encounter_class, ', ' order by encounter_class)            as encounter_types,
        max(cast(encounter_start as date))                                              as last_encounter_date
    from {{ ref('stg_encounters') }}
    group by patient_id
),

vitals_latest as (
    select
        patient_id,
        max(case when observation_name ilike '%Body Height%'
                 then value || coalesce(' ' || units, '') end)                          as height,
        max(case when observation_name ilike '%Body Weight%'
                 then value || coalesce(' ' || units, '') end)                          as weight,
        max(case when observation_name ilike '%Body Mass Index%'
                 then value end)                                                        as bmi,
        max(case when observation_name ilike '%Systolic Blood Pressure%'
                 then value end)                                                        as bp_systolic,
        max(case when observation_name ilike '%Diastolic Blood Pressure%'
                 then value end)                                                        as bp_diastolic
    from {{ ref('stg_observations') }}
    where category = 'vital-signs'
    group by patient_id
),

-- one row per patient per lab type (most recent value)
labs_ranked as (
    select
        patient_id,
        observation_name,
        value,
        units,
        row_number() over (
            partition by patient_id, observation_name
            order by observation_date desc
        ) as rn
    from {{ ref('stg_observations') }}
    where category = 'laboratory'
),
labs_agg as (
    select
        patient_id,
        string_agg(
            observation_name || ': ' || value || coalesce(' ' || units, ''),
            '; '
            order by observation_name
        )                                                                               as recent_labs
    from labs_ranked
    where rn = 1
    group by patient_id
)

select
    c.patient_id,
    c.condition_count,
    c.conditions_list,
    c.first_condition_date,
    c.latest_condition_date,
    m.unique_medication_count,
    m.medications_list,
    e.total_encounters,
    e.encounter_types,
    e.last_encounter_date,
    v.height,
    v.weight,
    v.bmi,
    case
        when v.bp_systolic is not null and v.bp_diastolic is not null
        then v.bp_systolic || '/' || v.bp_diastolic || ' mmHg'
    end                                                                                 as blood_pressure,
    l.recent_labs,

    -- Rich clinical note text consumed by the RAG chunker
    'Patient ' || c.patient_id
        || ' — Conditions (' || c.condition_count || '): ' || c.conditions_list || '.'

        || case when m.medications_list is not null
                then ' Medications (' || m.unique_medication_count || '): ' || m.medications_list || '.'
                else ' Medications: none recorded.' end

        || case when e.total_encounters is not null
                then ' Encounters: ' || e.total_encounters
                    || ' visit(s) — types: ' || coalesce(e.encounter_types, 'N/A')
                    || coalesce('; last visit ' || e.last_encounter_date::varchar, '') || '.'
                else '' end

        || case when v.height is not null or v.weight is not null or v.bmi is not null
                then ' Vitals —'
                    || coalesce(' Height: ' || v.height, '')
                    || coalesce(', Weight: ' || v.weight, '')
                    || coalesce(', BMI: ' || v.bmi, '')
                    || case when v.bp_systolic is not null and v.bp_diastolic is not null
                            then ', BP: ' || v.bp_systolic || '/' || v.bp_diastolic || ' mmHg'
                            else '' end
                    || '.'
                else '' end

        || case when l.recent_labs is not null
                then ' Recent Labs: ' || l.recent_labs || '.'
                else '' end
                                                                                        as clinical_note_text,

    current_timestamp                                                                   as created_at

from conditions_agg c
left join medications_agg  m on c.patient_id = m.patient_id
left join encounters_agg   e on c.patient_id = e.patient_id
left join vitals_latest    v on c.patient_id = v.patient_id
left join labs_agg         l on c.patient_id = l.patient_id
order by c.patient_id
