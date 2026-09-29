-- VeloCity × Jev: Schadenmeldungen, Urteile und Auswertung
-- PostgreSQL 15+ / Supabase. Eigenes Schema, getrennt von den WaWi-Sichten v_wawi_*.
-- Wiederholbar ausführbar; löscht keine Daten.

create schema if not exists jev_labor;

-- Meldungen mit Soll-Labels (Quelle: daten/meldungen.csv)
create table if not exists jev_labor.meldung (
    meldung_id               text primary key,
    fahrrad_id               integer,
    rahmennummer             text,
    typ_code                 text not null check (typ_code in ('CITY', 'EBIKE', 'CARGO')),
    kanal                    text,
    text                     text not null,
    soll_kategorie           text not null,
    soll_schwere             text check (soll_schwere in ('gering', 'mittel', 'fahruntauglich')),
    soll_sicherheitsrelevant boolean not null,
    soll_personenschaden     boolean not null,
    soll_ist_schaden         boolean not null,
    merkmal                  text
);

comment on table jev_labor.meldung is
    'Synthetische Schadenmeldungen für VeloCity mit Soll-Labels; soll_schwere ist leer, wenn kein Schaden vorliegt.';

-- Ein Lauf = ein Datensatz, ein Modell, ein Stand der Fragen und ein Satz Schwellen
create table if not exists jev_labor.lauf (
    lauf_id        bigint generated always as identity primary key,
    zeitpunkt      timestamptz not null,
    modell         text not null,
    regel_version  text not null,
    schwellen      jsonb not null,
    input_tokens   integer,
    output_tokens  integer,
    anmerkung      text
);

-- Nachgetragen mit der Anbindung an die VeloCity-Warenwirtschaft. Dieselben
-- Zeilen stehen in velocity-fallstudie/db/aufbau/0026_jev_meldungseingang.sql;
-- wer hier eine Spalte ändert, ändert sie dort auch.
alter table jev_labor.lauf add column if not exists lauf_schluessel      text;
alter table jev_labor.lauf add column if not exists datensatz            text;
alter table jev_labor.lauf add column if not exists fragen_stand         integer;
alter table jev_labor.lauf add column if not exists fragen_fingerabdruck text;
alter table jev_labor.lauf add column if not exists freigegeben_am       timestamptz;
create unique index if not exists lauf_schluessel_uq on jev_labor.lauf (lauf_schluessel);

create table if not exists jev_labor.urteil (
    lauf_id              bigint not null references jev_labor.lauf (lauf_id) on delete cascade,
    meldung_id           text   not null references jev_labor.meldung (meldung_id),
    modell               text   not null,
    ist_schadensmeldung  numeric(6, 5) not null check (ist_schadensmeldung between 0 and 1),
    kategorie            text   not null,
    kategorie_konfidenz  numeric(6, 5) not null,
    kategorie_wkt        jsonb  not null,
    schwere_stufe        text   not null check (schwere_stufe in ('gering', 'mittel', 'fahruntauglich')),
    schwere_score        numeric(6, 5) not null,
    schwere_konfidenz    numeric(6, 5) not null,
    schwere_wkt          jsonb  not null,
    sicherheitsrelevant  numeric(6, 5) not null check (sicherheitsrelevant between 0 and 1),
    personenschaden      numeric(6, 5) not null check (personenschaden between 0 and 1),
    entscheidung         text   not null check (entscheidung in ('kein_schaden_weiterleiten', 'sperren', 'pruefen', 'auftrag')),
    eskalation           boolean not null,
    begruendung          text,
    wawi_kategorie       text,
    wawi_schwere         text,
    input_tokens         integer,
    output_tokens        integer,
    request_id           text,
    primary key (lauf_id, meldung_id)
);

create index if not exists urteil_meldung_idx on jev_labor.urteil (meldung_id);

