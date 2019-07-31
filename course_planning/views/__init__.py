"""
Views for the course_planning application
"""
#######################################################################
from __future__ import print_function, unicode_literals

from collections import OrderedDict

from classes.views import GraphvizTemplateResponse
from django.contrib import messages
from django.db.models import Count, Q, QuerySet
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from formtools.wizard.views import SessionWizardView

from ..forms import (
    TeachingProfileCoreForm,
    get_course_teaching_preferences_formset,
    get_semester_teaching_preferences_formset,
    get_teaching_survey_answers_formset,
    get_timeslot_teaching_preferences_formset,
)
from ..models import (
    CourseTeachingPreference,
    Program,
    SemesterTeachingPreference,
    TeachingProfile,
    TeachingSurveyAnswer,
    TeachingSurveyQuestion,
    TimeslotTeachingPreference,
)

#######################################################################
#######################################################################


class ProgramMixin(object):
    queryset = Program.objects.active()


#######################################################################


class ProgramListView(ProgramMixin, ListView):
    """
    List the programs
    """

    queryset = Program.objects.public()


#######################################################################


class ProgramDetailView(ProgramMixin, DetailView):
    """
    Detail for an indivudal program
    """


#######################################################################


class ProgramDetailSvgView(ProgramMixin, DetailView):
    """
    The program graph
    """

    template_name = "course_planning/program_detail.dot"
    response_class = GraphvizTemplateResponse
    content_type = "image/svg+xml"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        return context


#######################################################################


class TeachingProfileDetailView(DetailView):
    def get_object(self, *args, **kwargs):
        profile = get_object_or_404(
            TeachingProfile, person__username=self.request.user.username
        )
        return profile


#######################################################################


def get_wizard_view_kwargs():
    form_list = [TeachingProfileCoreForm, get_semester_teaching_preferences_formset()]
    # complicated query to filter out programs that don't have
    #   any valid choices in the form.
    program_queryset = (
        Program.objects.active()
        .filter(scheduled=True)
        .annotate(
            course_count=Count(
                "courseprograminfo",
                filter=Q(
                    courseprograminfo__active=True,
                    courseprograminfo__course__active=True,
                    courseprograminfo__course__course__active=True,
                ),
            )
        )
        .filter(course_count__gt=0)
    )
    program_count = program_queryset.count()
    for _ in range(program_count):
        form_list.append(get_course_teaching_preferences_formset())
    program_steps = [
        str(i)
        for i in range(
            TeachingProfileWizardView.BEFORE_PROGRAM_FORMS,
            program_count + TeachingProfileWizardView.BEFORE_PROGRAM_FORMS,
        )
    ]

    form_list.append(get_timeslot_teaching_preferences_formset())
    timeslot_step = str(program_count + TeachingProfileWizardView.BEFORE_PROGRAM_FORMS)
    form_list.append(get_teaching_survey_answers_formset())
    survey_step = str(
        program_count + TeachingProfileWizardView.BEFORE_PROGRAM_FORMS + 1
    )

    computed_form_list = OrderedDict()
    for i, f in enumerate(form_list):
        computed_form_list[str(i)] = f

    return {
        "form_list": computed_form_list,
        "program_queryset": program_queryset,
        "program_count": program_count,
        "program_steps": program_steps,
        "timeslot_step": timeslot_step,
        "survey_step": survey_step,
    }


#######################################################################


