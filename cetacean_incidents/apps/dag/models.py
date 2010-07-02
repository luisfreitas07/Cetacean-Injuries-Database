from django.db import models

class RootDAGNodeManager(models.Manager):
    def get_query_set(self):
        qs = super(self.__class__, self).get_query_set()
        # filter out all DAGNodes that are the subtype in a DAGEdge
        # TODO simplier way to query for that?
        return qs.annotate(supertypes_num=models.Count('supertypes')).filter(supertypes_num=0)

# TODO There's gotta be a more elegant way than these factory functions.
# Perhaps using metaclasses?

def DAGNode_factory(edge_model_name):
    class DAGNode(models.Model):
        supertypes= models.ManyToManyField(
            'self',
            through= edge_model_name,
            symmetrical= False,
            blank= True,
            null= True,
            related_name= 'subtypes',
            help_text= 'what other types would be implied by this type?'
        )
        
        objects = models.Manager()
        roots = RootDAGNodeManager()
        
        def _get_implied_supertypes_with_ignore(self, ignore_types):
            # The ignore_types arg is a set of DAGNodes that won't be included in 
            # the results. It's used to prevent infinite loops in recursive calls.
            
            # be sure 'self' is in ignore_types.
            ignore_types |= set([self])
            # traverse supertypes and return a set of all DAGNodes seen
            implied_supertypes = set(self.supertypes.all()) - ignore_types
            if len(implied_supertypes):
                to_traverse = implied_supertypes.copy()
                for supertype in to_traverse:
                    implied_supertypes |= supertype._get_implied_supertypes_with_ignore(
                        ignore_types= ignore_types | implied_supertypes,
                    )
            return frozenset(implied_supertypes)

        @property
        def implied_supertypes(self):
            return self._get_implied_supertypes_with_ignore(ignore_types=set())
        
        class Meta:
            abstract = True

    return DAGNode

class DAGException(Exception):
    '''\
    Exception thrown when a DAGEdge would violate the directed-
    acyclic-graph nature of DAGNodes. E.g. when the subtype and supertype
    are the same.
    '''
    pass

def DAGEdge_factory(node_model):
    class DAGEdge(models.Model):
        
        '''\
        Intended to be used as the 'through' model in a ManyToManyField('self') 
        when implementing a Directed Acyclic Graph (DAG). Basically just does 
        cycle-checking when a new relation is added.
        '''
        
        subtype = models.ForeignKey(
            node_model,
            related_name= 'subtype_relations',
        )
        supertype = models.ForeignKey(
            node_model,
            related_name= 'supertype_relations',
        )
        
        def save(self, *args, **kwargs):
            # check if this new relation would create a cycle in the DAG
            if self.subtype == self.supertype:
                raise self.DAGException(
                    "%s can't be a supertype of itself!" % unicode(self.subtype),
                )
                
            if self.subtype in self.supertype.implied_supertypes:
                raise self.DAGException(
                    # TODO determined what the cycle would be
                    "%s can't be a supertype of %s, that would create a cycle!" % (
                        unicode(self.supertype),
                       unicode(self.subtype),
                    )
                )

            return super(DAGEdge, self).save(*args, **kwargs)
        
        def __unicode__(self):
            return "%r -> %r" % (self.subtype, self.supertype)
        
        class Meta:
            abstract = True
            unique_together = ('subtype', 'supertype')

    return DAGEdge
    