-- Soll-Entscheidung aus den Labels; dieselbe Regel wie soll_entscheidung() in regeln.py
create or replace view jev_labor.v_urteil_vs_soll as
select
    u.lauf_id,
    m.meldung_id,
    m.typ_code,
    m.merkmal,
    m.text,
    m.soll_kategorie,
    u.kategorie,
    u.kategorie_konfidenz,
    m.soll_schwere,
    u.schwere_stufe,
    u.schwere_konfidenz,
    m.soll_sicherheitsrelevant,
    u.sicherheitsrelevant,
    m.soll_personenschaden,
    u.personenschaden,
    case
        when not m.soll_ist_schaden then 'kein_schaden_weiterleiten'
        when m.soll_sicherheitsrelevant or m.soll_schwere = 'fahruntauglich' then 'sperren'
        when m.soll_kategorie = 'keine_zuordnung' then 'pruefen'
        else 'auftrag'
    end as soll_entscheidung,
    u.entscheidung,
    u.eskalation,
    u.begruendung
from jev_labor.urteil u
join jev_labor.meldung m using (meldung_id);

-- Kennzahlen je Lauf
create or replace view jev_labor.v_lauf_kennzahlen as
select
    l.lauf_id,
    l.zeitpunkt,
    l.modell,
    l.schwellen,
    count(*)                                                              as meldungen,
    round(avg((v.entscheidung <> 'pruefen')::int), 3)                     as automatisierungsquote,
    count(*) filter (where v.entscheidung = 'pruefen')                    as zur_pruefung,
    count(*) filter (where v.entscheidung <> 'pruefen'
                       and v.entscheidung <> v.soll_entscheidung)         as fehlentscheidungen,
    count(*) filter (where v.soll_entscheidung = 'sperren'
                       and v.entscheidung in ('auftrag', 'kein_schaden_weiterleiten')) as sicherheitsschaden_uebersehen,
    count(*) filter (where v.entscheidung = 'sperren'
                       and v.soll_entscheidung <> 'sperren')              as unnoetig_gesperrt,
    round(avg((v.kategorie = v.soll_kategorie)::int)
          filter (where v.soll_schwere is not null), 3)                   as trefferquote_kategorie,
    round(avg((v.schwere_stufe = v.soll_schwere)::int)
          filter (where v.soll_schwere is not null), 3)                   as trefferquote_schwere,
    l.input_tokens,
    l.output_tokens
from jev_labor.lauf l
join jev_labor.v_urteil_vs_soll v using (lauf_id)
group by l.lauf_id;

-- Konfusionsmatrix der Kategorie in Langform (für Pivot in Power BI oder Excel)
create or replace view jev_labor.v_kategorie_konfusion as
select lauf_id, soll_kategorie, kategorie as jev_kategorie, count(*) as anzahl,
       round(avg(kategorie_konfidenz), 3) as mittlere_konfidenz
from jev_labor.v_urteil_vs_soll
where soll_schwere is not null
group by lauf_id, soll_kategorie, kategorie;

-- Kalibrierung: Wie oft ist "sicherheitsrelevant" wirklich wahr, je Wahrscheinlichkeitsband?
create or replace view jev_labor.v_kalibrierung_sicherheit as
select lauf_id,
       width_bucket(sicherheitsrelevant, 0, 1.000001, 5) as band,
       round(min(sicherheitsrelevant), 2)                as p_von,
       round(max(sicherheitsrelevant), 2)                as p_bis,
       count(*)                                          as anzahl,
       round(avg(sicherheitsrelevant), 3)                as mittlere_wahrscheinlichkeit,
       round(avg(soll_sicherheitsrelevant::int), 3)      as tatsaechlicher_anteil
from jev_labor.v_urteil_vs_soll
where soll_schwere is not null
group by lauf_id, band
order by lauf_id, band;

-- Arbeitsliste für die Disposition: offene Prüffälle und Eskalationen des letzten Laufs
create or replace view jev_labor.v_arbeitsliste as
select m.meldung_id, m.rahmennummer, m.fahrrad_id, m.text,
       u.entscheidung, u.eskalation, u.begruendung, u.wawi_kategorie, u.wawi_schwere
from jev_labor.urteil u
join jev_labor.meldung m using (meldung_id)
where u.lauf_id = (select max(lauf_id) from jev_labor.lauf)
  and (u.entscheidung in ('pruefen', 'sperren') or u.eskalation)
order by u.eskalation desc, (u.entscheidung = 'sperren') desc, u.sicherheitsrelevant desc;

-- Optional: Lesezugriff für die Studierenden-Rolle (Rollenname anpassen)
-- grant usage on schema jev_labor to studi;
-- grant select on all tables in schema jev_labor to studi;
-- alter default privileges in schema jev_labor grant select on tables to studi;
