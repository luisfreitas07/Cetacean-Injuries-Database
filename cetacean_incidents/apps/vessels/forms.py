from django import forms
from django.forms.util import flatatt

from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.conf import settings

from models import VesselInfo
from cetacean_incidents.apps.countries.models import Country
from cetacean_incidents.apps.contacts.models import Contact

class FlagSelect(forms.Select):
    '''\
    Extension of a Select widget that inserts a little flag image for the 
    currently selected country.
    '''
    
    class Media:
        js = (settings.JQUERY_FILE,)
    
    def render(self, name, value, attrs=None, choices=()):
        if value is None:
            value = ''

        # insert a nice bit of javascript to show the flag of the country
        # selected
        # TODO check that attrs['id'] is set?
        output = [ '''\
        <script type="text/javascript">
            jQuery(function(){
                var select = $("#%(id)s > select");
                select.change(function(event){
                    // remove the old flag first
                    $("#%(id)s > img.flag").remove()
                    if ( select.val() == '' )
                        return;
                    var icon_url = "%(media)s" + select.val().toLowerCase()  + ".png";
                    // set the margin to 1/4 the image size
                    $("#%(id)s").prepend("<img style=\\"margin: 4px;\\" class=\\"flag\\" src=\\"" + icon_url + "\\">");
                });
                // trigger the event to load the flag for the initial value.
                select.change();
            });
        </script>
        ''' % {
            'id': attrs ['id'],
            'media': reverse('site-media', kwargs={'path': 'flags/'}),
        }]

        span_attrs = self.build_attrs(attrs)
        select_attrs = self.build_attrs(name=name)
        output.append(u'<span%s><select%s>' % (flatatt(span_attrs), flatatt(select_attrs)))
        options = self.render_options(choices, [value])
        if options:
            output.append(options)
        output.append('</select></span>')
        return mark_safe(u'\n'.join(output))

class FlagField(forms.ModelChoiceField):
    '''\
    A ModelChoiceField that uses FlagSelect as a widget, and Country.objects.all()
    as a default queryset.
    '''
    
    widget = FlagSelect
    
    def __init__(self, queryset=None, *args, **kwargs):
        if queryset is None:
            queryset = Country.objects.all()
        return super(FlagField, self).__init__(queryset=queryset, *args, **kwargs)

class VesselInfoForm(forms.ModelForm):
    
    # ModelForm won't fill in all the handy args for us if we sepcify our own
    # field
    _f = VesselInfo._meta.get_field('flag')
    flag = FlagField(
        required= _f.blank != True,
        help_text= _f.help_text,
        label= _f.verbose_name.capitalize(),
        initial='US',
    )

    class Meta:
        model = VesselInfo

class NiceVesselInfoForm(VesselInfoForm):
    '''\
    To be used with a ContactForm on the same page for adding a new Contact.
    '''
    
    contact_choices = (
        ('new', 'add a new contact'),
        ('other', 'use an existing contact'),
        ('none', 'no contact info'),
    )

    contact_choice = forms.ChoiceField(
        choices= tuple(),
        initial= 'none',
        widget= forms.RadioSelect,
        #help_text= "create a new contact for the vessel's contact?",
    )
    
    # should be the same as whatever ModelForm would generate for the 'contact'
    # field, except with a different name
    _f = VesselInfo._meta.get_field('contact')
    existing_contact = forms.ModelChoiceField(
        queryset= Contact.objects.all(),
        required= False,
        help_text= _f.help_text,
        label= _f.verbose_name.capitalize(),
    )
    
    def __init__(self, *args, **kwargs):
        super(NiceVesselInfoForm, self).__init__(*args, **kwargs)
        self['contact_choice'].field.choices = self.contact_choices
    
    class Meta:
        model = VesselInfo
        exclude = ('contact')

class ObserverVesselInfoForm(NiceVesselInfoForm):
    '''\
    To be used with a ContactForm on the same page for adding a new Contact.
    '''
    
    contact_choices = (
        ('new', 'add a new contact'),
        ('reporter', 'use the same contact as the reporter'),
        ('observer', 'use the same contact as the observer'),
        ('other', 'use an existing contact'),
        ('none', 'no contact info'),
    )
    
    class Meta:
        model = VesselInfo
        exclude = ('contact')

