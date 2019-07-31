"""
Schedule initalization utilities.
"""
################################################################

import datetime

from classes.models import Section, Semester, Timeslot

from ... import conf
from ...models import DraftSection, SemesterTeachingPreference

################################################################


class AlreadyDone(RuntimeError):
    pass


################################################################


def _mirror_section(session, section, debug):
    if debug:
        print("considering section:", section)
    if not section.active:
        if debug:
            print("-> section not active")
        return False
    if not section.course.active:
        if debug:
            print("-> course not active")
        return False
    if not section.course.department.active:
        if debug:
            print("-> department not active")
        return False
    if not section.course.department.advertised:
        if debug:
            print("-> department not advertised")
        return False
    if section.section_type not in conf.get("valid_section_types"):
        if debug:
            print("-> section type", section.section_type, "is not okay")
        return False

    semester = section.term.term
    if semester not in [e[0] for e in SemesterTeachingPreference.SEMESTER_CHOICES]:
        if debug:
            print(
                "-> semester",
                semester,
                "not a valid choice",
                SemesterTeachingPreference.SEMESTER_CHOICES,
            )
        return False
    course = section.course
    instructor = None  # always start with blank instructors
    timeslot = section.sectionschedule_set.active().timeslot()
    if section.section_type == "on":
        timeslot = Timeslot.objects.Online()
    verbose_name = section.section_name

    obj, created = DraftSection.objects.get_or_create(
        verbose_name=verbose_name,
        course=course,
        session=session,
        semester=semester,
        defaults={"timeslot": timeslot, "instructor": instructor},
    )
    return created


################################################################


def from_classes_app(session, semester_list, debug):
    """
    Initalize the given ``session`` from the section data given
    by ``semester_list``.
    """
    if session.initialized:
        raise AlreadyDone("session already initialized")
    count = 0
    for semester in semester_list:
        for section in semester.section_set.all():
            if _mirror_section(session, section, debug):
                count += 1
    if count > 0:
        session.initialized = True
        session.save()
    # TODO: even/odd corrections
    return count


################################################################


def get_semester_list_2(section_qs):
    """
    Guess at the relevant semester queryset given by the ``session``.
    """
    return Semester.objects.filter(id__in=section_qs.values_list("term_id", flat=True))


################################################################


def from_classes_current(view_cls, session, debug=False):
    section_qs = session.current_actual_sections()
    semester_list = get_semester_list_2(section_qs)
    return from_classes_app(session, semester_list, debug)


################################################################


def from_classes_last_year(view_cls, session, debug=False):
    section_qs = session.prev_actual_sections()
    if debug:
        print("section count", section_qs.count())
    semester_list = get_semester_list_2(section_qs)
    if debug:
        print("semester list", semester_list)
    result = from_classes_app(session, semester_list, debug)
    if debug:
        print("result", result)
    return result


################################################################


def from_classes_two_years_ago(view_cls, session, debug=False):
    section_qs = session.two_years_ago_actual_sections()
    if debug:
        print("section count", section_qs.count())
    semester_list = get_semester_list_2(section_qs)
    if debug:
        print("semester list", semester_list)
    result = from_classes_app(session, semester_list, debug)
    if debug:
        print("result", result)
    return result


################################################################
