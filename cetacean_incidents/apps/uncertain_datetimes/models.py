import re
from calendar import month_name, isleap
import datetime

from django.db import models

MAXMONTH = len(month_name) - 1 # month_name[0] is blank

def month_days(year=None):
    feb_days = 29 if year is None or isleap(year) else 28
    #             jan feb       mar apr may jun jul aug sep oct nov dec
    return (None, 31, feb_days, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)

class UncertainDateTime(object):
    """Class similiar to a python datetime, except the individual fields can be
    None (to indicate 'unknown')"""
    
    def __init__(self, year=None, month=None, day=None, hour=None, minute=None, second=None, microsecond=None):

        if not year is None:
            if not isinstance(year, int):
                raise TypeError("year must be an integer or None, not a %s" % type(year))
            # sortkey() assumes a four-character year
            if not year > -1000:
                raise ValueError("year must be greater than -1000")
            if not year < 10000:
                raise ValueError("year must be less than 10000")
            # don't allow years that aren't useable in python datetimes
            if not year >= datetime.MINYEAR:
                raise ValueError("year must be greater than %d" % datetime.MINYEAR)
            if not year <= datetime.MAXYEAR:
                raise ValueError("year must be less than %d" % datetime.MAXYEAR)
        self.year = year

        if not month is None:
            if not isinstance(month, int):
                raise TypeError("month must be an integer or None, not a %s" % type(month))
            if not month >= 1:
                raise ValueError("month must be greater than or equal to 1")
            if not month <= MAXMONTH:
                raise ValueError("month must be less than or equal to %d" % MAXMONTH)
        self.month = month

        if not day is None:
            if not isinstance(day, int):
                raise TypeError("day must be an integer or None, not a %s" % type(day))
            if not day >= 1:
                raise ValueError("day must be greater than or equal to 1")
            if not month is None:
                month_days(year)[month]
                if not day <= max_day:
                    raise ValueError("day must be less than or equal to %d when month is %d" % (max_day, month))
            else:
                max_day = 31
                if not day <= max_day:
                    raise ValueError("day must be less than or equal to %d when month is None" % max_day)
        self.day = day

        if not hour is None:
            if not isinstance(hour, int):
                raise TypeError("hour must be an integer or None, not a %s" % type(hour))
            if not hour >= 0:
                raise ValueError('hour must be greater than or equal to 0')
            if not hour < 24:
                raise ValueError('hour must be less than 24')
        self.hour = hour

        if not minute is None:
            if not isinstance(minute, int):
                raise TypeError("minute must be an integer or None, not a %s" % type(minute))
            if not minute >= 0:
                raise ValueError('minute must be greater than or equal to 0')
            if not minute < 60:
                raise ValueError('minute must be less than 60')
        self.minute = minute

        if not second is None:
            if not isinstance(second, int):
                raise TypeError("second must be an integer or None, not a %s" % type(second))
            if not second >= 0:
                raise ValueError('second must be greater than or equal to 0')
            # not bothering with leap-seconds
            if not second < 60:
                raise ValueError('second must be less than 60')
        self.second = second

        if not microsecond is None:
            if not isinstance(microsecond, int):
                raise TypeError("microsecond must be an integer or None, not a %s" % type(year))
            if not microsecond >= 0:
                raise ValueError('microsecond must be greater than or equal to 0')
            if not microsecond < 10 ** 6 :
                raise ValueError('microsecond must be less than %d' % 10 ** 6)
        self.microsecond = microsecond
    
    SORTKEY_MAX_LEN = len('YYYYMMDDHHMMSSuSSSSS')
    SORTS_BEFORE_DIGITS = ' '
    SORTS_AFTER_DIGITS = 'z'

    def sortkey(self, unknown_is_later=False):
        '''\
        If unknown_is_later is True, the sortkeys returned will sort unknown
        elements of the date _after_ dates where they're known (that are other 
        wise identical). For example: 2004-03-?? 08:??:?? will sort _after_
        2004-03-20 08:??:?? but _before_ 2004-03-20 09:??:?? .
        '''
        
        parts = []
        for fieldname, width in (
            (       'year', 4),
            (      'month', 2),
            (        'day', 2),
            (       'hour', 2),
            (     'minute', 2),
            (     'second', 2),
            ('microsecond', 6),
        ):
            val = getattr(self, fieldname)
            if val is None:
                if unknown_is_later:
                    parts.append(self.SORTS_AFTER_DIGITS * width) 
                else:
                    parts.append(self.SORTS_BEFORE_DIGITS * width) 
            else:
                parts.append(('%0' + str(width) + 'd') % val)
        
        return ''.join(parts)
    
    @classmethod
    def from_sortkey(cls, key):
        '''\
        Constructs a new UncertainDateTime from a return value of another 
        UncertainDateTime's sortkey() method.
        '''

        if not isinstance(key, basestring):
            raise TypeError(
                "key passed to sortkey must be a string or unicode, not %s" 
                % type(key)
            )
        
        match = re.search(r'(.{4})(.{2})(.{2})(.{2})(.{2})(.{2})(.{6})', key)
        if not match:
            raise ValueError("key passed wasn't formatted correctly: %s" % key)
        args = match.groups()

        blank_re = re.compile(r'^[' + cls.SORTS_BEFORE_DIGITS + cls.SORTS_AFTER_DIGITS + ']+$')
        def string_converter(val):
            if blank_re.search(val):
                return None
            return int(val)
        args = map(string_converter, args)
        
        return cls(*args)
    
    @property
    def earliest(self):
        '''\
        Returns a python datetime that's the earliest possible point in this
        UncertainDateTime.
        '''
        
        (year, month, day, hour, minute, second, microsecond) = (self.year, self.month, self.day,  self.hour, self.minute, self.second, self.microsecond)
        if year is None:
            year = datetime.MINYEAR
        if month is None:
            month = 1
        if day is None:
            day = 1
        if hour is None:
            hour = 0
        if minute is None:
            minute = 0
        if second is None:
            second = 0
        if microsecond is None:
            microsecond = 0
        
        return datetime.datetime(year, month, day, hour, minute, second, microsecond)
    
    @property
    def latest(self):
        '''\
        Returns a python datetime that's the latest possible point in this
        UncertainDateTime.
        '''
        
        (year, month, day, hour, minute, second, microsecond) = (self.year, self.month, self.day, self.hour, self.minute, self.second, self.microsecond)
        if year is None:
            year = datetime.MAXYEAR
        if month is None:
            month = MAXMONTH
        if day is None:
            day = month_days(year)[month]
        if hour is None:
            hour = 24 - 1
        if minute is None:
            minute = 60 - 1
        if second is None:
            second = 60 - 1 # not bothering with leap-seconds
        if microsecond is None:
            microsecond = 1000000 - 1
        
        result = datetime.datetime(year, month, day, hour, minute, second, microsecond)
        
        # we actually want the point at the _end_ of the range, so add one
        # microsecond to the result of the above maxing-out of each field.
        if result < datetime.datetime.max:
            result += datetime.timedelta(microseconds=1)
        
        return result

