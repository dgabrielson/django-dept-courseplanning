"""
Utilities for generating a printable timetable of classes.
See django-dept-classes:classes/utils/print_timetable.py
"""
###############################################################
#######################
from __future__ import print_function, unicode_literals

import datetime
from itertools import chain, groupby

from people.models import Person

#######################

###############################################################


def preliminary_table(draftsection_qs):
    # construct preliminary timetable
    timetable = {}
    for timeslot, items in groupby(draftsection_qs, lambda e: e.timeslot):
        litems = list(items)
        for day in timeslot.day:
            if day not in "MTWRF":
                continue
            if day not in timetable:
                timetable[day] = {}
            if timeslot.start_time not in timetable[day]:
                timetable[day][timeslot.start_time] = []
            timetable[day][timeslot.start_time] += litems
    return timetable


###############################################################


def _instructor_abbrev_map(draftsection_qs):
    # map instructors to name abbreviations

    def auto_abbreviate(name, n=1):
        if name is None:
            return ""
        parts = name.split()
        first_parts = "".join([p[0] for p in parts[:-1]])
        last_part = parts[-1][:n]
        return first_parts + last_part

    instr_pks = set(
        draftsection_qs.exclude(instructor__isnull=True).values_list(
            "instructor__person_id", flat=True
        )
    )
    instructor_qs = Person.objects.filter(pk__in=instr_pks).distinct()

    name_map = {}
    collision_map = {}
    instr_map = {}
    for instr in instructor_qs:
        instr_map[instr.pk] = instr
        abbr = instr.personkeyvalue_set.lookup("initials")
        if abbr is None:
            abbr = auto_abbreviate(instr.cn, 1)
            collision_map[instr.pk] = True
        else:
            abbr = abbr.value
            collision_map[instr.pk] = None
        name_map[instr.pk] = abbr

    # collision check...
    def _collision_check(name_map, collision_map):
        value_list = list(name_map.values())
        for key, value in name_map.items():
            count = value_list.count(value)
            if count == 1:
                collision_map[key] = None
            else:
                collision_map[key] = [k for k, v in name_map.items() if v == value]

    _collision_check(name_map, collision_map)

    # first fix: auto_abbreviate(..., 2)
    for key, value in collision_map.items():
        if value is not None:
            for pk in value:
                instr = instr_map[pk]
                name_map[pk] = auto_abbreviate(instr.cn, 2)

    _collision_check(name_map, collision_map)

    # second fix: numbers.
    key_done = []
    for key, value in collision_map.items():
        if key in key_done:
            continue
        if value is not None:
            n = 1
            for count, pk in enumerate(value, 1):
                name_map[pk] += "{}".format(count)
                key_done.append(pk)

    # final check: there should be no collisions here...
    _collision_check(name_map, collision_map)
    assert not any([v for k, v in collision_map.items()]), "still have collisions"
    return name_map


###############################################################


def _format_multisection(schedule, name_map, draftsection_qs):
    result = schedule.course.code
    if (
        len(
            set(
                draftsection_qs.filter(course=schedule.course).values_list(
                    "verbose_name", flat=True
                )
            )
        )
        > 1
    ):
        result += " " + schedule.verbose_name
    abbrev = (
        name_map.get(schedule.instructor.person_id, None)
        if schedule.instructor is not None
        else None
    )
    if abbrev:
        result += ": " + abbrev
    return result


###############################################################


def _collapse_timeslot(draftsection_qs, name_map, schedule_qs):
    results = []
    seen = set()
    # collapse cross numbered courses -- same location, same instructor
    # HERE we make NO assumptions about crosslisting -- these are drafts
    # collapse section names -- if there is more than one section, keep section_name; else just course name
    for sched in draftsection_qs:
        if sched in seen:
            continue
        results.append(_format_multisection(sched, name_map, schedule_qs))
        seen.add(sched)
    return sorted(results)


###############################################################


def _initial_display_table(timetable, name_map, draftsection_qs):
    # construct display timetable:
    display_timetable = {}
    for day in timetable:
        display_timetable[day] = {}
        for time in timetable[day]:
            display_timetable[day][time] = _collapse_timeslot(
                timetable[day][time], name_map, draftsection_qs
            )
    return display_timetable


###############################################################


