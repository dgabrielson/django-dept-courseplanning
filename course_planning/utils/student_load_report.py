#######################################################################

import datetime
import operator
from functools import reduce  # Python 3
from itertools import chain, repeat

from classes.models import Enrollment, Section, Semester
from django.db.models import Avg, Q
from spreadsheet import sheetWriter

from .. import conf

#######################################################################


def _undergraduate_section_filter(queryset):
    """
    This should probably be configurable, since it's how we do things here.
    """
    query = reduce(
        operator.or_, [Q(course__code__startswith=str(i)) for i in range(1, 5)]
    )
    return queryset.filter(query, section_type__in=conf.get("valid_section_types"))


#######################################################################


def _do_section_data(section):
    """
    Return the lastest, estimated_average numbers for the enrollments
    of this section.
    """
    try:
        latest_enrol = section.enrollment_set.latest().registration
    except Enrollment.DoesNotExist:
        latest_enrol = None
    dr = list(section.sectionschedule_set.date_range())
    dr[0] += datetime.timedelta(days=3 * 7)
    dr[1] -= datetime.timedelta(days=3 * 7)
    aggr_data = section.enrollment_set.filter(created__date__range=dr).aggregate(
        est_avg=Avg("registration")
    )
    est_avg = aggr_data.get("est_avg", None)
    if est_avg is not None:
        est_avg = int(round(est_avg))
    return latest_enrol, est_avg


#######################################################################


def _do_term_data(term, old_data):
    term_data = {}
    section_qs = term.section_set.active()
    section_qs = section_qs.filter(course__department__advertised=True)
    section_qs = section_qs.filter(instructor__teachingprofile__active=True)
    section_qs = _undergraduate_section_filter(section_qs)
    for section in section_qs:
        final, est_avg = _do_section_data(section)
        if section.instructor_id not in term_data:
            term_data[section.instructor_id] = {}
        if final is not None:
            if "final" not in term_data[section.instructor_id]:
                term_data[section.instructor_id]["final"] = 0
            term_data[section.instructor_id]["final"] += final
            if "section_count" not in term_data[section.instructor_id]:
                term_data[section.instructor_id]["section_count"] = 0
            term_data[section.instructor_id]["section_count"] += 1
        if est_avg is not None:
            if "est_avg" not in term_data[section.instructor_id]:
                term_data[section.instructor_id]["est_avg"] = 0
            term_data[section.instructor_id]["est_avg"] += est_avg
    for instr_id in term_data:
        if instr_id not in old_data:
            old_data[instr_id] = {}
        old_data[instr_id][term.pk] = term_data[instr_id]
    return old_data


#######################################################################


def _format_data(data):
    table = []
    # headers:
    term_list = data.get("terms", [])
    term_row = [""] + list(chain.from_iterable(repeat(str(e), 2) for e in term_list))
    table.append(term_row)
    count_row = [""] + ["average", "final"] * len(term_list)
    table.append(count_row)
    for profile in data.get("teachingprofiles", []):
        row = [str(profile.person)]
        profile_data = data.get(profile.person_id, None)
        if profile_data is not None:
            for term in term_list:
                term_data = profile_data.get(term.pk, {})
                final = term_data.get("final", None)
                est_avg = term_data.get("est_avg", None)
                section_count = term_data.get("section_count", None)  # unused
                if final is None:
                    final = ""
                if est_avg is None:
                    est_avg = ""
                row.append(est_avg)
                row.append(final)
        table.append(row)
    return table


#######################################################################


def make_student_load_report(start_date, end_date, format_):
    """
    Given a start_date, end_date, and file format, return the data stream
    for a spreadsheet.
    """
    from ..models import TeachingProfile

    current_term = Semester.objects.get_by_date(start_date)
    finish_term = Semester.objects.get_by_date(end_date)
    data = {
        "terms": [],
        "teachingprofiles": TeachingProfile.objects.filter(active=True),
    }
    while True:
        data = _do_term_data(current_term, data)
        data["terms"].append(current_term)
        if current_term == finish_term:
            break
        current_term = current_term.get_next()

    table = _format_data(data)
    return sheetWriter(table, format_)


#######################################################################