class UncertainDateTimeField(models.Field):
    
    description = """a DateTime whose individual fields (year, month, day, etc)
    may be unknown"""
    
    __metaclass__ = models.SubfieldBase
    
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = UncertainDateTime.SORTKEY_MAX_LEN
        super(UncertainDateTimeField, self).__init__(*args, **kwargs)
    
    def to_python(self, value):
        if value is None:
            return None
        
        if isinstance(value, UncertainDateTime):
            return value
        
        return UncertainDateTime.from_sortkey(value)
        
    def get_prep_value(self, value):
        
        if value is None:
            return None
        
        return value.sortkey()

    # django lookup types:
    # exact, iexact, contains, icontains, gt, gte, lt, lte, in, startswith,
    # istartswith, endswith, iendswith, range, year, month, day, isnull, search,
    # regex, iregex
    def get_prep_lookup(self, lookup_type, value):
        if lookup_type == 'exact':
            return self.get_prep_value(value)
        elif lookup_type == 'in':
            return [self.get_prep_value(v) for v in value]
        else:
            raise TypeError('Lookup type %r not supported.' % lookup_type)

    def get_internal_type(self):
        return 'CharField'
        
    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_db_prep_value(value)

class DateTime(models.Model):
    '''Model to handle the various uncertainties in dates and times.'''

    year = models.IntegerField(
        help_text="Year is the one required field, because without it there's no point in recording the rest."
    )
    months = [(i, month_name[i])for i in range(1,len(month_name))]
    month = models.IntegerField(
        choices= months,
        blank= True,
        null= True,
    )
    day = models.IntegerField(
        blank= True,
        null= True,
    )
    
    hour = models.IntegerField(
        choices = [(i, i) for i in range(0,24)],
        blank= True,
        null= True,
        help_text= "midnight is 0, 1pm is 13, etc. Note that all datetimes are TAI (i.e. timezoneless). It's up to the editing and display interface to convert accordingly.",
    )
    minute = models.IntegerField(
        blank= True,
        null= True,
    )
    second = models.FloatField(
        blank= True,
        null= True,
    )
    
    import_notes = models.TextField(
        blank= True,
        editable= False, # note that this only means it's not editable in the admin interface or ModelForm-generated forms
        help_text= "field to be filled in by import scripts for data they can't assign to a particular field",
    )
    
    def clean(self):
        # TODO is individual field validation OK here?
        # hour
        if not self.hour is None:
            if self.hour < 0:
                raise ValidationError('no negative hours')
            if self.hour > 23:
                raise ValidationError('hours should be less than 24')
        # minute
        if not self.minute is None:
            if self.minute < 0:
                raise ValidationError('no negative minutes')
            if self.minute > 59:
                raise ValidationError('minutes should be less than 60')
        # second
        if not self.second is None:
            if self.second < 0:
                raise ValidationError('no negative seconds')
            # FYI python datetime doesn't like leap-seconds
            if self.second == 60:
                raise ValidationError('no leap-seconds')
            if self.second > 60:
                raise ValidationError('seconds should be less than 60')
    
    @property
    def earliest(self):
        '''\
        Returns a python datetime that's the earliest point in this potentially 
        vauge DateTime.
        '''
        
        (year, month, day, hour, minute, second) = (self.year, self.month, self.day,  self.hour, self.minute, self.second)
        if month is None:
            month = 1
        if day is None:
            day = 1
        if hour is None:
            hour = 0
        if minute is None:
            minute = 0
        if second is None:
            second = 0
            usecond = 0
        else:
            usecond = math.fmod(second, 1)
            second = math.floor(second)
        
        return datetime.datetime(year, month, day, hour, minute, second, usecond, pytz.utc)
    
    @property
    def latest(self):
        '''\
        Returns a python datetime that's the latest point in this potentially 
        vauge DateTime.
        '''
        
        #                   jan feb   mar apr may jun jul aug sep oct nov dec
        MONTH_DAYS = (None, 31, None, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
        
        (year, month, day, hour, minute, second) = (self.year, self.month, self.day, self.hour, self.minute, self.second)
        if month is None:
            month = 12
        if day is None:
            if month == 2:
                if isleap(year):
                    day = 29
                else:
                    day = 28
            else:
                day = MONTH_DAYS[month]
        if hour is None:
            hour = 24 - 1
        if minute is None:
            minute = 60 - 1
        if second is None:
            second = 60 - 1 # not bothering with leap-seconds
            usecond = 1000000 - 1
        else:
            usecond = math.fmod(second, 1)
            second = math.floor(second)
        
        result = datetime.datetime(year, month, day, hour, minute, second, usecond, pytz.utc)
        
        # we actually want the point at the _end_ of the range, so add one
        # microsecond to the result of the above maxing-out of each field
        result += datetime.timedelta(microseconds=1)
        
        return result

    @property
    def breadth(self):
        '''\
        The length of time that this DateTime might refer to.
        '''
        
        return self.latest - self.earliest
    
    # note that giving only a year and a hour is OK, so you can indicate
    # time-of-day without knowing what day it was exactly
    def __unicode__(self):
        ret = u"%04d" % self.year
        if not self.month is None:
            ret += u"-%02d" % self.month
            if not self.day is None:
                ret += u"-%02d" % self.day
        if not self.hour is None:
            ret += u" %02dh" % self.hour
            if not self.minute is None:
                ret += u" %02dm" % self.minute
                if not self.second is None:
                    ret += u" %02ds" % self.second
        return ret
    
    class Meta:
        ordering = ('year', 'month', 'day', 'hour', 'minute', 'second')
        
