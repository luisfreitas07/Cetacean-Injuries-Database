import base64
import bz2
from datetime import datetime

from django.conf import settings
from django.core.paginator import (
    Paginator,
    InvalidPage,
    EmptyPage,
)
from django.core.urlresolvers import reverse
from django.db.models import Q
from django import forms as django_forms
from django.forms import Media
from django.http import HttpResponse
from django.shortcuts import (
    render_to_response,
    redirect,
)
from django.template import (
    Context,
    RequestContext,
)
from django.views.decorators.http import condition
from django.utils.datastructures import SortedDict

from django.contrib.auth.decorators import login_required

from cetacean_incidents.decorators import (
    permission_required,
    global_etag,
)
from cetacean_incidents import generic_views

from cetacean_incidents.forms import PagingForm

from cetacean_incidents.apps.entanglements.models import Entanglement

from cetacean_incidents.apps.jquery_ui.tabs import Tabs

from cetacean_incidents.apps.reports.forms import ReportForm

from cetacean_incidents.apps.shipstrikes.models import Shipstrike

from cetacean_incidents.apps.taxons.models import Taxon

from cetacean_incidents.apps.uncertain_datetimes import UncertainDateTime
from cetacean_incidents.apps.uncertain_datetimes.models import UncertainDateTimeField

from ..models import (
    Animal,
    Case,
    YearCaseNumber,
)
from ..forms import (
    AnimalForm,
    CaseAnimalForm,
    CaseForm,
    CaseMergeForm,
    CaseMergeSourceForm,
    CaseSearchForm,
    CaseReportForm,
)
from ..templatetags.case_extras import YearsForm

from tabs import (
    AnimalTab,
    CaseTab,
)

def rfc822_quoting(string):
    """Returns a "quoted-string" as defined in IETF RFC 822."""
    # TODO will a HttpResponse do this for us?
    
    # escape any of '"' '\' or U+000D
    if isinstance(string, unicode):
        string = string.encode('utf-8')
    string = string.replace('\\', '\\\\')
    string = string.replace('"', '\\"')
    string = string.replace('\x0d', '\\\x0d')
    
    # enclose in quotes
    return '"%s"' % string

@login_required
def case_detail(request, case_id, extra_context={}):
    # TODO this is quite inefficient
    case = Case.objects.get(id=case_id)
    case_class = case.specific_class()
    
    # TODO hack
    if case.case_type == 'Entanglement':
        return redirect(case.specific_instance())
    
    # the case_detail.html template needs jQuery
    if not 'media' in extra_context:
        extra_context['media'] = Media(js=(settings.JQUERY_FILE,))

    if request.user.has_perms(('incidents.change_case', 'incidents.delete_case')):
        merge_form = CaseMergeSourceForm(destination=case)
        extra_context['merge_form'] = merge_form
        extra_context['media'] += merge_form.media
        extra_context['media'] += Media(js=(settings.JQUERY_FILE,))

    return generic_views.object_detail(
        request,
        object_id= case_id,
        queryset= case_class.objects.select_related().all(),
        template_object_name= 'case',
        extra_context= extra_context,
    )

@login_required
def cases_by_year(request, year=None):
    # handle the year in a GET arg:
    yf = YearsForm(request.GET)
    if yf.is_valid():
        year = yf.cleaned_data['year']
        return redirect(reverse('cases_by_year', args=[year]), permanent=True)
    
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
@condition(etag_func=global_etag)
def case_search(request, searchform_class=CaseSearchForm, template=u'incidents/case_search.html'):
    
    # use a SortedDict to ensure 'paging' comes last
    form_classes = SortedDict([
        ('case', searchform_class),
        ('paging', PagingForm),
    ])
    forms = SortedDict()
    for name, cls in form_classes.items():
        form_kwargs = {
            'prefix': name
        }
        if request.GET:
            form_kwargs['data'] = request.GET
        forms[name] = cls(**form_kwargs)
    
    case_list = tuple()
    
    search_done = False
    if forms['case'].is_bound:
        if forms['case'].is_valid():
            case_list = forms['case'].results()
            search_done = True
    
    per_page = 1
    page = 1
    if forms['paging'].is_valid():
        if 'per_page' in forms['paging'].cleaned_data:
            per_page = forms['paging'].cleaned_data['per_page']
        if 'page_num' in forms['paging'].cleaned_data:
            page = forms['paging'].cleaned_data['page_num']

    paginator = Paginator(case_list, per_page)
    
    try:
        cases = paginator.page(page)
    except (EmptyPage, InvalidPage):
        cases = paginator.page(paginator.num_pages)
    
    # use an unreserved character so it doesn't get escaped in the URL
    all_ids = u"_".join(map(lambda c: unicode(c.id), case_list))
    # This make sense as a URL, conceptually, so let's try to keep it that way
    MAX_GET_LENGTH = 1000
    if len(all_ids) > MAX_GET_LENGTH:
        zall_ids = all_ids.encode('utf-8')
        zall_ids = bz2.compress(zall_ids)
        zall_ids = base64.urlsafe_b64encode(zall_ids)
        # prepend a 'z' so we know it was compressed
        zall_ids = u'z' + zall_ids.decode('utf-8')
        if len(zall_ids) < len(all_ids):
            all_ids = zall_ids
    
    media = reduce(lambda m, f: m + f.media, forms.values(), Media())
    
    return render_to_response(
        template,
        {
            'forms': forms,
            'is_bound': search_done,
            'media': media,
            'cases': cases,
            'all_ids': all_ids,
            'case_count': paginator.count,
        },
        context_instance= RequestContext(request),
    )

