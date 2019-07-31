"""
Admin classes for the  course_planning application
"""
#######################################################################
from __future__ import print_function, unicode_literals

from functools import partial

from django.conf.urls import url
from django.contrib import admin
from django.contrib.auth.decorators import permission_required
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.utils.html import format_html
from django.views.generic import TemplateView

from .forms import TeachingSurveyQuestionAdminForm
from .mixins.cbv_admin import ClassBasedViewsAdminMixin
from .models import (
    CourseInfo,
    CourseProgramInfo,
    CourseTeachingPreference,
    DraftScheduleSession,
    DraftSection,
    Program,
    SemesterTeachingPreference,
    TeachingProfile,
    TeachingSurveyAnswer,
    TeachingSurveyQuestion,
    TimeslotTeachingPreference,
)
from .schedule.views import (
    AdminAutoSchedule,
    AdminCourseDetailView,
    AdminInitializeFromCurrentCourseData,
    AdminInitializeFromPrevCourseData,
    AdminInitializeFromTwoYearsAgoCourseData,
    AdminScheduleView,
    AdminTeachingProfileDetailView,
    ajax,
)
from .views.admin import (
    AdminStudentLoadReport,
    AdminStudentLoadReportDownloadView,
    AdminTeachingProfileReport,
    PrintTimetable,
)

# adaptive use of admin_export:
try:
    import admin_export
except ImportError:
    admin_export = None

#######################################################################


class CourseProgramInfoInline(admin.TabularInline):
    model = CourseProgramInfo
    extra = 0
    list_select_related = True
    autocomplete_fields = ["course"]


#######################################################################


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    inlines = [CourseProgramInfoInline]
    list_display = ["verbose_name", "slug", "public", "ordering", "scheduled"]
    list_filter = ["active", "public", "scheduled", "modified", "created"]
    save_on_top = True


#######################################################################


@admin.register(CourseInfo)
class CourseInfoAdmin(admin.ModelAdmin):
    autocomplete_fields = ["course"]
    inlines = [CourseProgramInfoInline]
    list_display = ["course", "has_lab", "fall", "winter", "summer", "runs"]
    list_editable = ["has_lab", "fall", "winter", "summer", "runs"]
    list_filter = ["active", "has_lab", "fall", "winter", "summer", "runs"]
    list_select_related = True
    save_on_top = True
    search_fields = ["course__department__code", "course__code", "course__name"]


#######################################################################


@admin.register(CourseProgramInfo)
class CourseProgramInfoAdmin(admin.ModelAdmin):
    list_display = ["course", "program", "usual_year"]
    list_editable = ["program", "usual_year"]
    list_filter = ["active", "program", "usual_year"]
    save_on_top = True
    search_fields = [
        "course__course__department__code",
        "course__course__code",
        "course__course__name",
    ]


#######################################################################


class CourseTeachingPreferenceInline(admin.TabularInline):
    model = CourseTeachingPreference
    extra = 0


#######################################################################


class TimeslotTeachingPreferenceInline(admin.TabularInline):
    model = TimeslotTeachingPreference
    extra = 0


#######################################################################


class SemesterTeachingPreferenceInline(admin.TabularInline):
    model = SemesterTeachingPreference
    extra = 0


#######################################################################


class TeachingSurveyAnswerInline(admin.TabularInline):
    model = TeachingSurveyAnswer
    readonly_fields = ["question", "profile"]
    extra = 0


#######################################################################


@admin.register(TeachingProfile)
class TeachingProfileAdmin(admin.ModelAdmin):
    autocomplete_fields = ["person"]
    inlines = [
        CourseTeachingPreferenceInline,
        TimeslotTeachingPreferenceInline,
        SemesterTeachingPreferenceInline,
        TeachingSurveyAnswerInline,
    ]
    list_display = [
        "person",
        "agreed_load",
        "last_reviewed",
        "preference_same_day",
        "preference_no_back_to_back",
    ]
    ordering = ["person"]
    readonly_fields = ["last_reviewed"]
    save_on_top = True
    search_fields = ["person__cn", "person__username", "person__emailaddress__address"]

    def get_urls(self):
        """
        Extend the admin urls for this model.
        Provide a link by subclassing the admin change_form,
        and adding to the object-tools block.
        """
        urls = super().get_urls()
        urls = [
            url(
                r"^summary-report/$",
                self.admin_site.admin_view(AdminTeachingProfileReport.as_view()),
                name="teachingprofile_summary",
                kwargs={"admin_options": self},
            ),
            url(
                r"^student-load-report/$",
                self.admin_site.admin_view(AdminStudentLoadReport.as_view()),
                name="teachingprofile_student_load_report",
                kwargs={"admin_options": self},
            ),
            url(
                r"^student-load-report/download/$",
                self.admin_site.admin_view(
                    AdminStudentLoadReportDownloadView.as_view()
                ),
                name="teachingprofile_student_load_report_download",
                kwargs={"admin_options": self},
            ),
        ] + urls
        return urls


