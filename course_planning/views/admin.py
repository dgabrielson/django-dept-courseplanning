"""
Admin views for the app.
"""
#######################################################################

import datetime

from django.views.generic.base import View
from django.views.generic.edit import FormView
from django.views.generic.list import ListView
from latex.djangoviews import LaTeXDetailView

from ..forms import StudentLoadReportForm
from ..mixins.cbv_admin import AdminSiteViewMixin
from ..models import DraftScheduleSession, SemesterTeachingPreference, TeachingProfile
from ..utils import semester_session_sort
from ..utils.print_timetable import latex_tabular_list
from .mixins import SessionFileViewMixin

#######################################################################


class AdminTeachingProfileReport(AdminSiteViewMixin, ListView):
    queryset = TeachingProfile.objects.filter(active=True).order_by("person")
    template_name = "admin/course_planning/teachingprofile/summary_report.html"


#######################################################################


class PrintTimetable(LaTeXDetailView):
    """
    A quick view timetable of all advertised section schedules
    for a given semester.
    """

    queryset = DraftScheduleSession.objects.filter(active=True)
    template_name = "course_planning/print/timetable.tex"
    as_attachment = False

    def get_context_data(self, *args, **kwargs):
        context = super(PrintTimetable, self).get_context_data(*args, **kwargs)

        draftsection_qs = self.object.draftsection_set.all().filter(active=True)
        term_set = set(draftsection_qs.values_list("semester", flat=True))
        term_display = dict(SemesterTeachingPreference.SEMESTER_CHOICES)
        term_list = []
        for t in semester_session_sort(term_set):
            term_section_qs = draftsection_qs.filter(semester=t)
            term_list.append(
                {
                    "term": term_display[t],
                    "tabular_list": latex_tabular_list(term_section_qs),
                }
            )
        context.update({"term_list": term_list})
        return context


#######################################################################


class AdminStudentLoadReport(AdminSiteViewMixin, SessionFileViewMixin, FormView):
    """
    This view generates the report.
    The view ``AdminStudentLoadReportDownloadView`` actually handles
    the download.
    """

    form_class = StudentLoadReportForm
    login_required = True
    template_name = (
        "admin/course_planning/teachingprofile/student_load_report_form.html"
    )
    session_prefix = "student-load-report"

    def get_initial(self):
        """
        Returns initial data for the form (a dictionary).
        """
        today = datetime.date.today()
        if today.month <= 8:
            start_year = today.year - 2
        else:
            start_year = today.year - 1

        start_date = datetime.date(start_year, 9, 1)
        end_date = datetime.date(start_year + 1, 8, 31)
        return dict(start_date=start_date, end_date=end_date)

    # def form_valid(self, form):
    #     """
    #     Define form valid, rather than a success url, because a valid
    #     form returns the spreadsheet.
    #     """
    #     return form.on_success()

    def get_success_url(self):
        # redirect to this url.
        return "."

    def form_valid(self, form):
        """
        If the form is valid, create responses
        """
        # stash generated data:
        basename = "student-load-report_%s" % datetime.date.today()
        format, data = form.response_data()
        self.set_session_result(basename, format, data)
        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        # is the download available?
        context["allow_download"] = self.has_session_result()
        return context


#######################################################################


class AdminStudentLoadReportDownloadView(
    AdminSiteViewMixin, SessionFileViewMixin, View
):
    session_prefix = "student-load-report"
    login_required = True

    def get(self, *args, **kwargs):
        return self.data_response(disposition_type="attachment")


#######################################################################
