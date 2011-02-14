from datetime import datetime

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.forms import Media
from django.shortcuts import render_to_response, redirect
from django.template import Context, RequestContext

from cetacean_incidents import generic_views
from cetacean_incidents.decorators import permission_required

from cetacean_incidents.apps.uncertain_datetimes import UncertainDateTime
from cetacean_incidents.apps.uncertain_datetimes.models import UncertainDateTimeField

from ..models import Animal, Case, YearCaseNumber
from ..forms import AnimalForm, CaseForm, CaseSearchForm, CaseAnimalForm

from cetacean_incidents.apps.jquery_ui.tabs import Tabs
from cetacean_incidents.apps.entanglements.models import Entanglement
from cetacean_incidents.apps.shipstrikes.models import Shipstrike

from tabs import AnimalTab, CaseTab, CaseSINMDTab

@login_required
def case_detail(request, case_id, extra_context={}):
    # TODO this is quite inefficient
    case = Case.objects.get(id=case_id)
    case_class = case.specific_class()
    return generic_views.object_detail(
        request,
        object_id= case_id,
        queryset= case_class.objects.select_related().all(),
        template_object_name= 'case',
        extra_context= extra_context,
    )

@login_required
def cases_by_year(request, year=None):
    if year is None:
        year = datetime.now().year
    year = int(year)
    cases = Case.objects.filter(observation__datetime_observed__startswith=u"%04d" % year).order_by('current_yearnumber__year', 'current_yearnumber__number', 'pk')
    # Oracle doesn't support distinct, so this is a work-around
    case_list = []
    case_set = set()
    for c in cases:
        if not c in case_set:
            case_list.append(c)
        case_set.add(c)
    cases = case_list
    return render_to_response(
        "incidents/cases_by_year.html",
        {
            'year': year,
            'cases': cases,
        },
        context_instance= RequestContext(request),
    )

@login_required
def case_search(request, after_date=None, before_date=None):
    # prefix should be the same as the homepage
    prefix = 'case_search'
    form_kwargs = {
        'prefix': prefix,
    }
    if request.GET:
        form_kwargs['data'] = request.GET
    else:
        data = {}
        if not after_date is None:
            data[prefix + '-after_date'] = after_date
        if not before_date is None:
            data[prefix + '-before_date'] = before_date
        if data:
            form_kwargs['data'] = data
    form = CaseSearchForm(**form_kwargs)
    
    case_list = tuple()

    if form.is_valid():

        manager = Case.objects
        if form.cleaned_data['case_type']:
            # TODO go through different case types automatically
            ct = form.cleaned_data['case_type']
            if ct == 'e':
                manager = Entanglement.objects
            if ct == 's':
                manager = Shipstrike.objects
            if ct == 'c':
                manager = Case.objects
        
        query = Q()
    
        if form.cleaned_data['observed_after_date']:
            
            date = form.cleaned_data['observed_after_date']
            date = UncertainDateTime.from_date(date)
            
            query &= UncertainDateTimeField.get_after_q(date, 'observation__datetime_observed')
            
        if form.cleaned_data['observed_before_date']:

            date = form.cleaned_data['observed_before_date']
            date = UncertainDateTime.from_date(date)
            
            query &= UncertainDateTimeField.get_before_q(date, 'observation__datetime_observed')
        
        if form.cleaned_data['reported_after_date']:
        
            date = form.cleaned_data['reported_after_date']
            date = UncertainDateTime.from_date(date)
            
            query &= UncertainDateTimeField.get_after_q(date, 'observation__datetime_reported')
            
        if form.cleaned_data['reported_before_date']:

            date = form.cleaned_data['reported_before_date']
            date = UncertainDateTime.from_date(date)
            
            query &= UncertainDateTimeField.get_before_q(date, 'observation__datetime_reported')

        if form.cleaned_data['taxon']:
            t = form.cleaned_data['taxon']
            # TODO handle taxon uncertainty!
            query &= Q(observation__taxon__in=Taxon.objects.with_descendants(t))

        if form.cleaned_data['case_name']:
            name = form.cleaned_data['case_name']
            query &= Q(names__icontains=name)

        if form.cleaned_data['observation_narrative']:
            on = form.cleaned_data['observation_narrative']
            query &= Q(observation__narrative__icontains=on)

        # TODO shoulde be ordering such that cases with no date come first
        case_order_args = ('-current_yearnumber__year', '-current_yearnumber__number', 'id')

        # TODO Oracle doesn't support distinct() on models with TextFields
        #cases = manager.filter(query).distinct().order_by(*case_order_args)
        cases = manager.filter(query).order_by(*case_order_args)
        
        # simulate distinct() for Oracle
        # an OrderedSet in the collections library would be nice...
        # TODO not even a good workaround, since we have to pass in the count
        # seprately
        seen = set()
        case_list = list()
        for c in cases:
            if not c in seen:
                seen.add(c)
                case_list.append(c)

    return render_to_response(
        "incidents/case_search.html",
        {
            'form': form,
            'media': form.media,
            'case_list': case_list,
            'case_count': len(case_list),
        },
        context_instance= RequestContext(request),
    )

