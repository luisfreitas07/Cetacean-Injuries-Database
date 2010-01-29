from django.db import models
from cetacean_incidents.apps.contacts.models import Contact, Organization
from cetacean_incidents.apps.vessels.models import VesselInfo
from cetacean_incidents.apps.locations.models import Location
from django.contrib.auth.models import User
from django.contrib.localflavor.us.models import USStateField
from utils import probable_gender, probable_taxon

GENDERS = (
    ("f", "female"),
    ("m", "male"),
)

class Taxon(models.Model):
    '''\
    A taxon is a generic term for a grouping of organisms made by a taxonimist.
    Whether it's a genus or a species (or a subspecies or a infragenus, etc.) is
    somewhat arbitrary, although a standardized system is the goal of the ICZN.
    For our purposes, we have taxons with very well-accepted ranks. Unranked
    taxons are currently not supported (note that ranks are often used for
    sorting, so you would need at least some autogenerated rank based on the
    Taxon tree).
    '''
    
    # The ranks are numbered so that negative ones are part of a binomial name,
    # whereas positive ones are larger groupings.

    MAIN_RANKS = (
        (-1.0, 'species'), # S
        (0.0, 'genus'),    # P
        (1.0, 'family'),   # L
        (2.0, 'order'),    # E
    )
    # generate the super-, sub-, and infra-, ranks
    RANK_CHOICES = ()
    for rank in MAIN_RANKS:
        RANK_CHOICES += (
            (rank[0] - 0.4, 'infra' + rank[1]),  # s
            (rank[0] - 0.2, 'sub' + rank[1]),    # p
            rank,                                # l
            (rank[0] + 0.4, 'super' + rank[1]),  # e
        )
    
    name = models.CharField(
        max_length= 255,
        help_text= 'The scientific name for this taxon (i.e. the one in Latin).',
        verbose_name= 'scientific name',
    )
    common_name = models.CharField(
        max_length = 255,
        blank= True,
        help_text= "a comma-delimited list of common English name(s) for " + 
                   'this taxon (e.g. "humpback whale" or "dolphins, ' +
                   'porpises").',
    )
    supertaxon = models.ForeignKey(
        'self',
        null= True,
        blank= True,
        related_name='subtaxons',
        help_text="The smallest taxon that contains this one",
    )
    rank = models.FloatField(choices=RANK_CHOICES)
    
    def _is_binomial(self):
        if not self.rank is None:
            return self.rank < 0
        # go up ancestors until a ranked one is found, if it's 0 or below, this
        # is a binomial taxon
        t = self
        while not t.rank:
            if not t.supertaxon:
                return False
            t = t.supertaxon
        if t.rank <= 0:
            return True
    
    class Meta:
        ordering = ['name']
        #order_with_respect_to = 'supertaxon'
        verbose_name = 'taxon'
        verbose_name_plural = 'taxa'
        
    def __unicode__(self):
        if self._is_binomial():
            # go up the taxon tree looking for a taxon with rank 0. if we find
            # one, print out it's initial, plus the names of each taxon we found
            # on the way.
            nomens = self.name
            t = self.supertaxon
            while t.rank < 0:
                nomens = t.name + ' ' + nomens
                if not t.supertaxon:
                    break
                t = t.supertaxon
            if t.rank == 0:
                return u'%s. %s' % (t.name[0], nomens)
        return u'%s %s' % (self.name, self.get_rank_display())

class Animal(models.Model):
    name = models.CharField(
        max_length= 255,
        help_text= 'The name given to this particular animal (e.g. "Kingfisher"). Not an ID number.'
    )
    
    def _get_probable_gender(self):
        return probable_gender(self.observation_set)
    probable_gender = property(_get_probable_gender)
    determined_gender = models.CharField(
        max_length= 1,
        blank= True,
        choices= GENDERS,
        help_text= 'as determined from the genders indicated in specific events',
    )
    
    def _get_probable_taxon(self):
        return probable_taxon(self.observation_set)
    probable_taxon = property(_get_probable_taxon)
    determined_taxon = models.ForeignKey(
        Taxon,
        blank= True,
        null= True,
        help_text= 'as determined from the taxa indicated in specific events',
    )
    
    def __unicode__(self):
        if self.name:
            return self.name
        return "animal %s" % self.pk
    
    @models.permalink
    def get_absolute_url(self):
        return ('animal_detail', [str(self.id)]) 

class Observation(models.Model):
    '''\
    An observation is a source of data for an Animal. It has an observer and
    and date/time and details of how the observations were taken. Note that the
    observer data may be scanty if this isn't a firsthand report.
    '''

    observer = models.ForeignKey(
        Contact,
        blank= True,
        null= True,
        related_name= 'observed',
    )
    observer_vessel = models.ForeignKey(
        VesselInfo,
        blank= True,
        null= True,
        unique= True,
        related_name= 'observed',
        help_text= 'the vessel the observer was on, if any',
    )
    observation_datetime = models.ForeignKey(
        DateTime,
        unique = True,
        help_text= 'the start of the observation',
    )
    # TODO duration?
    location = models.ForeignKey(
        Location,
        blank= True,
        null= True,
        related_name= "observed_here",
    )

    def _is_firsthand(self):
        return self.reporter == self.observer
    firsthand = property(_is_firsthand)
    reporter = models.ForeignKey(
        Contact,
        blank= True,
        null= True,
        related_name= 'reported',
        help_text= '''\
            Same as observer if this is a firsthand report. If not, this is who
        informed us of the incidents.
        ''',
    )
    report_datetime = models.ForeignKey(
        DateTime,
        blank= True,
        null= True,
        unique = True,
        help_text = 'when we first heard about the observation',
    )
    
    taxon = models.ForeignKey(
        Taxon,
        blank= True,
        null= True,
        help_text= 'The most specific taxon that can be applied to this ' +
            'animal. (e.g. a species)',
    )

    gender = models.CharField(
        max_length= 1,
        choices= GENDERS,
        blank= True,
        help_text= 'The gender of this animal, if known.'
    )
    
    animal = models.ForeignKey(Animal)
    
    animal_description = models.TextField(
        blank= True,
        help_text= """\
        Please note anything that would help identify the individual animal or
        it's species or gender, etc. Even if you've determined those already,
        please indicate what that was on the basis of.
        """
    )
    
    def __unicode__(self):
        ret = "visit"
        if self.date:
            ret += " on %s" % self.date
        if self.observer:
            ret += " by %s" % self.observer
        ret += " (%d)" % self.id
        return ret
    
    class Meta:
        ordering = ['date', 'time', 'id']

