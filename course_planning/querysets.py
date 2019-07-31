"""
Models for the course_planning application.
"""
#######################
from __future__ import print_function, unicode_literals

import operator

#######################
#######################################################################
from functools import reduce

from django.core.exceptions import ImproperlyConfigured
from django.db import models

#######################################################################
#######################################################################
#######################################################################


class BaseCustomQuerySet(models.query.QuerySet):
    """
    Custom QuerySet.
    """

    def active(self):
        """
        Returns only the active items in this queryset
        """
        return self.filter(active=True)

    def search(self, *criteria):
        """
        Magic search for objects.
        This is heavily modelled after the way the Django Admin handles
        search queries.
        See: django.contrib.admin.views.main.py:ChangeList.get_queryset
        """
        if not hasattr(self, "search_fields"):
            raise ImproperlyConfigured(
                "No search fields.  Provide a "
                "search_fields attribute on the QuerySet."
            )

        if len(criteria) == 0:
            assert False, "Supply search criteria"

        terms = map(lambda s: "{}".format(s), criteria)
        if len(terms) == 1:
            terms = terms[0].split()

        def construct_search(field_name):
            if field_name.startswith("^"):
                return "%s__istartswith" % field_name[1:]
            elif field_name.startswith("="):
                return "%s__iexact" % field_name[1:]
            elif field_name.startswith("@"):
                return "%s__search" % field_name[1:]
            else:
                return "%s__icontains" % field_name

        qs = self.filter(active=True)
        orm_lookups = [
            construct_search("{}".format(search_field))
            for search_field in self.search_fields
        ]
        for bit in terms:
            or_queries = [models.Q(**{orm_lookup: bit}) for orm_lookup in orm_lookups]
            qs = qs.filter(reduce(operator.or_, or_queries))

        return qs.distinct()


#######################################################################
#######################################################################
#######################################################################


class ProgramQuerySet(BaseCustomQuerySet):
    def public(self):
        """
        Returns only the active and public items in this queryset
        """
        return self.filter(active=True, public=True)


#######################################################################


class CourseInfoQuerySet(BaseCustomQuerySet):
    pass


#######################################################################


class CourseProgramInfoQuerySet(BaseCustomQuerySet):
    def public(self):
        """
        Returns the items that have public programs.
        """
        return self.filter(
            active=True, program__active=True, program__public=True
        ).order_by("-constraint", "program")

    def required(self):
        return self.filter(active=True, constraint="r")

    def recommended(self):
        return self.filter(active=True, constraint="c")

    def optional(self):
        return self.filter(active=True, constraint="o")


#######################################################################