#######################################################################


@admin.register(TeachingSurveyQuestion)
class TeachingSurveyQuestionAdmin(admin.ModelAdmin):
    inlines = [TeachingSurveyAnswerInline]
    form = TeachingSurveyQuestionAdminForm
    list_display = ["question", "active"]


#######################################################################


class HelpAdminView(TemplateView):
    pass


class DraftScheduleHelpAdminView(HelpAdminView):
    template_name = "admin/course_planning/draftschedulesession/howto.html"


@admin.register(DraftScheduleSession)
class DraftScheduleSessionAdmin(ClassBasedViewsAdminMixin, admin.ModelAdmin):
    actions = ["spreadsheet_export_action", "csv_export_action"]
    list_display = ["verbose_name", "start_date", "end_date", "changelist_buttons"]
    readonly_fields = ["initialized"]

    def changelist_buttons(self, obj):
        if obj.pk:
            return format_html(
                '<a class="button" href="{}">Worksheet</a>&nbsp;'
                '<a class="button" href="{}">Export spreadsheet</a>&nbsp;'
                '<a class="button" href="{}">Print timetable</a>',
                reverse("admin:draftschedulesession_worksheet", kwargs={"pk": obj.pk}),
                reverse(
                    "admin:draftschedulesession_export_spreadsheet",
                    kwargs={"pk": obj.pk},
                ),
                reverse(
                    "admin:draftschedulesession_export_print_timetable",
                    kwargs={"pk": obj.pk},
                ),
            )
        return ""

    changelist_buttons.short_description = "Actions"
    changelist_buttons.allow_tags = True

    def get_actions(self, request):
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            del actions["delete_selected"]
        if admin_export is None:
            del actions["spreadsheet_export_action"]
            del actions["csv_export_action"]
        else:
            # remove the admin_export default export actions:
            if "export_redirect_spreadsheet_xlsx" in actions:
                del actions["export_redirect_spreadsheet_xlsx"]
            if "export_redirect_spreadsheet_csv" in actions:
                del actions["export_redirect_spreadsheet_csv"]
        return actions

    def get_urls(self):
        """
        Extend the admin urls for this model.
        Provide a link by subclassing the admin change_form,
        and adding to the object-tools block.
        """
        urls = super().get_urls()
        urls = [
            url(
                r"^howto/$",
                self.admin_site.admin_view(
                    permission_required("course_planning.change_draftschedulesession")(
                        self.cb_changeform_view
                    )
                ),
                kwargs={
                    "view_class": DraftScheduleHelpAdminView,
                    "title": "Using the scheduler",
                    "add": False,
                    "original": "How to",
                },
                name="course_planning_draftschedulesession_howto",
            ),
            url(
                r"^_save_section/$",
                self.admin_site.admin_view(ajax.save_section),
                name="draftschedulesession_ajax_save_section",
            ),
            url(
                r"^_load_section_extra/$",
                self.admin_site.admin_view(ajax.load_section_extra),
                name="draftschedulesession_ajax_load_section_extra",
            ),
            url(
                r"^_get_instructor_loads/$",
                self.admin_site.admin_view(ajax.get_instructor_loads),
                name="draftschedulesession_ajax_get_instructor_loads",
            ),
            url(
                r"^course-info/(?P<slug>.+)/$",
                self.admin_site.admin_view(AdminCourseDetailView.as_view()),
                name="draftschedulesession_course_info",
                kwargs={"admin_options": self},
            ),
            url(
                r"^(?P<session_id>.+)/instructor-info/(?P<pk>.+)/$",
                self.admin_site.admin_view(AdminTeachingProfileDetailView.as_view()),
                name="draftschedulesession_instructor_info",
                kwargs={"admin_options": self},
            ),
            url(
                r"^(?P<pk>.+)/init-current/$",
                self.admin_site.admin_view(
                    AdminInitializeFromCurrentCourseData.as_view()
                ),
                name="draftschedulesession_init_current",
                kwargs={"admin_options": self},
            ),
            url(
                r"^(?P<pk>.+)/init-prev/$",
                self.admin_site.admin_view(AdminInitializeFromPrevCourseData.as_view()),
                name="draftschedulesession_init_prev",
                kwargs={"admin_options": self},
            ),
            url(
                r"^(?P<pk>.+)/init-two-years-ago/$",
                self.admin_site.admin_view(
                    AdminInitializeFromTwoYearsAgoCourseData.as_view()
                ),
                name="draftschedulesession_init_twoyears",
                kwargs={"admin_options": self},
            ),
            url(
                r"^(?P<pk>.+)/auto-schedule/$",
                self.admin_site.admin_view(AdminAutoSchedule.as_view()),
                name="draftschedulesession_auto_schedule",
                kwargs={"admin_options": self},
            ),
            url(
                r"^(?P<pk>.+)/schedule-worksheet/$",
                self.admin_site.admin_view(AdminScheduleView.as_view()),
                name="draftschedulesession_worksheet",
                kwargs={"admin_options": self},
            ),
            url(
                r"^(?P<pk>.+)/export/spreadsheet/$",
                self.admin_site.admin_view(self.export_view),
                name="draftschedulesession_export_spreadsheet",
                kwargs={"format_": "xlsx"},
            ),
            url(
                r"^(?P<pk>.+)/export/csv/$",
                self.admin_site.admin_view(self.export_view),
                name="draftschedulesession_export_spreadsheet",
                kwargs={"format_": "csv"},
            ),
            url(
                r"^(?P<pk>.+)/timetable/print/$",
                self.admin_site.admin_view(PrintTimetable.as_view()),
                name="draftschedulesession_export_print_timetable",
            ),
        ] + urls
        return urls

    def export_action(self, request, queryset, format_):
        """
        Redirect to the actual view.
        """
        url = reverse_lazy("admin_export_spreadsheet")
        pk_list = (
            DraftSection.objects.filter(session__in=queryset, active=True)
            .values_list("pk", flat=True)
            .distinct()
        )
        query = "&".join(["pk={0}".format(s) for s in pk_list])
        if format_ is None:
            format_ = request.POST.get("format", None)
        if format_ is None:
            format_ = request.GET.get("format", None)
        if format_ is None:
            format_ = "xlsx"
        query += "&format=" + format_
        ct = ContentType.objects.get_for_model(DraftSection)
        query += "&contenttype={0}".format(ct.pk)
        return HttpResponseRedirect(url + "?" + query)

    def spreadsheet_export_action(self, request, queryset):
        return self.export_action(request, queryset, format_="xlsx")

    spreadsheet_export_action.short_description = "Export schedule to XLSX spreadsheet"

    def csv_export_action(self, request, queryset):
        return self.export_action(request, queryset, format_="csv")

    csv_export_action.short_description = "Export schedule to CSV spreadsheet"

    def export_view(self, request, pk, format_=None):
        queryset = DraftScheduleSession.objects.filter(pk=pk)
        return self.export_action(request, queryset, format_=format_)


#######################################################################


@admin.register(DraftSection)
class DraftSectionAdmin(admin.ModelAdmin):
    actions = ["clear_instructor"]
    list_display = ["__str__", "session", "semester", "instructor", "timeslot"]
    list_filter = ["session", "semester"]
    ordering = ["session", "-semester", "course", "verbose_name"]

    def clear_instructor(self, request, queryset):
        queryset.update(instructor=None)

    clear_instructor.short_description = (
        "Clear the instructor from the selected section(s)"
    )

    def move_semester(self, request, queryset, value):
        queryset.update(semester=value)


# A bit of dynamic method generation and class manipulation.
for code, name in SemesterTeachingPreference.SEMESTER_CHOICES:
    action = "move_semester_{}".format(name.lower().replace(" ", "_"))
    f = partial(DraftSectionAdmin.move_semester, value=code)
    f.short_description = "Move selected section(s) to " + name
    f.__name__ = action
    setattr(DraftSectionAdmin, action, f)
    if action not in DraftSectionAdmin.actions:
        DraftSectionAdmin.actions.append(action)

#######################################################################
#######################################################################
