from django.conf.urls.defaults import *
from models import Animal

animal_args = {
    'queryset': Animal.objects.all(),
    'template_object_name': 'animal',
}

urlpatterns = patterns('django.views.generic.list_detail',
    url(r'^$', 'object_list', animal_args, name='animal_list'),
    url(r'^(?P<object_id>\d+)/$', 'object_detail', animal_args, name='animal_detail'),
)
