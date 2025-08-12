-- SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
-- SPDX-License-Identifier: MPL-2.0
COPY(
    SELECT DISTINCT
        brugervendtnoegle AS user_key,
        rel.rel_maal_uuid AS employee,
        brel.rel_maal_urn AS cpr
    FROM
        organisationfunktion_registrering reg
    INNER JOIN
        organisationfunktion_attr_egenskaber attr ON
        reg.id = attr.organisationfunktion_registrering_id
    INNER JOIN
        organisationfunktion_relation rel ON
        reg.id = rel.organisationfunktion_registrering_id
    INNER JOIN
        bruger_registrering breg ON
        bruger_id = rel_maal_uuid
    INNER JOIN
        bruger_relation brel ON
        breg.id = brel.bruger_registrering_id
    WHERE
        funktionsnavn = 'Engagement'
        AND rel.rel_type = 'tilknyttedebrugere'
        AND brel.rel_type = 'tilknyttedepersoner'
        AND brugervendtnoegle <> '-'
    -- LIMIT 5
) TO '/tmp/engagements.csv' DELIMITER ',' CSV HEADER;
