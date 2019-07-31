"""
Course planning forms
"""
#######################################################################
from __future__ import print_function, unicode_literals

import datetime
import mimetypes

from django import forms
from django.contrib.admin import widgets
from django.forms.models import inlineformset_factory
from django.http import HttpResponse
from markuphelpers.forms import (
    LinedTextAreaMediaMixin,
    LinedTextareaWidget,
    ReStructuredTextFormMixin,
)

from . import conf
from .models import (
    CourseTeachingPreference,
    SemesterTeachingPreference,
    TeachingProfile,
    TeachingSurveyAnswer,
    TeachingSurveyQuestion,
    TimeslotTeachingPreference,
)
from .utils import make_student_load_report

####################################################################


class TeachingSurveyQuestionAdminForm(ReStructuredTextFormMixin, forms.ModelForm):
    restructuredtext_fields = [("question", True)]

    class Meta:
        fields = "__all__"
        model = TeachingSurveyQuestion
        widgets = {"question": LinedTextareaWidget}


#######################################################################


class TeachingSurveyQuestionForm(TeachingSurveyQuestionAdminForm):
    class Meta(TeachingSurveyQuestionAdminForm.Meta):
        fields = ["question"]

    class Media:
        css = {"all": ("css/forms.css",)}


#######################################################################


class TeachingSurveyAnswerForm(forms.ModelForm):
    class Meta:
        fields = ["answer"]
        model = TeachingSurveyAnswer
        widgets = {"answer": forms.Textarea(attrs={"rows": 4, "cols": 60})}

    class Media:
        css = {"all": ("css/forms.css",)}


#######################################################################


class TeachingProfileContainerForm(forms.ModelForm):
    """
    For model formsets to work on.
    """

    class Meta:
        model = TeachingProfile
        fields = []


#######################################################################


class TeachingProfileCoreForm(TeachingProfileContainerForm):
    class Meta:
        model = TeachingProfile
        fields = ["agreed_load", "preference_same_day", "preference_no_back_to_back"]

    class Media:
        css = {"all": ("css/forms.css",)}


#######################################################################


class CourseTeachingPreferenceForm(forms.ModelForm):
    class Meta:
        model = CourseTeachingPreference
        fields = ["score"]
        widgets = {
            "score": forms.TextInput(
                attrs={"min": 0, "max": "9", "type": "number", "style": "width:2.5em;"}
            )
        }

    class Media:
        css = {"all": ("css/forms.css",)}


#######################################################################


class TimeslotTeachingPreferenceForm(forms.ModelForm):
    class Meta:
        model = TimeslotTeachingPreference
        fields = ["score"]
        widgets = {
            "score": forms.TextInput(
                attrs={"min": 0, "max": "9", "type": "number", "style": "width:2.5em;"}
            )
        }

    class Media:
        css = {"all": ("css/forms.css",)}


#######################################################################


class SemesterTeachingPreferenceForm(forms.ModelForm):
    class Meta:
        model = SemesterTeachingPreference
        fields = ["preferred_load"]

    class Media:
        css = {"all": ("css/forms.css",)}


#######################################################################


class BaseSemesterFormSet(forms.BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.total_load = float(kwargs.pop("total_load"))
        return super().__init__(*args, **kwargs)

    def clean(self):
        if any(self.errors):
            return
        if self.total_load is None:
            raise forms.ValidationError(
                "There was an error retrieving your agreed load (sorry)."
            )
        load_v = [form.cleaned_data["preferred_load"] for form in self.forms]
        if sum(load_v) != self.total_load:
            raise forms.ValidationError(
                "The given loads do not total your agreed load from the previous step (\\( {} \\ne {} \\))".format(
                    sum(load_v), self.total_load
                )
            )


#######################################################################


class BaseScoreFormSet(forms.BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        """
        Note: there is no way for the formset factory functions
        to pass in the min_score kwarg.
        """
        self.min_score = kwargs.pop("min_score", 0)
        return super().__init__(*args, **kwargs)

    def clean(self):
        if any(self.errors):
            return
        score_v = [form.cleaned_data["score"] for form in self.forms]
        if sum(score_v) < self.min_score:
            raise forms.ValidationError("Your total score needs to be higher than that")


#######################################################################


def get_semester_teaching_preferences_formset(
    form=SemesterTeachingPreferenceForm, formset=BaseSemesterFormSet, **kwargs
):
    if "can_delete" not in kwargs:
        kwargs["can_delete"] = False
    if "extra" not in kwargs:
        kwargs["extra"] = 0
    return inlineformset_factory(
        TeachingProfile, SemesterTeachingPreference, form, formset, **kwargs
    )


#######################################################################


def get_course_teaching_preferences_formset(
    form=CourseTeachingPreferenceForm, formset=BaseScoreFormSet, **kwargs
):
    if "can_delete" not in kwargs:
        kwargs["can_delete"] = False
    if "extra" not in kwargs:
        kwargs["extra"] = 0
    return inlineformset_factory(
        TeachingProfile, CourseTeachingPreference, form, formset, **kwargs
    )


#######################################################################


def get_timeslot_teaching_preferences_formset(
    form=TimeslotTeachingPreferenceForm, formset=BaseScoreFormSet, **kwargs
):
    if "can_delete" not in kwargs:
        kwargs["can_delete"] = False
    if "extra" not in kwargs:
        kwargs["extra"] = 0
    return inlineformset_factory(
        TeachingProfile, TimeslotTeachingPreference, form, formset, **kwargs
    )


#######################################################################


def get_teaching_survey_answers_formset(
    form=TeachingSurveyAnswerForm, formset=forms.BaseInlineFormSet, **kwargs
):
    if "can_delete" not in kwargs:
        kwargs["can_delete"] = False
    if "extra" not in kwargs:
        kwargs["extra"] = 0
    return inlineformset_factory(
        TeachingProfile, TeachingSurveyAnswer, form, formset, **kwargs
    )


#######################################################################


class StudentLoadReportForm(forms.Form):
    """
    Funding Report input form.
    """

    start_date = forms.DateField(required=True)
    end_date = forms.DateField(required=True)
    format_ = forms.ChoiceField(
        choices=conf.get("spreadsheet_formats"),
        label="Format",
        required=True,
        initial=conf.get("default_spreadsheet_format"),
    )

    class Media:
        css = {"all": ("admin/css/widgets.css",)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["start_date"].widget = widgets.AdminDateWidget()
        self.fields["end_date"].widget = widgets.AdminDateWidget()

    def get_result_data(self):
        """
        Assumed that is_valid() has been checked and is True.

        Returns the data stream for the spreadsheet.
        """
        return make_student_load_report(
            self.cleaned_data["start_date"],
            self.cleaned_data["end_date"],
            self.cleaned_data["format_"],
        )

    def response_data(self):
        stream = self.get_result_data()
        format = self.cleaned_data["format_"]
        return format, stream

    def on_success(self):
        """
        Assumed that is_valid() has been checked and is True.
        """
        format, stream = self.get_response_data()
        filename = "student-load-report_%s" % datetime.date.today()
        filename += "." + format
        content_type, encoding = mimetypes.guess_type(filename)
        response = HttpResponse(content_type=content_type)
        response["Content-Disposition"] = "attachment; filename=" + filename
        response.write(stream)
        return response


#######################################################################

#######################################################################