def edit_case_animal(request, case_id):
    
    case = Case.objects.get(id=case_id)
    
    # we'll need to change the animal for all this cases observations, and for
    # any cases they're relevant to, and any of those cases other observations,
    # etc.
    case_set = set([case])
    observation_set = set()
    sets_changed = True
    while sets_changed:
        sets_changed = False
        for c in case_set:
            for o in c.observation_set.all():
                if o not in observation_set:
                    observation_set.add(o)
                    sets_changed = True
        for o in observation_set:
            for c in o.cases.all():
                if c not in case_set:
                    case_set.add(c)
                    sets_changed = True
    
    if request.method == 'POST':
        form = CaseAnimalForm(request.POST, initial={'animal': case.animal})
        if form.is_valid():
            # empty value means new animal
            if form.cleaned_data['animal'] is None:
            # TODO wrap the creation of the animal and the saving of the cases
            # in a transaction? or is that already handled by middleware?
                animal = Animal.objects.create()
            else:
                animal = form.cleaned_data['animal']
            for c in case_set:
                c.animal = animal
                c.save()
            for o in observation_set:
                o.animal = animal
                o.save()
            return redirect(case)

    else:
        form = CaseAnimalForm(initial={'animal': case.animal})
    
    return render_to_response(
        "incidents/edit_case_animal.html",
        {
            'case': case,
            'case_set': case_set,
            'observation_set': observation_set,
            'form': form,
            'media': form.media,
        },
        context_instance= RequestContext(request),
    )

def _change_case(
        request,
        case,
        case_form,
        template='incidents/edit_case.html',
        additional_tabs=[],
        additional_tab_context={},
    ):

    if request.method == 'POST':
        print '_change_case: POST'
        animal_form = AnimalForm(request.POST, prefix='animal', instance=case.animal)
        if animal_form.is_valid() and case_form.is_valid():
            print '_change_case: valid'
            animal_form.save()
            case_form.save()
            return redirect(case)
        else:
            print repr({
                'animal_form': animal_form.errors,
                'case_form': case_form.errors,
            })
            
    else:
        animal_form = AnimalForm(prefix='animal', instance=case.animal)
    
    tab_context = Context({
        'animal': case.animal,
        'animal_form': animal_form,
        'case': case,
        'case_form': case_form,
    })
    tab_context.update(additional_tab_context)
    
    tabs = [
        AnimalTab(html_id='animal'),
        CaseTab(html_id='case'),
        CaseSINMDTab(html_id='case-sinmd'),
    ] + additional_tabs
    for t in tabs:
        t.context = tab_context
    
    tabs = Tabs(tabs)
    
    template_media = Media(
        css= {'all': (settings.JQUERYUI_CSS_FILE,)},
        js= (settings.JQUERY_FILE, settings.JQUERYUI_JS_FILE),
    )
    
    return render_to_response(
        template, 
        {
            'animal': case.animal,
            'case': case,
            'tabs': tabs,
            'media': case_form.media + animal_form.media + tabs.media + template_media,
        },
        context_instance= RequestContext(request),
    )

@login_required
@permission_required('incidents.change_case')
@permission_required('incidents.change_animal')
def edit_case(request, case_id):

    case = Case.objects.get(id=case_id).specific_instance()

    if request.method == 'POST':
        print "post!"
        form = CaseForm(request.POST, prefix='case', instance=case)
    else:
        form = CaseForm(prefix='case', instance=case)
        
    return _change_case(request, case, form)

