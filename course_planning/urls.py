"""
The url patterns for the course_planning application.
"""

from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from . import views

urlpatterns = [
    url(r"^$", views.ProgramListView.as_view(), name="courseplanning-program-list"),
    url(
        r"^teaching-preferences/$",
        login_required(views.TeachingProfileDetailView.as_view()),
        name="courseplanning-teaching-profile",
    ),
    url(
        r"^teaching-preferences/update/$",
        login_required(views.TeachingProfileWizardView.as_view()),
        name="courseplanning-teaching-profile-wizard",
    ),
    url(
        r"^(?P<slug>[\w-]+)/$",
        views.ProgramDetailView.as_view(),
        name="courseplanning-program-detail",
    ),
    url(
        r"^(?P<slug>[\w-]+)/graph.svg$",
        views.ProgramDetailSvgView.as_view(),
        name="courseplanning-program-graph",
    ),
]
