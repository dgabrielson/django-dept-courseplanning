"""
Schedule related views
"""
###############################################################

from classes.models import Course
from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import RedirectView
from django.views.generic.detail import DetailView
from django.views.generic.edit import UpdateView

from ...mixins.cbv_admin import AdminFormMixin, AdminSiteViewMixin
from ...mixins.formset import UpdateViewWithFormset
from ...models import DraftScheduleSession, TeachingProfile
from ...utils import preference_by_course
from ..forms import get_draftsection_formset
from ..utils import auto, initialize

###############################################################


class DraftScheduleSessionObjectMixin(object):
    def get_object(self, queryset=None, pk=None):
        if queryset is None:
            queryset = DraftScheduleSession.objects.all()
        if pk is None:
            pk = self.kwargs.get("pk", None)
        return get_object_or_404(queryset, pk=pk)


###############################################################


class AdminScheduleView(
    DraftScheduleSessionObjectMixin,
    AdminSiteViewMixin,
    AdminFormMixin,
    UpdateViewWithFormset,
    UpdateView,
):
    """
    Actually just the inline formset associated with this session
    """

    model = DraftScheduleSession
    fields = []
    form_class = None
    template_name = "admin/course_planning/draftschedulesession/worksheet.html"

    def get_formset_class(self):
        return get_draftsection_formset()

    def get_formset_kwargs(self, *args, **kwargs):
        kwargs = super().get_formset_kwargs(*args, **kwargs)
        kwargs["queryset"] = self.object.draftsection_set.filter(active=True).order_by(
            "-semester", "course", "verbose_name"
        )
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["teachingprofile_list"] = TeachingProfile.objects.filter(
            active=True
        ).order_by("person")
        return context


###############################################################


class AdminInitializer(
    DraftScheduleSessionObjectMixin, AdminSiteViewMixin, RedirectView
):
    initializer = None

    def get_redirect_url(self, pk, **kwargs):
        if self.initializer is None:
            raise ImproperlyConfigured(
                "Child classes must set the initializer class attribute"
            )
        obj = self.get_object(pk=pk)
        try:
            self.initializer(obj)
        except initialize.AlreadyDone:
            pass
        return reverse(
            "admin:course_planning_draftschedulesession_change", args=[obj.pk]
        )


###############################################################


class AdminInitializeFromCurrentCourseData(AdminInitializer):
    initializer = initialize.from_classes_current


class AdminInitializeFromPrevCourseData(AdminInitializer):
    initializer = initialize.from_classes_last_year


class AdminInitializeFromTwoYearsAgoCourseData(AdminInitializer):
    initializer = initialize.from_classes_two_years_ago


###############################################################


class AdminAutoSchedule(
    DraftScheduleSessionObjectMixin, AdminSiteViewMixin, RedirectView
):
    def get_redirect_url(self, pk, **kwargs):
        obj = self.get_object(pk=pk)
        auto.main(obj)
        return reverse(
            "admin:course_planning_draftschedulesession_change", args=[obj.pk]
        )


###############################################################


class AdminCourseDetailView(AdminSiteViewMixin, DetailView):
    model = Course
    template_name = "admin/course_planning/draftschedulesession/course_detail.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["preference_list"] = preference_by_course(self.object, min_score=4)
        if self.request.GET.get("_popup", None):
            context["is_popup"] = True
        return context


###############################################################


class AdminTeachingProfileDetailView(AdminSiteViewMixin, DetailView):
    model = TeachingProfile
    template_name = (
        "admin/course_planning/draftschedulesession/teachingprofile_detail.html"
    )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        session_id = self.kwargs.get("session_id", None)
        session = get_object_or_404(DraftScheduleSession, pk=session_id)
        context["session"] = session
        context["course_list"] = self.object.draftsection_set.filter(
            active=True, session=session
        ).order_by("-semester", "course", "verbose_name")
        if self.request.GET.get("_popup", None):
            context["is_popup"] = True
        return context


###############################################################
