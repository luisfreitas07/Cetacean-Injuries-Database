# -*- encoding: utf-8 -*-

from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import models

from cetacean_incidents.apps.taxons.utils import probable_taxon

from cetacean_incidents.apps.documents.models import Documentable

from cetacean_incidents.apps.uncertain_datetimes.models import UncertainDateTimeField

from ..utils import probable_gender

from animal import Animal

class CaseManager(models.Manager):
    def same_timeframe(self, case):
        '''\
        Returns cases that _may_ have been happening at the same time as the one
        given. Takes into account the potential vagueness of observation dates.
        '''
        
        # TODO avoid circular imports more elegantly?
        from observation import Observation
        
        # collect all the observation dates
        obs_dates = map(lambda o: o.datetime_observed, Observation.objects.filter(case=case))
        sametime_q = models.Q()
        for date in obs_dates:
            sametime_q |= UncertainDateTimeField.get_sametime_q(date, 'observation__datetime_observed')
        
        return Case.objects.filter(sametime_q)
        
    def associated_cases(self, case):
        '''\
        Given a case, return a list of _other_ cases that may be relevant to it.
        This includes cases in the same timeframe that are either for the same
        animal or have nearby coordinates.
        '''
        
        # TODO nearby coords
        
        result = self.same_timeframe(case).filter(animal=case.animal).exclude(id=case.id)
        
        # oracle workaround
        result = set(result)
        
        return result

# TODO there's probably a way to get a list of all the subclasses,
# but for now we'll just collected them ourselves.
class CaseMeta(models.Model.__metaclass__):
    
    case_class = None
    
    # TODO should probably do a check if the passed classdef has this as a 
    # metaclass, to handle all the various inheritance edge cases this doesn't.
    # For now though, our inheritance DAG is just a 2-level tree with Case as
    # the root...
    def __new__(self, name, bases, dict):
    
        if self.case_class is None and name == 'Case':
            the_class = super(CaseMeta, self).__new__(self, name, bases, dict)
            self.case_class = the_class
            self.case_class.detailed_classes = {name: the_class}

        elif self.case_class in bases:
            # modify the save method to set the case_type field

            if 'save' in dict.keys():
                def save_wrapper(old_save):
                    def new_save(inst, *args, **kwargs):
                        isnt.case_type = name
                        return old_save(inst, *args, **kwargs)
                    return new_save
                dict['save'] = save_wrapper(dict['save'])
            else:
                def new_save(inst, *args, **kwargs):
                    inst.case_type = name
                    return self.case_class.save(inst, *args, **kwargs)
                dict['save'] = new_save

            the_class = super(CaseMeta, self).__new__(self, name, bases, dict)
            self.case_class.detailed_classes[name] = the_class

        return the_class

