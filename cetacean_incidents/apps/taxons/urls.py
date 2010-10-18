from django.conf.urls.defaults import *
import views

urlpatterns = patterns('',
    url(r'^search$', views.taxon_search, name='taxon_search'),
    url(r'^import$', views.import_search, name='taxon_import'),
    url(r'^import/(?P<tsn>\d+)$', views.import_tsn, name='taxon_import_tsn'),
    url(r'^itis$', views.itis_search, name='itis'),
    url(r'^import/add_taxa$', views.add_taxa, name='add_taxa'),
)

