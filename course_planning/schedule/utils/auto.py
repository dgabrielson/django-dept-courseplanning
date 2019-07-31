"""
Automated scheduling utilities.
"""
################################################################

from random import random

from classes.models import Timeslot
from django.db.models import Count

from ...models import (
    CourseTeachingPreference,
    SemesterTeachingPreference,
    TeachingProfile,
    TimeslotTeachingPreference,
)
from .imsvm import ImsvmRefuse, imsvm

################################################################

SEMESTER_LIST = [e[0] for e in SemesterTeachingPreference.SEMESTER_CHOICES]

################################################################


def main(session):
    """
    Do a schedule.
    - Only attempt to slot instructors into place if the current
        instructor is None (unset)
    -
    """
    instructor_data = {}
    imsvm_refusal = {s: False for s in SEMESTER_LIST}
    while True:
        section_qs, instructor_data = _remove_scheduled(session)
        if not section_qs.exists():
            break
        if not instructor_data:
            break
        if all(imsvm_refusal.values()):
            break
        for semester in SEMESTER_LIST:
            semester_section_qs = section_qs.filter(semester=semester)
            semester_section_qs = _remove_timeslot_conflicts(semester_section_qs)
            # TODO: do semester_section_qs in program order groups.
            ranking_matrix, person_list, section_list = _build_ranking_matrix(
                semester, semester_section_qs, instructor_data
            )
            try:
                matches = imsvm(ranking_matrix, rank_threshold=0.5)
            except ImsvmRefuse:
                imsvm_refusal[semester] = True
                continue
            if not matches:
                imsvm_refusal[semester] = True
            for person_idx, section_idx in matches:
                person = person_list[person_idx]
                section = section_list[section_idx]
                section.instructor = person
                section.save()
    return instructor_data


################################################################


def _init_instructor_data():
    """
    Construct initial instructor data map
    """
    qs = TeachingProfile.objects.filter(active=True)
    semesterprefs_qs = SemesterTeachingPreference.objects.filter(active=True)
    values_qs = qs.values(
        "pk", "agreed_load", "preference_same_day", "preference_no_back_to_back"
    )
    results = {v["pk"]: v for v in values_qs}
    for pk in results:
        semesterprefs_local = semesterprefs_qs.filter(profile_id=pk)
        semesterprefs_list = list(
            semesterprefs_local.values("semester", "preferred_load")
        )
        results[pk]["term_load"] = {
            v["semester"]: v["preferred_load"] for v in semesterprefs_list
        }
        results[pk]["remaining_load"] = results[pk]["agreed_load"]
        results[pk]["remaining_term_load"] = results[pk]["term_load"].copy()
        results[pk]["occupied_timeslots"] = {
            v["semester"]: [] for v in semesterprefs_list
        }
    return results


################################################################


def _remove_scheduled(session):
    """
    Remove those sections which already have instructors
    Do a full count of remaining instructor loads, and return this.
    If an instructor is at their load, do not include them.
    """
    qs = session.draftsection_set.filter(active=True)
    instructor_data = _init_instructor_data()
    # update instructor data
    instr_section_qs = qs.filter(instructor__isnull=False)
    profile_pks = set(instr_section_qs.values_list("instructor_id", flat=True))
    for pk in profile_pks:
        instr_sections = instr_section_qs.filter(instructor_id=pk)
        # print(instr_sections)
        instr_data = instructor_data[pk]
        for section in instr_sections:
            # print(section)
            instr_data["remaining_load"] -= 1
            semester = section.semester
            if section.timeslot:
                instr_data["occupied_timeslots"][semester].append(section.timeslot_id)
            instr_data["remaining_term_load"][semester] -= 1
        if instr_data["remaining_load"] <= 0:
            instructor_data.pop(pk)
    return qs.filter(instructor__isnull=True), instructor_data


################################################################


def _remove_timeslot_conflicts(section_qs):
    """
    From the section_qs only; remove any conflicting timeslots
    - find duplicate timeslots, only keep one section for each.
    """
    used_timeslots = set(section_qs.values_list("timeslot_id", flat=True))
    qs = Timeslot.objects.filter(
        active=True, scheduled=True, pk__in=used_timeslots
    ).annotate(section_count=Count("draftsection"))
    qs_one = qs.filter(section_count=1)
    qs_multiple = qs.filter(section_count__gte=2)
    # The annotations get a bit confused using the indirect backwards relation on the above filtered querysets...
    sections = list(
        qs.filter(pk__in=qs_one.values_list("pk", flat=True)).values_list(
            "draftsection", flat=True
        )
    )
    for timeslot_id in qs_multiple.values_list("pk", flat=True):
        pk = (
            section_qs.filter(timeslot_id=timeslot_id)
            .order_by("-course")
            .values_list("pk", flat=True)[0]
        )
        sections.append(pk)
    return section_qs.filter(pk__in=sections)


################################################################


def _build_ranking_matrix(semester, section_qs, instructor_data):
    """
    At this point the section_qs will have only unique timeslots,
    and instructors that are at their load have been removed
    from instructor_data.  Their load for the current term
    may be ≤ 0 however.

    Each row of the ranking matrix is the instructors preference vector
    for the sections given.

    The ``semester`` value is given purely as a shortcut, since it's
    predetermined.
    """
    section_list = list(section_qs)
    course_timeslots = [(s.course_id, s.timeslot_id) for s in section_list]
    rankings = []
    profile_list = list(TeachingProfile.objects.filter(pk__in=instructor_data))

    for profile in profile_list:
        course_prefs = dict(
            CourseTeachingPreference.objects.filter(
                active=True, profile=profile
            ).values_list("course_id", "score")
        )
        timeslots_prefs = dict(
            TimeslotTeachingPreference.objects.filter(
                active=True, profile=profile
            ).values_list("timeslot_id", "score")
        )
        row = []
        instr_data = instructor_data[profile.pk]
        t_weight = 1
        if instr_data["remaining_term_load"][semester] <= 0:
            t_weight = 0
        if 0 < instr_data["remaining_term_load"][semester] < 1:
            t_weight = int(random() > instr_data["remaining_term_load"][semester])
        for course_id, timeslot_id in course_timeslots:
            c_score = course_prefs.get(course_id, 0)
            if timeslot_id in instr_data["occupied_timeslots"][semester]:
                t_score = 0
            else:
                t_score = timeslots_prefs.get(timeslot_id, 0)
                t_score *= t_weight
                # TODO: test adjacent timeslots for preference_no_back_to_back
                # TODO: test days of timeslots for preference_same_day
            section_score = c_score * (t_score * c_score + random())
            row.append(section_score)
        rankings.append(row)
    return rankings, profile_list, section_list


################################################################
