#######################################################################

from itertools import combinations

from .student_load_report import make_student_load_report

#######################################################################


def _timeslots_adjacent(t1, t2, near_minutes):
    # check days:
    if not (t1.day in t2.day or t2.day in t1.day):
        return False
    # WLOG, t1 starts first:
    if t2.start_time < t1.start_time:
        t1, t2 = t2, t1
    return (
        t1.stop_time.hour * 60 + t1.stop_time.minute + 45
        > t2.start_time.hour * 60 + t2.start_time.minute
    )


#######################################################################


def has_adjacent_timeslots(timeslot_list, near_minutes=None):
    """
    For every pair of timeslots in timeslot list, determine
    if any of them are adjancent (including overlap.)
    """
    if near_minutes is None:
        near_minutes = 45
    for t1, t2 in combinations(timeslot_list, 2):
        if _timeslots_adjacent(t1, t2, near_minutes):
            return True
    return False


#######################################################################


def preference_by_course(course, min_score=0):
    """
    Return a list of teaching profiles, score pairs that would prefer this course.
    """
    return (
        course.courseteachingpreference_set.filter(active=True)
        .exclude(score__lt=min_score)
        .order_by("-score", "profile")
    )


#######################################################################


def semester_annual_sort(semester_list):
    """
    The default ordering for semesters is by the calendar year.
    """
    return list(sorted(semester_list))


#######################################################################


def semester_session_sort(semester_list):
    """
    Session sort begins with Fall term.
    """
    l = list(sorted(semester_list))
    if l[-1] == "3":
        l.insert(0, l.pop(-1))
    return l


#######################################################################
