from django.db import models

class TaxonManager(models.Manager):

    def descendants(self, taxon):
        'Return a tuple of all taxons that descend from the given taxon (not including the given taxon)'
        
        # how much does order matter ? This is a depth-first traversal right
        # now.
        children = taxon.subtaxons.all().order_by('name')
        result = []
        for child in children:
            result.append(child)
            result += self.descendants(child)

        return tuple(result)

    def with_descendants(self, taxon):
        'Return a tuple of all taxons that descend from the given taxon (including the given taxon)'

        return (taxon,) + self.descendants(taxon)

class Taxon(models.Model):
    '''\
    A taxon is a generic term for a grouping of organisms made by a taxonimist.
    Whether it's a genus or a species (or a subspecies or a infragenus, etc.) is
    somewhat arbitrary, although a standardized system is the goal of the ICZN.
    For our purposes, we have taxons with very well-accepted ranks. Unranked
    taxons are currently not supported (note that ranks are often used for
    sorting, so you would need at least some autogenerated rank based on the
    Taxon tree), which is more complicated than you think.
    '''

    # The ranks are numbered so that negative ones are part of a binomial name,
    # whereas positive ones are larger groupings.

    MAIN_RANKS = (
        (-1.0, 'species'),
        (0.0, 'genus'),
        (1.0, 'family'),
        (2.0, 'order'),
    )
    # generate the super-, sub-, and infra-, ranks
    RANK_CHOICES = ()
    for rank in MAIN_RANKS:
        RANK_CHOICES += (
            (rank[0] - 0.4, 'infra' + rank[1]),
            (rank[0] - 0.2, 'sub' + rank[1]),
            rank,
            (rank[0] + 0.4, 'super' + rank[1]),
        )

    name = models.CharField(
        max_length= 255,
        help_text= 'The scientific name for this taxon (i.e. the one in Latin).',
        verbose_name= 'scientific name',
    )
    common_names = models.CharField(
        max_length = 255,
        blank= True,
        help_text= '''\
        a comma-delimited list of common English name(s) for this taxon (e.g. "humpback whale" or "dolphins, porpises").
        '''
    )
    supertaxon = models.ForeignKey(
        'self',
        null= True,
        blank= True,
        # TODO should be subtaxa!
        related_name='subtaxons',
        help_text="The smallest taxon that contains this one",
    )
    rank = models.FloatField(choices=RANK_CHOICES)

    def _get_ancestors(self):
        if self.supertaxon is None:
            return []
        return self.supertaxon.ancestors + [self.supertaxon]
    'a list of ancestor Taxa, starting at a root'
    ancestors = property(_get_ancestors)

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

    # TODO cycle detection!

    objects = TaxonManager()

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

