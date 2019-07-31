"""
Template tags for the course_planning application.
"""
#####################################################################
from __future__ import print_function, unicode_literals

from django import template
from django.utils.timezone import now

from ..models import DraftScheduleSession

#####################################################################

register = template.Library()

#####################################################################


@register.simple_tag(name="upcoming_sessions")
def get_upcoming_schedulesessions():
    queryset = DraftScheduleSession.objects.filter(active=True)
    queryset = queryset.filter(start_date__gt=now())
    return queryset


#####################################################################
