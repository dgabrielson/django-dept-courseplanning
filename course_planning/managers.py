"""
Managers for the course_planning application.
"""
#######################
from __future__ import print_function, unicode_literals

from django.db import models

from .querysets import CourseInfoQuerySet, CourseProgramInfoQuerySet, ProgramQuerySet

#######################
#######################################################################

#######################################################################
#######################################################################
#######################################################################


class CustomQuerySetManager(models.Manager):
    """
    Custom Manager for an arbitrary model, just a wrapper for returning
    a custom QuerySet
    """

    use_for_related_fields = False
    queryset_class = models.query.QuerySet
    always_select_related = None

    # use always_select_related when the ``__str__`` method for a model
    #   pull foreign keys.

    def get_queryset(self):
        """
        Return the custom QuerySet
        """
        queryset = self.queryset_class(self.model)
        if self.always_select_related is not None:
            queryset = queryset.select_related(*self.always_select_related)
        return queryset


#######################################################################
#######################################################################

ProgramManager = ProgramQuerySet.as_manager

#######################################################################


class CourseInfoManagerOnly(CustomQuerySetManager):
    queryset_class = CourseInfoQuerySet
    always_select_related = ["course", "course__department"]


CourseInfoManager = CourseInfoManagerOnly.from_queryset(CourseInfoQuerySet)

#######################################################################


class CourseProgramInfoManagerOnly(CustomQuerySetManager):
    queryset_class = CourseProgramInfoQuerySet
    always_select_related = [
        "course",
        "course__course",
        "course__course__department",
        "program",
    ]


CourseProgramInfoManager = CourseProgramInfoManagerOnly.from_queryset(
    CourseProgramInfoQuerySet
)

#######################################################################
