alter table "ENTANGLEMENTS_ENTANGLEMENT4F56"
  add ("DISENTANGLEMENT_ATTEMPTED" NUMBER(1) CHECK (("DISENTANGLEMENT_ATTEMPTED" IN (0,1)) OR ("DISENTANGLEMENT_ATTEMPTED" IS NULL)))
;

