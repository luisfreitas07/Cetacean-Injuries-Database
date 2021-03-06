# -*- encoding: utf-8 -*-

import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from cetacean_incidents.apps.clean_cache import (
    CacheDependency,
    TestList,
)

from cetacean_incidents.apps.delete_guard import guard_deletes

from cetacean_incidents.apps.documents.models import Documentable

from cetacean_incidents.apps.taxons.models import Taxon
from cetacean_incidents.apps.taxons.utils import probable_taxon

from ..utils import probable_gender

from imported import Importable

GENDERS = (
    ("f", "female"),
    ("m", "male"),
)

class AnimalManager(models.Manager):
    
    def animals_under_taxon(self, taxon):
        '''\
        Returns a queryset of animals determined to be either in the taxon given
        or in a subtaxon of it.
        '''
        return self.filter(determined_taxon__in=Taxon.objects.descendants_ids(taxon))

class Animal(Documentable, Importable):
    field_number = models.CharField(
        max_length= 255,
        blank= True,
        verbose_name= "stranding field number",
        help_text= "The field number assigned to this animal by the stranding network. Left blank for animals with no number. If not blank, the field number must be unique to this animal.",
    )

    name = models.CharField(
        blank= True,
        unique= False, # Names aren't assigned by us, so leave open the
                       # posibility for duplicates
        max_length= 255,
        help_text= u'Name(s) given to this particular animal. E.g. “Kingfisher”, “RW #2427”. Separate multiple names with commas. This field is intended as a catch-all for animal identifiers besides the field number (which is stored separately).'
    )
    
    @property
    def names(self):
        if not self.name:
            return []
        return filter(lambda n: bool(n), [n.strip() for n in self.name.split(',')])

    determined_taxon = models.ForeignKey(
        Taxon,
        blank= True,
        null= True,
        help_text= u'The most specific taxon this animal is known to be. This will be the default taxon for new observations of this animal. This is seperate from the taxa listed in observations of it, since the observations may be mistaken or less specific.',
    )
    
    # observation_set is added to this class once Observation is initialized
    # TODO still not the ideal way of doing this
    def probable_taxon(self):
        if hasattr(self, 'observation_set'):
            return probable_taxon(self.observation_set)
        return None
    def taxon(self):
        if self.determined_taxon:
            return self.determined_taxon
        probable_taxon = self.probable_taxon()
        if probable_taxon:
            return probable_taxon
        return None
    
    determined_gender = models.CharField(
        max_length= 1,
        blank= True,
        choices= GENDERS,
        verbose_name= 'determined sex',
        help_text= u"If the sex of this animal is known, fill it in here and it will then be the default for new observations of this animal.",
    )

    def probable_gender(self):
        if hasattr(self, 'observation_set'):
            return probable_gender(self.observation_set)
        return None
    def get_probable_gender_display(self):
        gender = self.probable_gender()
        if gender is None:
            return None
        return [g[1] for g in GENDERS if g[0] == gender][0]
    def gender(self):
        if self.determined_gender:
            return self.determined_gender
        probable_gender = self.probable_gender()
        if probable_gender:
            return probable_gender
        return None

    determined_dead_before = models.DateField(
        blank= True,
        null= True,
        verbose_name= "dead on or before", # no, not really verbose, but it's 
                                           # easier to change this than to alter 
                                           # the fieldname in the schema
        help_text= u"""\
            A date when the animal was certainly dead, as determined from the observations of this animal. If you're unsure of an exact date, just put something certainly after it; e.g. if you know it was dead sometime in July of 2008, just put 2008-07-31 (or 2008-08-01). If you're totally unsure, just put the current date. Any animal with a date before today is considered currently dead.
        """
    )
    
    # TODO timezone?
    @property
    def dead(self):
        return (not self.determined_dead_before is None) and self.determined_dead_before <= datetime.date.today()
    
    carcass_disposed = models.NullBooleanField(
        blank= True,
        null= True,
        default= None,
        verbose_name= "carcass disposed?", # yeah, not very verbose, but you can't have a question mark in a fieldname
        help_text= "If this animal is dead, was the carcass disposed of?",
    )
    
    partial_necropsy = models.BooleanField(
        default= False,
        verbose_name= "partially necropsied?", # yeah, not very verbose, but you can't have a question mark in a fieldname
        help_text= "If this animal is dead, has a partial necropsy ever been performed on it?",
    )
    
    necropsy = models.BooleanField(
        default= False,
        verbose_name= "fully necropsied?", # yeah, not very verbose, but you can't have a question mark in a fieldname
        help_text= "If this animal is dead, has a full necropsy ever been performed on it?",
    )
    
    cause_of_death = models.CharField(
        max_length = 1023,
        blank= True,
        verbose_name= "probable cause of mortality",
        help_text= "If this animal is dead, what (if any) probable cause of mortality has been determined?",
    )
    
    def nmfs_ids(self):
        # TODO doesn't this belong in the entanglements app?
        ent_cases = self.case_set.filter(case_type='Entanglement').exclude(entanglement__nmfs_id__isnull=True).exclude(entanglement__nmfs_id='')
        # note that values_list() won't work on the above queryset
        return [c.entanglement.nmfs_id for c in ent_cases]
    
    def first_observation(self):
        if not self.observation_set.count():
            return None
        return self.observation_set.order_by('datetime_observed')[0]
    
    def last_observation(self):
        if not self.observation_set.count():
            return None
        return self.observation_set.order_by('datetime_observed').reverse()[0]
    
    def clean(self):
        if False:
            if not self.field_number is None and self.field_number != '':
                # check that an existing animal doesn't already have this field_number
                animals = Animal.objects.filter(field_number=self.field_number)
                if self.id:
                    animals = animals.exclude(id=self.id)
                if animals.count() > 0:
                    raise ValidationError("field number '%s' is already in use by animal '%s'" % (self.field_number, unicode(animals[0])))

        if self.necropsy and not self.determined_dead_before:
            self.determined_dead_before = datetime.date.today()
    
    def _get_deps(self, fieldname):
        deps = CacheDependency(
            update= {self: TestList([True])},
            delete= {self: TestList([True])},
        )
        
        if fieldname == 'taxon':
            deps |= self._get_deps('probable_taxon')
        
        if fieldname == 'probable_taxon':
            if not self.determined_taxon:
                from cetacean_incidents.apps.incidents.models import Observation
                deps |= CacheDependency(
                    create= {
                        Observation: TestList([
                            lambda o: o.animal == self,
                        ]),
                    },
                )
                for o in self.observation_set.all():
                    deps |= CacheDependency(
                        update= {o: TestList([True])},
                        delete= {o: TestList([True])},
                    )
                # TODO depend on the relationships of the taxa in those observations?
        
        return deps
    
    def get_html_options(self):
        opts = super(Animal, self).get_html_options()
        
        opts['template'] = u'animal.html'
        
        if not 'context' in opts:
            opts['context'] = {}
        opts['context'].update({
            'animal': self,
            'multiple_ids': self.names and self.field_number or len(self.names) > 1,
        })
        
        opts['use_cache'] = True
        
        if not 'cache_deps' in opts:
            opts['cache_deps'] = CacheDependency()
        
        # TODO animal.html uses animal.dead, which depends on today's date
        opts['cache_deps'] |= CacheDependency(
            update= {self: TestList([True])},
            delete= {self: TestList([True])},
        )
        
        return opts
    
    def __unicode__(self):
        if self.field_number:
            return self.field_number
        if self.name:
            return self.name
        if self.id:
            return "unnamed animal #%06d" % self.id
        return "unnamed, unsaved animal"
    
    @models.permalink
    def get_absolute_url(self):
        return ('animal_detail', [str(self.id)]) 
    
    objects = AnimalManager()
    
    class Meta:
        app_label = 'incidents'
        ordering = ('field_number', 'name', 'id')

guard_deletes(Taxon, Animal, 'determined_taxon')