class TeachingProfileWizardView(SessionWizardView):
    template_name = "course_planning/teaching_profile_wizard.html"
    # instance variables provided by ``get_wizard_view_kwargs()``
    form_list = [TeachingProfileCoreForm, get_semester_teaching_preferences_formset()]
    program_queryset = None
    program_count = None
    program_steps = None
    timeslot_step = None
    survey_step = None
    BEFORE_PROGRAM_FORMS = 2

    def __init__(self, *args, **kwargs):
        kwargs.update(get_wizard_view_kwargs())
        return super().__init__(*args, **kwargs)

    def get_form_instance(self, step):
        # determine the step if not given
        form_instance = super().get_form_instance(step)
        profile = get_object_or_404(
            TeachingProfile, person__username=self.request.user.username
        )
        return profile

    def populate_profile(
        self, profile, model, accessor, values, foreign_key=True, extra_filters=None
    ):
        """
        This uses set differences to compute necessary adds and removes.
        """
        # print('populate_profile() begins')
        # print('model =', model.__name__)
        if extra_filters is None:
            extra_filters = {}
        have = set(
            model.objects.filter(profile=profile, **extra_filters).values_list(
                accessor, flat=True
            )
        )
        # print('have:', have)
        # construct need set depending on type of values...
        if foreign_key:
            if isinstance(values, QuerySet):
                need = set(values.values_list("pk", flat=True))
            else:
                need = set((v.pk for v in values))
        else:
            need = set(values)
        # print('need:', need)
        # difference sets:
        add_values = need.difference(have)
        # print('add values:', add_values)
        remove_values = have.difference(need)
        # print('remove values:', remove_values)
        if foreign_key:
            accessor += "_id"
        for v in add_values:
            kwargs = {"profile": profile, accessor: v}
            # print('add:', kwargs)
            model.objects.create(**kwargs)
        for v in remove_values:
            kwargs = {"profile": profile, accessor: v}
            # print('delete:', kwargs)
            model.objects.filter(**kwargs).delete()
        # print('populate_profile() ends')

    def get_form_kwargs(self, step):
        kwargs = super().get_form_kwargs(step)
        profile = get_object_or_404(
            TeachingProfile, person__username=self.request.user.username
        )

        if step == "1":
            # prepopulate
            codes = (c for c, d in SemesterTeachingPreference.SEMESTER_CHOICES)
            self.populate_profile(
                profile,
                SemesterTeachingPreference,
                "semester",
                codes,
                foreign_key=False,
            )
            kwargs["queryset"] = SemesterTeachingPreference.objects.filter(active=True)
            prev_data = self.storage.get_step_data("0")
            agreed_load = None
            if prev_data is not None:
                agreed_load = prev_data.get("0-agreed_load", None)
            kwargs["total_load"] = agreed_load

        if step in self.program_steps:
            from classes.models import Course

            index = int(step) - self.BEFORE_PROGRAM_FORMS
            program = self.program_queryset[index]
            course_list = Course.objects.active().filter(
                department__active=True,
                courseinfo__active=True,
                courseinfo__courseprograminfo__active=True,
                courseinfo__courseprograminfo__program_id=program.pk,
            )

            # prepopulate
            extra_filters = {
                "course__courseinfo__courseprograminfo__program_id": program.pk
            }
            self.populate_profile(
                profile,
                CourseTeachingPreference,
                "course",
                course_list,
                extra_filters=extra_filters,
            )
            kwargs["queryset"] = CourseTeachingPreference.objects.filter(
                active=True, course__in=course_list
            )

        if step == self.timeslot_step:
            # prepopulate
            from classes.models import Timeslot

            timeslot_qs = Timeslot.objects.filter(active=True, scheduled=True)
            self.populate_profile(
                profile, TimeslotTeachingPreference, "timeslot", timeslot_qs
            )
            kwargs["queryset"] = TimeslotTeachingPreference.objects.filter(active=True)

        if step == self.survey_step:
            # prepopulate
            question_qs = TeachingSurveyQuestion.objects.filter(active=True)
            self.populate_profile(
                profile, TeachingSurveyAnswer, "question", question_qs
            )
            kwargs["queryset"] = TeachingSurveyAnswer.objects.filter(
                question__active=True, active=True
            )

        return kwargs

    def get_form_title(self, step):
        if step == "0":
            return "Basic information"
        if step == "1":
            return "Preferred semester teaching loads"
        if step in self.program_steps:
            index = int(step) - self.BEFORE_PROGRAM_FORMS
            program = self.program_queryset[index]
            return "Preferences for " + str(program)
        if step == self.timeslot_step:
            return "Timeslot preferences"
        if step == self.survey_step:
            return "Additional questions"
        return "UNKOWN"

    def get_formset_label(self, step):
        if step == "1":
            return "semester"
        if step in self.program_steps:
            return "course"
        if step == self.timeslot_step:
            return "timeslot"
        if step == self.survey_step:
            return "question"
        return ""

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form, **kwargs)
        step = self.steps.current
        context["wizard_step"] = step
        context["form_title"] = self.get_form_title(step)
        context["formset_label"] = self.get_formset_label(step)
        return context

    def get_done_url(self, profile):
        return profile.get_absolute_url()

    def done(self, form_list, **kwargs):
        # save all the things!
        # print('running done()')
        form_list = list(form_list)  # convert from odict_values
        profile_form = form_list[0]
        profile = profile_form.instance
        profile.last_reviewed = now()
        for form in form_list:
            form.save()
        messages.success(
            self.request,
            "Thanks! Your teaching preferences have been updated.",
            fail_silently=True,
        )
        # print('done() finished redirect')
        return HttpResponseRedirect(self.get_done_url(profile))


#######################################################################
#######################################################################