class SeriousInjuryAndMortality(models.Model):
    '''\
    Abstract class to collect together all the Serious Injury and Mortality
    fields.
    '''
    
    ## serious injury and mortality determination ##
    si_n_m_fieldnames = []

    review_1_date = models.DateField(
        blank= True,
        null= True,
        verbose_name = "1st reviewer date",
    )
    si_n_m_fieldnames.append('review_1_date')

    review_1_inits = models.CharField(
        max_length= 5,
        blank= True,
        null= True,
        verbose_name = "1st reviewer initials",
    )
    si_n_m_fieldnames.append('review_1_inits')

    review_2_date = models.DateField(
        blank= True,
        null= True,
        verbose_name = "2nd reviewer date",
    )
    si_n_m_fieldnames.append('review_2_date')

    review_2_inits = models.CharField(
        max_length= 5,
        blank= True,

        null= True,
        verbose_name = "2nd reviewer initials",
    )
    si_n_m_fieldnames.append('review_2_inits')

    case_confirm_criteria = models.IntegerField(
        blank= True,
        null= True,
        verbose_name = "criteria for case confirmation",
        help_text= "a number in one of the ranges 11-14, 21-24, or 31-34",
    )
    si_n_m_fieldnames.append('case_confirm_criteria')

    animal_fate = models.CharField(
        max_length= 2,
        choices = (
            ('mt', 'mortality'),
            ('si', 'serious injury'),
            ('ns', 'non-serious injury'),
            ('no', 'no injury from human interaction'),
            ('un', 'unknown'),
        ),
        default= 'un',
        blank= True,
    )
    si_n_m_fieldnames.append('animal_fate')
    
    fate_cause = models.CharField(
        max_length= 1,
        choices = (
            ('y', 'yes'),
            ('m', 'can\'t be ruled out'),
            ('n', 'no'),
            ('-', 'not applicable'),
        ),
        default= '-',
        blank= True,
        help_text= "Did the injury this case is concerned with lead to the animal's fate above? If the fate was 'no injury' or 'unknown' this should be 'not applicable'",
    )
    si_n_m_fieldnames.append('fate_cause')
    
    fate_cause_indications = models.IntegerField(
        blank= True,
        null= True,
        verbose_name= "indications of fate cause",
        help_text= "a number in one of the ranges 41-44, 51-54, or 61-66",
    )
    si_n_m_fieldnames.append('fate_cause_indications')

    si_prevented = models.NullBooleanField(
        blank= True,
        null= True,
        verbose_name = "serious injury warranted if no intervention?",
    )
    si_n_m_fieldnames.append('si_prevented')

    included_in_sar = models.NullBooleanField(
        blank= True,
        null= True,
        verbose_name = "included in SAR?"
    )
    si_n_m_fieldnames.append('included_in_sar')

    review_1_notes = models.TextField(
        blank= True,
        null= True,
        verbose_name = "1st reviewer notes",
    )
    si_n_m_fieldnames.append('review_1_notes')

    review_2_notes = models.TextField(
        blank= True,
        null= True,
        verbose_name = "2st reviewer notes",
    )
    si_n_m_fieldnames.append('review_2_notes')

    @property
    def si_n_m_info(self):
        def is_default(fieldname):
            value = getattr(self, fieldname)
            # first check if there's a default value
            default = self._meta.get_field(fieldname).default
            if default != models.fields.NOT_PROVIDED:
                if value == default:
                    return True
                return False
            
            # just consider None or the empty string to be the default otherwise
            if value is None:
                return True
            
            if value == '':
                return True
            
            return False
                
        return reduce(lambda so_far, fieldname: so_far or not is_default(fieldname), self.si_n_m_fieldnames, False)

    class Meta:
        abstract = True

