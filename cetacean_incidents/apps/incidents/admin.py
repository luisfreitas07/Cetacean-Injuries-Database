from django.contrib import admin
from reversion.admin import VersionAdmin
from models import Animal, Case, Observation, Entanglement, EntanglementObservation, Shipstrike, ShipstrikeObservation, GearType, GearTypeRelation, StrikingVesselInfo
from cetacean_incidents.apps.vessels.admin import VesselAdmin

class AnimalAdmin(VersionAdmin):
    pass
admin.site.register(Animal, AnimalAdmin)

class CaseAdmin(VersionAdmin):
    pass
admin.site.register(Case, CaseAdmin)

class EntanglementAdmin(CaseAdmin):
    pass
admin.site.register(Entanglement, EntanglementAdmin)

class ShipstrikeAdmin(CaseAdmin):
    pass
admin.site.register(Shipstrike, ShipstrikeAdmin)

class ObservationAdmin(VersionAdmin):
    pass
admin.site.register(Observation, ObservationAdmin)

class EntanglementObservationAdmin(ObservationAdmin):
    pass
admin.site.register(EntanglementObservation, EntanglementObservationAdmin)

class GearTypeAdmin(VersionAdmin):
    pass
admin.site.register(GearType, GearTypeAdmin)

class GearTypeRelationAdmin(VersionAdmin):
    pass
admin.site.register(GearTypeRelation, GearTypeRelationAdmin)

class ShipstrikeObservationAdmin(ObservationAdmin):
    pass
admin.site.register(ShipstrikeObservation, ShipstrikeObservationAdmin)

class StrikingVesselAdmin(VesselAdmin):
    pass
admin.site.register(StrikingVesselInfo, StrikingVesselAdmin)

