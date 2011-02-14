-- for oracle

-- add INCIDENTS_OBSERVATION_CASES table
CREATE TABLE "INCIDENTS_OBSERVATION_CASES" (
    "ID" NUMBER(11) NOT NULL PRIMARY KEY,
    "OBSERVATION_ID" NUMBER(11) NOT NULL,
    "CASE_ID" NUMBER(11) NOT NULL,
    UNIQUE ("OBSERVATION_ID", "CASE_ID")
)
;

DECLARE
    i INTEGER;
BEGIN
    SELECT COUNT(*) INTO i FROM USER_CATALOG
        WHERE TABLE_NAME = 'INCIDENTS_OBSERVATION_CASES_SQ' AND TABLE_TYPE = 'SEQUENCE';
    IF i = 0 THEN
        EXECUTE IMMEDIATE 'CREATE SEQUENCE "INCIDENTS_OBSERVATION_CASES_SQ"';
    END IF;
END;
/

CREATE OR REPLACE TRIGGER "INCIDENTS_OBSERVATION_CASES_TR"
BEFORE INSERT ON "INCIDENTS_OBSERVATION_CASES"
FOR EACH ROW
WHEN (new."ID" IS NULL)
    BEGIN
        SELECT "INCIDENTS_OBSERVATION_CASES_SQ".nextval
        INTO :new."ID" FROM dual;
    END;
/

-- add contraints to INCIDENTS_OBSERVATION_CASES
-- INCIDENTS_OBSERVATION_CASES.CASE_ID -> INCIDENTS_CASE
-- INCIDENTS_OBSERVATION_CASES.OBSERVATION_ID -> INCIDENTS_OBSERVATION
ALTER TABLE "INCIDENTS_OBSERVATION_CASES" ADD CONSTRAINT "CASE_ID_REFS_DOCUMENTABLE_2980" FOREIGN KEY ("CASE_ID") REFERENCES "INCIDENTS_CASE" ("DOCUMENTABLE_PTR_ID") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "INCIDENTS_OBSERVATION_CASES" ADD CONSTRAINT "OBSERVATION_ID_REFS_DOCUME0EF1" FOREIGN KEY ("OBSERVATION_ID") REFERENCES "INCIDENTS_OBSERVATION" ("DOCUMENTABLE_PTR_ID") DEFERRABLE INITIALLY DEFERRED;

-- populate INCIDENTS_OBSERVATION_CASES
insert into INCIDENTS_OBSERVATION_CASES (OBSERVATION_ID, CASE_ID) (select DOCUMENTABLE_PTR_ID, CASE_ID from INCIDENTS_OBSERVATION);

-- add "ANIMAL_ID" field to "INCIDENTS_OBSERVATION"
alter table INCIDENTS_OBSERVATION add column "ANIMAL_ID" NUMBER(11) REFERENCES "INCIDENTS_ANIMAL" ("DOCUMENTABLE_PTR_ID") DEFERRABLE INITIALLY DEFERRED;
-- add index
CREATE INDEX "INCIDENTS_OBSERVATION_5605F246" ON "INCIDENTS_OBSERVATION" ("ANIMAL_ID");
-- populate
update INCIDENTS_OBSERVATION set ANIMAL_ID = (
    select INCIDENTS_CASE.ANIMAL_ID
     from (
        select INCIDENTS_CASE.ANIMAL_ID, INCIDENTS_OBSERVATION_CASES.OBSERVATION_ID
         from 
          INCIDENTS_OBSERVATION_CASES join INCIDENTS_CASE
          on (INCIDENTS_OBSERVATION_CASES.CASE_ID = INCIDENTS_CASE.DOCUMENTABLE_PTR_ID)
        )
     where OBSERVATION_ID = DOCUMENTABLE_PTR_ID
);
-- mark as NOT NULL
ALTER TABLE "INCIDENTS_OBSERVATION" MODIFY ("ANIMAL_ID" NOT NULL);

-- remove "CASE_ID" field from "INCIDENTS_OBSERVATION"
ALTER TABLE "INCIDENTS_OBSERVATION" drop column "CASE_ID";


