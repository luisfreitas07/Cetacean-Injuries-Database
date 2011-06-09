-- for Oracle

-- assumes there aren't more than 9000 documentables already, and no more than
-- 2000 contacts.

/*
 * change the sequence DOCUMENTS_DOCUMENTABLE_SQ to be at 11000
 */
alter sequence DOCUMENTS_DOCUMENTABLE_SQ increment by 2200;
select DOCUMENTS_DOCUMENTABLE_SQ.nextval from dual;
alter sequence DOCUMENTS_DOCUMENTABLE_SQ increment by 1;

/*
 * change the trigger CONTACTS_CONTACT_TR to use DOCUMENTS_DOCUMENTABLE_SQ
 */

-- Contact
alter table CONTACTS_CONTACT add "DOCUMENTABLE_PTR_ID" NUMBER(11) REFERENCES "DOCUMENTS_DOCUMENTABLE" ("ID") DEFERRABLE INITIALLY DEFERRED;

update CONTACTS_CONTACT set DOCUMENTABLE_PTR_ID = ID + 9000 where ID < 11000;
update CONTACTS_CONTACT set DOCUMENTABLE_PTR_ID = ID where ID >= 11000;

insert into DOCUMENTS_DOCUMENTABLE (select DOCUMENTABLE_PTR_ID from CONTACTS_CONTACT);

alter table CONTACTS_CONTACT modify (DOCUMENTABLE_PTR_ID NOT NULL); 

/*
 * remove foreign-key contraint on CONTACTS_CONTACT_AFFILIATIONS.CONTACT_ID
 * remove foreign-key contraint on ENTANGLEMENTS_ENTANGLEMENT.ANALYZED_BY_ID
 * remove foreign-key contraint on ENTANGLEMENTS_ENTANGLEMENT4F56.GEAR_GIVER_ID
 * remove foreign-key contraint on ENTANGLEMENTS_ENTANGLEMENT4F56.GEAR_RETRIEVER_ID
 * remove foreign-key contraint on INCIDENTS_OBSERVATION.OBSERVER_ID
 * remove foreign-key contraint on INCIDENTS_OBSERVATION.REPORTER_ID
 * remove foreign-key contraint on SHIPSTRIKES_STRIKINGVESSELINFO.CAPTAIN_ID
 * remove foreign-key contraint on VESSELS_VESSELINFO.CONTACT_ID
 */

/*
 * chamge primary-key of CONTACTS_CONTACT from ID to DOCUMENTABLE_PTR_ID
 */
 
alter table CONTACTS_CONTACT drop column ID;

/* do this for each of the columns listed above */
-- update OTHERTABLE set OTHERFIELD_ID = OTHERFIELD_ID + 9000 where OTHERFIELD_ID < 11000;
-- alter table OTHERTABLE add foreign key (OTHERFIELD_ID) references "CONTACTS_CONTACT" ("DOCUMENTABLE_PTR_ID") DEFERRABLE INITIALLY DEFERRED;

update CONTACTS_CONTACT_AFFILIATIONS set CONTACT_ID = CONTACT_ID + 9000 where CONTACT_ID < 11000;
alter table CONTACTS_CONTACT_AFFILIATIONS add foreign key (CONTACT_ID) references "CONTACTS_CONTACT" ("DOCUMENTABLE_PTR_ID") DEFERRABLE INITIALLY DEFERRED;

update ENTANGLEMENTS_ENTANGLEMENT set ANALYZED_BY_ID = ANALYZED_BY_ID + 9000 where ANALYZED_BY_ID < 11000;
alter table ENTANGLEMENTS_ENTANGLEMENT add foreign key (ANALYZED_BY_ID) references "CONTACTS_CONTACT" ("DOCUMENTABLE_PTR_ID") DEFERRABLE INITIALLY DEFERRED;

update ENTANGLEMENTS_ENTANGLEMENT4F56 set GEAR_GIVER_ID = GEAR_GIVER_ID + 9000 where GEAR_GIVER_ID < 11000;
alter table ENTANGLEMENTS_ENTANGLEMENT4F56 add foreign key (GEAR_GIVER_ID) references "CONTACTS_CONTACT" ("DOCUMENTABLE_PTR_ID") DEFERRABLE INITIALLY DEFERRED;

update ENTANGLEMENTS_ENTANGLEMENT4F56 set GEAR_RETRIEVER_ID = GEAR_RETRIEVER_ID + 9000 where GEAR_RETRIEVER_ID < 11000;
alter table ENTANGLEMENTS_ENTANGLEMENT4F56 add foreign key (GEAR_RETRIEVER_ID) references "CONTACTS_CONTACT" ("DOCUMENTABLE_PTR_ID") DEFERRABLE INITIALLY DEFERRED;

update INCIDENTS_OBSERVATION set OBSERVER_ID = OBSERVER_ID + 9000 where OBSERVER_ID < 11000;
alter table INCIDENTS_OBSERVATION add foreign key (OBSERVER_ID) references "CONTACTS_CONTACT" ("DOCUMENTABLE_PTR_ID") DEFERRABLE INITIALLY DEFERRED;

update INCIDENTS_OBSERVATION set REPORTER_ID = REPORTER_ID + 9000 where REPORTER_ID < 11000;
alter table INCIDENTS_OBSERVATION add foreign key (REPORTER_ID) references "CONTACTS_CONTACT" ("DOCUMENTABLE_PTR_ID") DEFERRABLE INITIALLY DEFERRED;

update SHIPSTRIKES_STRIKINGVESSELINFO set CAPTAIN_ID = CAPTAIN_ID + 9000 where CAPTAIN_ID < 11000;
alter table SHIPSTRIKES_STRIKINGVESSELINFO add foreign key (CAPTAIN_ID) references "CONTACTS_CONTACT" ("DOCUMENTABLE_PTR_ID") DEFERRABLE INITIALLY DEFERRED;

update VESSELS_VESSELINFO set CONTACT_ID = CONTACT_ID + 9000 where CONTACT_ID < 11000;
alter table VESSELS_VESSELINFO add foreign key (CONTACT_ID) references "CONTACTS_CONTACT" ("DOCUMENTABLE_PTR_ID") DEFERRABLE INITIALLY DEFERRED;

/*
 * drop trigger CONTACTS_CONTACT_TR
 */

