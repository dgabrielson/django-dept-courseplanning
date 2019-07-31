"""
Schedule related forms
"""
###############################################################

from __future__ import print_function, unicode_literals

from classes.models import Timeslot
from django import forms
from django.forms.models import inlineformset_factory
from django_select2.forms import ModelSelect2Widget

from ..models import DraftScheduleSession, DraftSection, TeachingProfile

###############################################################


class TeachingProfileWidget(ModelSelect2Widget):
    model = TeachingProfile
    queryset = TeachingProfile.objects.filter(active=True).order_by("person")
    search_fields = [
        "person__cn__icontains",
        "person__username__icontains",
        "person__emailaddress__address__icontains",
    ]

    def label_from_instance(self, obj):
        return "{obj}".format(obj=obj)


###############################################################


class TimeslotWidget(ModelSelect2Widget):
    model = Timeslot
    queryset = Timeslot.objects.filter(active=True, scheduled=True)
    # NB: using __contains lookup on a date/time makes the lookup "fuzzy"
    #   i.e., doesn't have to be formatted as hh:mm or YYYY-MM-DD.
    search_fields = ["day", "start_time__contains"]

    def label_from_instance(self, obj):
        return obj.display()


###############################################################


class SectionSchedulingForm(forms.ModelForm):
    class Meta:
        model = DraftSection
        fields = ["course", "verbose_name", "semester", "instructor", "timeslot"]
        widgets = {
            "instructor": TeachingProfileWidget(
                attrs={"style": "width:200px;", "class": "instructor"}
            ),
            "timeslot": TimeslotWidget(
                attrs={"style": "width:200px;", "class": "timeslot"}
            ),
        }

    def __init__(self, *args, **kwargs):
        result = super().__init__(*args, **kwargs)
        instance = getattr(self, "instance", None)
        if instance and instance.id:
            self.fields["course"].widget.attrs["readonly"] = True
            self.fields["verbose_name"].widget.attrs["readonly"] = True
            self.fields["semester"].widget.attrs["readonly"] = True
        return result

    def _scrub_input(self, field):
        instance = getattr(self, "instance", None)
        if instance and instance.id:
            return getattr(instance, field)
        else:
            return self.cleaned_data.get(field)

    def clean_course(self):
        return self._scrub_input("course")

    def clean_verbose_name(self):
        return self._scrub_input("verbose_name")

    def clean_semester(self):
        return self._scrub_input("semester")


###############################################################


def get_draftsection_formset(
    form=SectionSchedulingForm, formset=forms.BaseInlineFormSet, **kwargs
):
    if "can_delete" not in kwargs:
        kwargs["can_delete"] = False
    if "extra" not in kwargs:
        kwargs["extra"] = 0
    return inlineformset_factory(
        DraftScheduleSession, DraftSection, form, formset, **kwargs
    )


###############################################################
