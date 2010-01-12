import operator

from django.db import models
from cetacean_incidents.apps.people.models import Person, Organization
from cetacean_incidents.apps.vessels.models import Vessel
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
    For our purposes, we have taxons with very well-accepted ranks (basically
    just genus and species).
    '''
    
    MAIN_RANKS = (
        ('O', 'order'),
        ('F', 'family'),
        ('G', 'genus'),
        ('S', 'species'),
    )
    # generate the super-, sub-, and infra-, ranks
    # note that this function takes a pair and returns a 4-tuple of pairs
    _expand = lambda r : (
        ('u' + r[0], 'super' + r[1]),
        r,
        ('b' + r[0], 'sub'   + r[1]),
        ('i' + r[0], 'infra' + r[1]),
    )
    ALL_RANKS = map(_expand, MAIN_RANKS)
    # ALL_RANKS is now a list of 4-tuples of pairs
    ALL_RANKS = reduce( lambda t1, t2: t1 + t2, ALL_RANKS )
    # ALL_RANKS is now a list of pairs
    ALL_RANKS = tuple(ALL_RANKS)
    
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
    rank = models.CharField(max_length=2, choices= ALL_RANKS)
    
    class Meta:
        ordering = ['name']
        #order_with_respect_to = 'supertaxon'
        verbose_name = 'taxon'
        verbose_name_plural = 'taxa'
        
    def __unicode__(self):
        if self.rank == 'S':
            genus = self
            while genus.rank != 'G' and genus.supertaxon is not None:
                genus = genus.supertaxon
            if genus.rank == 'G':
                return u'%s. %s' % (genus.name[0], self.name)
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

class Tag(models.Model):

    platform_id = models.CharField(
        max_length= 255,
        blank= True,
    )
    serial_id = models.CharField(
        max_length= 255,
        blank= True,
    )
    model_id = models.CharField(
        max_length= 255,
        blank= True,
    )
    tag_type = models.CharField(
        max_length= 255,
        blank= True,
    )
    color = models.CharField(
        max_length= 255,
        blank= True,
    )
    gps = models.BooleanField()
    vhf_frequency = models.FloatField(
        blank= True,
        null= True,
        help_text= "leave blank if not a VHF tag",
    )

    tagging_person = models.ForeignKey(Person, blank=True, null=True)
    tagging_org = models.ForeignKey(Organization, blank=True, null=True)
    built_date = models.DateField(blank=True)
    refurbished_date = models.DateField(blank=True)
    tagging_date = models.DateField(blank=True)
    tagging_location = models.ForeignKey(
        Location,
        blank= True,
        null= True,
    )
    expiration_date = models.DateField(blank=True)

    placement = models.CharField(
        max_length= 2,
        choices =  (
            ('D', 'dorsal'),
            ('DF', 'dorsal fin'),
            ('L', 'lateral body'),
            ('LF', 'left front'),
            ('LR', 'left rear'),
            ('RF', 'right front'),
            ('RR', 'right rear'),
        ),
        blank= True,
    )
    
    comments = models.TextField(blank=True)
    
    def __unicode__(self):
        if self.id_number:
            return unicode(self.id_number)
        parts = []
        desc = ''
        if self.pk:
            parts.append(unicode(self.pk))
        if self.color:
            parts.append(unicode(self.color))
        if self.placement:
            parts.append(self.get_placement_display())
        if self.type:
            parts.append(unicode(self.type))
        return u' '.join(parts + [u'tag'])

class TagObservation(models.Model):
    tag = models.ForeignKey(Tag)
    observation = models.ForeignKey('Observation')
    added = models.BooleanField(
        verbose_name= 'was it added during this observation?',
    )

class Observation(models.Model):
    '''\
    An observation is a source of data for an Animal. It has an observer and
    and date/time and details of how the observations were taken. Note that the
    observer data may be scanty if this isn't a firsthand report.
    '''

    observer = models.ForeignKey(
        Person,
        blank= True,
        null= True,
        related_name= 'observed',
    )
    vessel = models.ForeignKey(
        Vessel,
        blank= True,
        null= True,
        related_name= 'observed',
        help_text= 'the vessel the observer was on',
    )
    observer_comments = models.TextField(
        blank= True,
        help_text= 'any additional observations about the animal or '
                   + 'clarifications of the other fields'
    )
    date = models.DateField(
        blank= True,
        null= True,
        help_text= 'the date that the observation took place',
    )
    time = models.TimeField(
        blank= True,
        null= True,
        help_text= 'the time of the beginning of the observation',
    )
    # TODO separate begin and end times?

    def _is_firsthand(self):
        return self.reporter == self.observer
    firsthand = property(_is_firsthand)
    reporter = models.ForeignKey(
        Person,
        blank= True,
        null= True,
        help_text= '''\
            Same as observer if this is a firsthand report. If not, this is the
            person who either created this entry in the database, or filled out
            the form that was then imported into the database.
        ''',
    )
    date_reported = models.DateField(
        blank= True,
        null= True,
    )
    time_reported = models.TimeField(
        blank= True,
        null= True,
    )

    # TODO importer fields for the person/program that imported the datat into
    # this database
    
    location = models.ForeignKey(
        Location,
        blank= True,
        null= True,
        related_name= "observed_here",
    )
    
    animal_movement = models.CharField(
        max_length= 255,
        blank= True,
        null= True,
        help_text= "i.e. anchored, stranded, traveling",
    )
    animal_heading = models.CharField(
        max_length= 255,
        blank= True,
        null= True,
        help_text= "i.e. north, southwest, circling, random, unknown",
    )
    
    video_taken = models.NullBooleanField(
        blank= True,
    )
    '''If true, implies media_taken.'''
    photos_taken = models.NullBooleanField(
        blank= True,
    )
    '''If true, implies media_taken.'''
    media_taken = models.BooleanField(
        blank= True,
        verbose_name= "photos or videos taken",
    )
    media_taker = models.CharField(
        max_length = 255,
        blank= True,
        verbose_name= 'photo or video taker',
    )
    media_loc = models.CharField(
        max_length= 1023,
        blank= True,
        verbose_name= "photos or videos disposition",
        help_text= 'leave blank if unknown',
    ) # TODO implies media_taken
    
    animal = models.ForeignKey('Animal')
    taxon = models.ForeignKey(
        Taxon,
        help_text= 'The most specific taxon that can be applied to this ' +
            'animal. (e.g. a species)',
    )
    TAXON_METHODS=(
        ("p", "photo(s)"),
        ("v", "video(s)"),
        ("g", "genetics"),
        ("m", "morphology"),
    )
    taxon_method = models.CharField(
        "How was the species determined?",
        max_length= 1,
        choices= TAXON_METHODS,
        blank= True,
        help_text= 'leave blank if unknown'
    )

    gender = models.CharField(
        max_length= 1,
        choices= GENDERS,
        blank= True,
        help_text= 'The gender of this animal, if known.'
    )
    GENDER_METHODS = (
        ('p', 'physical exam'),
        ('g', 'genetics'),
        ('c', 'presence of calf'),
        ('o', 'visual observation'),
    )
    gender_method = models.CharField(
        "Method for determining gender",
        max_length= '1',
        choices= GENDER_METHODS,
        blank= True,
        help_text= "leave blank if unknown",
    )
    
    age = models.FloatField(
        blank= True,
        null= True,
        help_text="age in years (decimal years allowed)",
    )
    # use ints so they're orderable
    AGE_GROUPS = (
        (1, 'pup / calf'),
        (2, 'yearling'),
        (3, 'subadult'),
        (4, 'adult'),
    )
    age_group = models.SmallIntegerField(
        "Age-group",
        choices= AGE_GROUPS,
        blank= True,
        null= True,
        help_text= "leave blank if unknown",
    )
    AGE_METHODS = (
        ('b', "biopsy"),
        ('o', "visual observation"),
        ('p', "photo(s)"),
        ('v', "video(s)"),
    )
    age_method = models.CharField(
        "Method for determining age",
        max_length= 1,
        choices= AGE_METHODS,
        blank= True,
        help_text= "leave blank if unknown",
    )
    
    length = models.FloatField(
        "Estimated length in meters",
        blank= True,
        null= True,
        help_text= "leave blank if no estimation was made",
    )
    LENGTH_METHODS = (
        ('o', "visual observation"),
        ('p', "photo(s)"),
        ('v', "video(s)"),
    )
    length_method = models.CharField(
        max_length= 1,
        choices = LENGTH_METHODS,
        blank= True,
        help_text= "leave blank if no estimation was made",
    )
    
    weight = models.FloatField(
        "weight in kilograms",
        blank= True,
        null= True,
        help_text= "leave blank if no estimation was made",
    )
    WEIGHT_METHODS = (
        ('o', 'visual observation'),
        ('s', 'a big scale'),
    )
    weight_method = models.CharField(
        max_length= 1,
        choices = WEIGHT_METHODS,
        blank= True,
        help_text= "how was the weight measured, if at all",
    )
    
    animal_description = models.TextField(
        blank= True,
    )
    
    # tag data
    # see django ticket #999 for why this fields can't be 'tags'
    tags_seen = models.ManyToManyField(
        'Tag',
        through='TagObservation',
        blank= True,
        null= True,
    )
    
    def __unicode__(self):
        ret = "visit of %s" % self.animal
        if self.date:
            ret += " on %s" % self.date
        if self.observer:
            ret += " by %s" % self.date
        ret += " (%d)" % self.id
        return ret
    
    class Meta:
        ordering = ['date', 'time', 'animal']
