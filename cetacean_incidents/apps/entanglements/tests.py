from django.test import TestCase

from cetacean_incidents.apps.incidents.models import (
    Animal,
    Observation,
)
from cetacean_incidents.apps.uncertain_datetimes.models import UncertainDateTime

from models import (
    Entanglement,
    EntanglementObservation,
    GearAttribute,
    GearAttributeImplication,
)
from forms import GearOwnerForm

class GearAttributeTestCase(TestCase):
    def setUp(self):
        pass

    def test_implied_supertypes(self):
        line = GearAttribute.objects.create(name='line')
        self.assertEqual(line.implied_supertypes, frozenset())

        long_line = GearAttribute.objects.create(name='long line')
        GearAttributeImplication(supertype=line, subtype=long_line).save()
        self.assertEqual(long_line.implied_supertypes, frozenset([line]))

        longer_line = GearAttribute.objects.create(name='longer line')
        GearAttributeImplication(supertype=long_line, subtype=longer_line).save()
        self.assertEqual(
            longer_line.implied_supertypes,
            frozenset([line, long_line])
        )
        
        red = GearAttribute.objects.create(name='red')
        GearAttributeImplication(supertype=red, subtype=long_line).save()
        self.assertEqual(
            longer_line.implied_supertypes,
            frozenset([line, long_line, red])
        )

    def test_cyclecheck(self):
        line = GearAttribute.objects.create(name='line')
        long_line = GearAttribute.objects.create(name='long line')
        # no cycles to begin with, so this shouldn't raise exceptions
        try:
            GearAttributeImplication(supertype=line, subtype=long_line).save()
        except GearAttributeImplication.DAGException as (message):
            self.fail(message)
        
        # create a self-cycle
        self.assertRaises(
            GearAttributeImplication.DAGException,
            GearAttributeImplication(subtype=line, supertype=line).save,
        )
        
        # create a 3-node cycle
        longer_line = GearAttribute.objects.create(name='longer line')
        GearAttributeImplication(supertype=long_line, subtype=longer_line).save()
        self.assertRaises(
            GearAttributeImplication.DAGException,
            GearAttributeImplication(subtype=line, supertype=long_line).save,
        )

class EntanglementTestCase(TestCase):
    def test_geartypes(self):
        e = Entanglement.objects.create(animal=Animal.objects.create())

        line = GearAttribute.objects.create(name='line')

        long_line = GearAttribute.objects.create(name='long line')
        GearAttributeImplication(supertype=line, subtype=long_line).save()

        longer_line = GearAttribute.objects.create(name='longer line')
        GearAttributeImplication(supertype=long_line, subtype=longer_line).save()
        
        self.assertEqual(
            set(e.analyzed_gear_attributes.all()),
            set(),
        )
        self.assertEqual(
            set(e.implied_analyzed_gear_attributes),
            set(),
        )
        
        e.analyzed_gear_attributes.add(long_line)
        self.assertEqual(
            set(e.analyzed_gear_attributes.all()),
            set([long_line]),
        )
        self.assertEqual(
            set(e.implied_analyzed_gear_attributes),
            set([line]),
        )
        
        e.analyzed_gear_attributes.add(longer_line)
        self.assertEqual(
            set(e.analyzed_gear_attributes.all()),
            set([long_line, longer_line]),
        )
        self.assertEqual(
            set(e.implied_analyzed_gear_attributes),
            set([line]),
        )

    def test_gear_recovered(self):
        a = Animal.objects.create()
        e = Entanglement.objects.create(animal=a)
        true_obv = EntanglementObservation.objects.create(
            observation_ptr= Observation.objects.create(
                animal= a,
                datetime_observed= UncertainDateTime(year=2000),
                datetime_reported= UncertainDateTime(year=2000),
            ),
            gear_retrieved= True,
        )
        true_obv.observation_ptr.cases.add(e)
        false_obv = EntanglementObservation.objects.create(
            observation_ptr= Observation.objects.create(
                animal= a,
                datetime_observed= UncertainDateTime(year=2000),
                datetime_reported= UncertainDateTime(year=2000),
            ),
            gear_retrieved= False,
        )
        false_obv.observation_ptr.cases.add(e)
        none_obv = EntanglementObservation.objects.create(
            observation_ptr= Observation.objects.create(
                animal= a,
                datetime_observed= UncertainDateTime(year=2000),
                datetime_reported= UncertainDateTime(year=2000),
            ),
            gear_retrieved= None,
        )
        none_obv.observation_ptr.cases.add(e)
        self.assertEqual(
            e.gear_retrieved,
            True,
        )
        true_obv.gear_retrieved = False
        true_obv.save()
        self.assertEqual(
            e.gear_retrieved,
            None,
        )
        none_obv.gear_retrieved = False
        none_obv.save()
        self.assertEqual(
            e.gear_retrieved,
            False,
        )

class GearOwnerFormTestCase(TestCase):
    
    def test_blank(self):
        form = GearOwnerForm({})
        self.assertEquals(form.is_valid(), True)

class EntanglementObservationTestCase(TestCase):
    
    def setUp(self):
        self.o = Observation.objects.create(
            animal= Animal.objects.create(),
            datetime_observed= UncertainDateTime(2010),
            datetime_reported= UncertainDateTime(2010),
        )
        
    def test_basics(self):
        
        self.assertRaises(EntanglementObservation.DoesNotExist, getattr, self.o, 'entanglements_entanglementobservation')
        
        eo = EntanglementObservation.objects.create(
            observation_ptr= self.o,
        )
        
        self.assertEqual(self.o.entanglements_entanglementobservation, eo)
        
    def test_add_entanglement_extension_handler(self):
        a = Animal.objects.create()
        e = Entanglement.objects.create(
            animal= a
        )
        o1 = Observation.objects.create(
            animal= a,
            datetime_observed= UncertainDateTime(2009),
            datetime_reported= UncertainDateTime(2009),
        )
        self.assertRaises(EntanglementObservation.DoesNotExist, getattr, o1, 'entanglements_entanglementobservation')
        o1.cases.add(e)
        o1.entanglements_entanglementobservation
        
        o2 = Observation.objects.create(
            animal= a,
            datetime_observed= UncertainDateTime(2008),
            datetime_reported= UncertainDateTime(2008),
        )
        self.assertRaises(EntanglementObservation.DoesNotExist, getattr, o2, 'entanglements_entanglementobservation')
        e.observation_set.add(o2)
        # reload o2
        o2 = Observation.objects.get(pk=o2.pk)
        o2.entanglements_entanglementobservation