@login_required
def case_report(request):
    form_classes = {
        'case_report': CaseReportForm,
        'new_report': ReportForm,
    }
    form_kwargs = {}
    for name, cls in form_classes.items():
        form_kwargs[name] = {
            'prefix': name
        }
    if request.POST:
        form_kwargs['case_report']['data'] = request.POST
    
    # the GET string could have a value called 'cases' that's a
    # comma-delimited list of case IDs
    if request.GET and 'cases' in request.GET:
        case_ids = request.GET['cases']

        # 'cases' may have been compressed to keep the URL length down
        if case_ids[0] == u'z':
            case_ids = case_ids[1:]
            case_ids = case_ids.encode('utf-8')
            case_ids = base64.urlsafe_b64decode(case_ids)
            case_ids = bz2.decompress(case_ids)
            case_ids = case_ids.decode('utf-8')
        
        case_ids = map(int, case_ids.split('_'))
    else:
        case_ids = []
    cases = Case.objects.filter(id__in=case_ids)
    form_kwargs['case_report']['cases'] = cases

    forms = {}
    forms['case_report'] = form_classes['case_report'](**form_kwargs['case_report'])
    # only bind forms['new_report'] if 'new' was chosen in forms['case_report']
    if forms['case_report'].is_valid():
        if forms['case_report'].cleaned_data['new'] == 'new':
            form_kwargs['new_report'].update({
                'data': request.POST,
                'files': request.FILES,
            })
    forms['new_report'] = form_classes['new_report'](**form_kwargs['new_report'])

    if forms['case_report'].is_valid():
        report = None
        if forms['case_report'].cleaned_data['new'] == 'new':
            if forms['new_report'].is_valid():
                save = bool(forms['new_report'].cleaned_data['name'])
                report = forms['new_report'].save(commit=False)
                if save:
                    report.uploader = request.user
                    report.save()
                    forms['new_report'].save_m2m()
                
        elif forms['case_report'].cleaned_data['new'] == 'existing':
            report = forms['case_report'].cleaned_data['report']

        if not report is None:
            # use the cases list from the form, not from the URL
            context = {'cases': forms['case_report'].cleaned_data['cases']}

            if forms['case_report'].cleaned_data['to_pdf']:
                rendered = report.render_to_pdf(context)
                response = HttpResponse(rendered, mimetype='application/pdf')
                name = forms['case_report'].cleaned_data['pdf_name'] 
                if not name:
                    name = 'report.pdf'
                response['Content-Disposition'] = 'attachment; filename=%s' % rfc822_quoting(name)
                return response

            rendered = report.render(context)
            return HttpResponse(rendered, mimetype=report.format)
        
    template_media = Media(
        js= (settings.JQUERY_FILE, 'radiohider.js', 'checkboxhider.js'),
    )
    media = reduce(lambda m, f: m + f.media, forms.values(), template_media)
    
    return render_to_response(
        "incidents/case_report.html",
        {
            'cases': cases,
            'forms': forms,
            'media': media,
        },
        RequestContext(request),
    )

# TODO login_required?
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
        form = CaseAnimalForm(request.POST, initial={'animal': case.animal.pk})
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
        form = CaseAnimalForm(initial={'animal': case.animal.pk})
    
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
        animal_form = AnimalForm(request.POST, prefix='animal', instance=case.animal)
        if animal_form.is_valid() and case_form.is_valid():
            animal_form.save()
            case_form.save()
            return redirect(case)
            
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
        form = CaseForm(request.POST, prefix='case', instance=case)
    else:
        form = CaseForm(prefix='case', instance=case)
        
    return _change_case(request, case, form)

@login_required
@permission_required('incidents.change_case')
@permission_required('incidents.delete_case')
def case_merge(request, destination_id, source_id=None):
    # the "source" case will be deleted and references to it will be change to
    # the "destination" case
    
    destination = Case.objects.get(id=destination_id)
    
    if source_id is None:
        merge_form = CaseMergeSourceForm(destination, request.GET)
        if not merge_form.is_valid():
            return redirect('case_detail', destination.id)
        source = merge_form.cleaned_data['source']
    else:
        source = Case.objects.get(id=source_id)

    form_kwargs = {
        'source': source,
        'destination': destination,
    }
    
    if request.method == 'POST':
        form = CaseMergeForm(data=request.POST, **form_kwargs)
        if form.is_valid():
            form.save()
            form.delete()
            return redirect('case_detail', destination.id)
    else:
        form = CaseMergeForm(**form_kwargs)
    
    return render_to_response(
        'incidents/case_merge.html',
        {
            'object_name': 'case',
            'object_name_plural': 'cases',
            'destination': destination,
            'source': source,
            'form': form,
            'media': form.media,
        },
        context_instance= RequestContext(request),
    )

