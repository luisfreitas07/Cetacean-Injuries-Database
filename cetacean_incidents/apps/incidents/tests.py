import unittest
from models import GearType, GearTypeRelation

class GearTypeTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def test_implied_supertypes(self):
        line = GearType(name='line')
        line.save()
        self.assertEqual(line.implied_supertypes, frozenset())

        long_line = GearType(name='long line')
        long_line.save()
        GearTypeRelation(supertype=line, subtype=long_line).save()
        self.assertEqual(long_line.implied_supertypes, frozenset([line]))

        longer_line = GearType(name='longer line')
        longer_line.save()
        GearTypeRelation(supertype=long_line, subtype=longer_line).save()
        self.assertEqual(
            longer_line.implied_supertypes,
            frozenset([line, long_line])
        )
        
        red = GearType(name='red')
        red.save()
        GearTypeRelation(supertype=red, subtype=long_line).save()
        self.assertEqual(
            longer_line.implied_supertypes,
            frozenset([line, long_line, red])
        )

    def test_cyclecheck(self):
        line = GearType(name='line')
        line.save()
        long_line = GearType(name='long line')
        long_line.save()
        # no cycles to begin with, so this shouldn't raise exceptions
        try:
            GearTypeRelation(supertype=line, subtype=long_line).save()
        except GearTypeRelation.DAGException as (message):
            self.fail(message)
        
        # create a self-cycle
        self.assertRaises(
            GearTypeRelation.DAGException,
            GearTypeRelation(subtype=line, supertype=line).save,
        )
        
        # create a 3-node cycle
        longer_line = GearType(name='longer line')
        longer_line.save()
        GearTypeRelation(supertype=long_line, subtype=longer_line).save()
        self.assertRaises(
            GearTypeRelation.DAGException,
            GearTypeRelation(subtype=line, supertype=long_line).save,
        )