def latex_time_formatter(t):
    return "\\cellformat{{{0}}}".format(t.strftime("%H:%M").lstrip("0"))


def _display_timetable(timetable, time_formatter=None):
    # display timetable is column oriented (column major order);
    # need to convert to LaTeX/tabular (row major order).
    M = 0

    # make sure we have at least the five weekdays in the timetable:
    for day in "MTWRF":
        i = 0
        if day not in timetable:
            timetable[day] = {}

    # construct strictly ordered sequence of times; ``timetable[day]``
    times = sorted(list(set(sum([list(timetable[day]) for day in timetable], []))))
    times_by_day = {day: sorted(list(timetable[day])) for day in timetable}
    t_idx_map = {t: i for i, t in enumerate(times)}
    # grid max determines the maximum number of lines for each time.
    grid_max = {}
    for t in times:
        grid_max[t] = max((len(timetable.get(d, {}).get(t, [])) for d in timetable))
        # print(t, grid_max[t])

    # determine actual index of each time over all days.
    # Maximally sized blocks
    # Not the best algorithm, but this will at least keep
    # any courses from getting clobbered.

    for idx, t in enumerate(times):
        # does the next time occur on any of the same days as this time?
        next_time = times[idx + 1] if idx + 1 < len(times) else None
        if next_time is not None:
            t_idx_map[next_time] = max([t_idx_map[t] + grid_max[t], t_idx_map[t]]) + 1

    # # more compact, but could be better.
    # for idx, t in enumerate(times):
    #     nt = times[idx+1] if idx+1 < len(times) else None
    #     ntd = None
    #     for day in "MTWRF":
    #         # does the next time occur on any of the same days as this time?
    #         day_times = times_by_day[day]
    #         t_idx = day_times.index(t) if t in day_times else len(day_times)
    #         ntd_maybe = day_times[t_idx+1] if t_idx+1 < len(day_times) else None
    #         if ntd_maybe is not None and (ntd is None or ntd > ntd_maybe):
    #             ntd = ntd_maybe
    #     if ntd is not None:
    #         t_idx_map[ntd] = t_idx_map[t] + grid_max[t] + 1 #max([t_idx_map[t] + grid_max[t] + 1, t_idx_map[ntd]])
    #         if ntd == nt:
    #             nto = times[idx+2] if idx+2 < len(times) else None
    #             if nto is not None:
    #                 t_idx_map[nto] = t_idx_map[ntd]+1 #max(t_idx_map[ntd]+1, t_idx_map[nto])
    #     if nt is not None and nt != ntd:
    #         # The next time does not happen today.
    #         t_idx_map[nt] = max(t_idx_map[t] + 1, t_idx_map[nt])

    # make spots for worst case layout all times every day:
    day_length = {}
    for day in timetable:
        daytimes = sorted(list(timetable[day]))
        last_time = daytimes[-1]
        day_length[day] = t_idx_map[last_time] + len(timetable[day][last_time])

    M = max(day_length.values()) + 1

    tabular = []
    for day in "MTWRF":
        tabular.append([])
        for i in range(M):
            tabular[-1].append("")
        i = 0
        for t in sorted(timetable[day].keys()):
            # pad to time_idx
            i = t_idx_map[t]
            tabular[-1][i] = time_formatter(t) if time_formatter is not None else t
            # if day == 'M':
            #     print(i, tabular[-1][i])
            i += 1
            for course in timetable[day][t]:
                tabular[-1][i] = course
                # if day == 'M':
                #     print(i, course)
                i += 1

    tabular_t = []
    for j in range(M):
        tabular_t.append([])
        for i in range(5):
            tabular_t[-1].append(tabular[i][j])

    return tabular_t


###############################################################


def timetable(draftsection_qs, time_formatter=None):
    """
    Generate the timetable for a semester.
    Lots of assumptions here....
    """
    qs = draftsection_qs.exclude(timeslot__isnull=True)
    t1 = preliminary_table(qs)
    name_map = _instructor_abbrev_map(qs)
    t2 = _initial_display_table(t1, name_map, qs)
    t3 = _display_timetable(t2, time_formatter=time_formatter)
    return t3


###############################################################


def latex_tabular_list(draftsection_qs):
    return timetable(draftsection_qs, time_formatter=latex_time_formatter)


###############################################################