class Case(Documentable, SeriousInjuryAndMortality):
    '''\
    A Case is has all the data for _one_ incident of _one_ animal (i.e. a single strike of a ship, a single entanglement of an animal in a particular set of gear). Hypothetically the incident has a single datetime and place that it occurs, although that's almost never actually known. Cases keep much of their information in the form of a list of observations. They also serve to connect individual observations to animal entries.
    '''
    
    __metaclass__ = CaseMeta
    
    # TODO move this to Entanglement
    nmfs_id = models.CharField(
        max_length= 255,
        unique= False, # in case a NMFS case corresponds to multiple cases in
                       # our database
        blank= True,
        verbose_name= "NMFS entanglement case number",
    )
    
    animal = models.ForeignKey(
        Animal,
    )
    
    valid = models.IntegerField(
        choices= (
            (0, 'invalid'),
            (1, 'suspected'),
            (2, 'confirmed'),
        ),
        default= 1,
        verbose_name= 'Validity',
        help_text= "Invalid cases don't count towards year-totals."
    )
    
    happened_after = models.DateField(
        blank= True,
        null= True,
        help_text= "Please use '<year>-<month>-<day>'. Injuring incidents themselves are rarely observed, so this is a day whose start is definitely _before_ the incident. For entanglements, this is the 'last seen unentangled' date. For shipstrikes this would usually be the date of the last observation without the relevant scar or wound. In those cases were the date of the incident is known, put it here. (You should also add an observation for that day to indicate the actual incident was observed.) For uncertain dates, put a date at the begining of the range of possible ones, i.e. if you know the animal was seen uninjured in July of 2009, put '2009-07-01'.",
        verbose_name= 'incident was on or after',
    )
    
    ole_investigation = models.NullBooleanField(
        blank= True,
        null= True,
        default= False,
        verbose_name= "OLE Investigation",
        help_text= "Is there a corresponding Office of Law Enforcement investigation?",
    )
    
    # this should always be the YearCaseNumber with case matching self.id and
    # year matching self.date.year . But, it's here so we can order by it in
    # the database.
    current_yearnumber = models.ForeignKey(
        'YearCaseNumber',
        editable=False,
        null=True,
        related_name='current',
    )
    
    @property
    def yearly_number(self):
        "A number that's unique within cases whose case-dates have the same year. Note that this number can't be assigned until the case-date is defined, which doesn't happen until the a Observation is associated with it."
        if self.current_yearnumber:
            return self.current_yearnumber.number
        else:
            return None
    
    names = models.TextField(
        blank= False,
        editable= False,
        help_text= "Comma-separated list of autogenerated names with the format \"<year>#<case # in year> (<date>) <type> of <taxon>\", where <year> and <date> are determined by the earliest datetime_observed of it's observations, <type> is 'Entanglement' for all entanglements, and <taxon> is the most general one that includes all the ones mentioned in observations. Note that a case may have multiple names because many of these elements could change as observations are added or updated, however each Case name should always refer to a specific case.",
    )
    
    def _get_names_list(self):
        return filter(lambda x: x != '', self.names.split(','))
    def _put_names_iter(self, new_names):
        # TODO should the names-set be the union of the one passed and the
        # current one? This makes sense because once assigned, names should
        # never be removed. But, do we want to enforce that at this level?
        self.names = ','.join(new_names)
    names_list = property(_get_names_list,_put_names_iter)

    def _get_names_set(self):
        return frozenset(self._get_names_list())
    names_set = property(_get_names_set,_put_names_iter)

    def current_name(self):
        
        # TODO more elegant way to avoid circular imports?
        from observation import Observation
        self = self.detailed_queryset().select_related('current_yearnumber')[0]
        obs = Observation.objects.filter(case__id=self.id)
        # Cases with no obs yet don't get names
        if not obs.exists():
            return None

        date = self.date(obs)
        s = {}
        
        # if there's a NMFS ID use that
        if self.nmfs_id:
            s['id'] = self.nmfs_id
        else:
        # otherwise use our YearCaseNumber IDs
            s['year'] = unicode(self.current_yearnumber.year)
            s['yearly_number'] = self.current_yearnumber.number
            if self.yearly_number is None:
                s['yearly_number'] = -1
            
            s['id'] = "%(year)s#%(yearly_number)d" % s
        
        # trim off anything beyond a day
        s['date'] = "%04d" % date.year
        if date.month:
            s['date'] += '-%02d' % date.month
            if date.day:
                s['date'] += '-%02d' % date.day
        taxon = probable_taxon(obs)
        if not taxon is None:
            s['taxon'] = taxon.scientific_name()
        else:
            s['taxon'] = u'Unknown taxon'
        s['type'] = self._meta.verbose_name.capitalize()
        name = u"%(id)s (%(date)s) %(type)s of %(taxon)s" % s

        # append the current_name to the names list, if necessary
        if not name in self.names_set:
            self.names_list.append(name)
            self.save()
        
        return name
    
    def past_names_set(self):
        return self.names_set - set([self.current_name()])
    
    def past_names_list(self):
        return filter(lambda name: name != self.current_name(), self.names_list)

    def date(self, obs=None):
        '''\
        obs is a queryset of observations. it defaults to this case's
        observations.
        '''
        if obs is None:
            obs = self.observation_set

        if not obs.exists():
            return None
        return obs.order_by('datetime_observed')[0].datetime_observed
    
    def earliest_datetime(self):
        if not self.observation_set.exists():
            return None
        return min([o.earliest_datetime for o in self.observation_set.all()])

    def latest_datetime(self):
        '''\
        The latest that one of this case's observations _may_ have _started.
        '''
        if not self.observation_set.exists():
            return None
        return max([o.latest_datetime for o in self.observation_set.all()])
    
    def breadth(self):
        if not self.observation_set.exists():
            return None
        return self.latest_datetime() - self.earliest_datetime()
    
    def associated_cases(self):
        return Case.objects.associated_cases(self)
    
    def clean(self):
        if not self.nmfs_id is None and self.nmfs_id != '':
            # TODO do they have to be unique or not?
            # check that an existing case doesn't already have this nmfs_id
            cases = Case.objects.filter(nmfs_id=self.nmfs_id)
            if self.id:
                cases = cases.exclude(id=self.id)
            if cases.count() > 0:
                raise ValidationError("NMFS ID '%s' is already in use by case '%s'" % (self.nmfs_id, unicode(cases[0])))
        
        date = self.date()
        if date:
            def _next_number_in_year(year):
                this_year = YearCaseNumber.objects.filter(year=year)
                if this_year.count():
                    return this_year.order_by('-number')[0].number + 1
                else:
                    return 1
            def _new_yearcasenumber():
                year = date.year
                return YearCaseNumber.objects.create(
                    case=self,
                    year=year,
                    number= _next_number_in_year(year),
                )
        
            # do we have a newly assigned date and no yearly-number?
            if self.current_yearnumber:
                # is our current year different from the one in our current
                # yearly_number assignment
                if date.year != self.current_yearnumber.year:
                    try:
                        # do we have a previous assignment for our current year?
                        new_year_case_number = YearCaseNumber.objects.get(case=self, year=date.year)
                    except YearCaseNumber.DoesNotExist:
                        # add a new entry for this year-case combo
                        new_year_case_number = _new_yearcasenumber()
                    self.current_yearnumber = new_year_case_number
            else:
                # assign a new number
                self.current_yearnumber = _new_yearcasenumber()
    
    def detailed_queryset(self):
        '''\
        Returns a Case-subclass queryset that contains only the case returned by
        detailed().
        '''
        return self.detailed_classes[self.case_type].objects.filter(id=self.id)
    
    @property
    def detailed(self):
        '''Get the more specific instance of this Case, if any.'''
        if self.case_type == 'Case':
            return self
        return self.detailed_classes[self.case_type].objects.get(id=self.id)

    @property
    def detailed_class_name(self):
        return self.case_type

    case_type = models.CharField(
        max_length= 512,
        default= 'Case',
        editable= False,
        null= False,
        help_text= "A required field to be filled in by subclasses. Avoids using a database lookup just to determine the type of a case"
    )
    
    def probable_taxon(self):
        return probable_taxon(self.observation_set)
    
    def probable_gender(self):
        return probable_gender(self.observation_set)
    
    def __unicode__(self):
        current_name = self.current_name()
        if current_name is None:
            self = self.detailed
            if self.id:
                return u"%s #%06d" % (self._meta.verbose_name.capitalize(), self.id)
            else:
                return u"<new %s>" % (self._meta.verbose_name,)
        return current_name

    @models.permalink
    def get_absolute_url(self):
        return ('case_detail', [str(self.id)]) 
    
    def get_edit_url(self):
        return reverse('edit_case', args=[self.id])

    objects = CaseManager()

    class Meta:
        app_label = 'incidents'
        ordering = ('current_yearnumber__year', 'current_yearnumber__number', 'id')

class YearCaseNumber(models.Model):
    '''\
    A little table to do the bookkeeping when assigning yearly-numbers to cases.
    'year' is a year, 'case' is a case, 'number' is any yearly_number held by
    that case for that year, including it's current one.
    
    Assigning unique numbers to each case in a year is complicated; once a
    case-number in a given year has been assigned to a case, it mustn't ever be
    assigned to a different one, even if that case is changed to a different
    year or merged with another case. Ideally, if a case was assigned, say,
    2003#67 and then it's date was changed to 2004, it would be assigned the
    next unused yearly_number for 2004. If it was then changed back to 2003, it
    would be assigned #67 again. Thus, this table stores all past and current
    year-case-yearly_number combinations.
    '''
    
    year = models.IntegerField(db_index= True)
    case = models.ForeignKey(Case)
    number = models.IntegerField(db_index= True)
    
    def __unicode__(self):
        return "%04d #%03d <%s>" % (
            self.year,
            self.number,
            unicode(self.case),
        )
    
    class Meta:
        app_label = 'incidents'
        ordering = ('year', 'number')

