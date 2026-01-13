-- SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
-- SPDX-License-Identifier: MPL-2.0
WITH dublets AS (
    SELECT DISTINCT
        brugervendtnoegle AS user_key,
        brel.rel_maal_urn AS cpr,
        reg.organisationfunktion_id AS eng
    FROM
        organisationfunktion_registrering reg
    INNER JOIN
        organisationfunktion_attr_egenskaber attr ON
        reg.id = attr.organisationfunktion_registrering_id
    INNER JOIN
        organisationfunktion_tils_gyldighed tils ON
        reg.id = tils.organisationfunktion_registrering_id
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
        upper((reg.registrering).timeperiod) = 'infinity'
        -- AND gyldighed = 'Aktiv'
        AND funktionsnavn = 'Engagement'
        AND rel.rel_type = 'tilknyttedebrugere'
        AND brel.rel_type = 'tilknyttedepersoner'
        AND brugervendtnoegle <> '-'
    -- LIMIT 50
)
SELECT
    user_key,
    cpr,
    count(eng)
FROM
    dublets
GROUP BY
    user_key,
    cpr
HAVING
    count(eng) > 1
;
