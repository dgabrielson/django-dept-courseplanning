"""
Ajax endpoint views for scheduling.
"""
###############################################################

from django.http import Http404, JsonResponse

from ...models import DraftScheduleSession, DraftSection, TeachingProfile

###############################################################


class JsonError(Exception):
    def __init__(self, status, data=None):
        self.status = status
        if data is None:
            data = {}
        if not "status" in data:
            data["status"] = False
        if not "message" in data:
            data["message"] = "exception"

        self.data = data

    def as_response(self):
        return JsonResponse(status=self.status, data=self.data)


###############################################################


def _ensure_method(request, method):

    if request.method != method.upper():
        raise JsonError(400, {"message": "method not supported"})


###############################################################


def _load_object(request, model, pk_param):
    pk = request.POST.get(pk_param, None)
    if pk is None:
        raise JsonError(status=400, data={"message": "Invalid request"})
    try:
        obj = model.objects.get(pk=pk)
    except model.DoesNotExist:
        raise JsonError(status=404, data={"message": "Object not found"})
    return obj


###############################################################


def _build_notes(section):
    total_load, term_loads = section.instructor.get_remaining_loads(section.session)
    semester_load = term_loads.get(section.semester, 0)
    back_to_back = section.instructor.has_back_to_back(
        section.session, section.semester
    )
    has_different_days = section.instructor.has_different_days(
        section.session, section.semester
    )
    timeslot_conflicts = section.instructor.get_timeslot_conflicts(
        section.session, section.semester
    )
    notes = ""
    # Notes:
    #   - Timeslot conflict
    if timeslot_conflicts:
        notes += "Timeslot conflict. "
        # data['timeslot_conflicts'] = timeslot_conflicts
    #   - Total load at/over cap
    if total_load < 0:
        notes += "Over total load. "
    #   - Term load at/over cap
    if semester_load < -0.5:
        notes += "Over term load. "
    #   - Back to back teaching (vs prefs)
    if back_to_back:
        notes += "Back to back. "
    #   - Multi day teaching (vs prefs)
    if has_different_days:
        notes += "Has different days. "
    return notes, timeslot_conflicts, total_load, term_loads


###############################################################


def _build_additional_sections(section, old_instr_id, old_timeslot_id):
    """
    During a save action, we need to indicate what else needs to be updated
    """
    section_qs = section.session.draftsection_set.filter(active=True).exclude(
        pk=section.pk
    )
    results = []
    if section.instructor_id != old_instr_id:
        # update old instructor, if any
        if old_instr_id is not None:
            results += list(
                section_qs.filter(instructor_id=old_instr_id).values_list(
                    "pk", flat=True
                )
            )
        # update new instructor
        if section.instructor_id is not None:
            results += list(
                section_qs.filter(instructor_id=section.instructor_id).values_list(
                    "pk", flat=True
                )
            )
    if section.timeslot_id != old_timeslot_id:
        # update old timeslots
        if old_timeslot_id is not None:
            results += list(
                section_qs.filter(timeslot_id=old_timeslot_id).values_list(
                    "pk", flat=True
                )
            )
        # update new timeslots
        if section.timeslot_id is not None:
            results += list(
                section_qs.filter(timeslot_id=section.timeslot_id).values_list(
                    "pk", flat=True
                )
            )

    return list(set(results))


###############################################################


def load_section_extra(request, section=None, old_instr_id=None, old_timeslot_id=None):
    try:
        _ensure_method(request, "POST")
        from_save = section is not None
        if section is None:
            try:
                section = _load_object(request, DraftSection, "section_pk")
            except JsonError as e:
                return e.as_response()

        data = {
            "status": True,
            "message": "",
            "score": "",
            "notes": "",
            "section_id": section.pk,
            "timeslot_conflicts": None,
            "additional_sections": [],
            "remaining_load": None,
            "remaining_term_loads": None,
            "instructor_id": None,
        }
        if section.instructor is not None and section.timeslot is not None:
            data["score"] = section.instructor.get_score(
                section.course_id, section.timeslot_id
            )
        if old_instr_id is not None:
            data["old_instructor_id"] = old_instr_id
        if section.instructor is not None:
            data["instructor_id"] = section.instructor_id
            n, tc, rl, tl = _build_notes(section)
            data["notes"] = n
            data["timeslot_conflicts"] = tc
            data["remaining_load"] = rl
            data["remaining_term_loads"] = tl.get("display", None)
        if from_save:
            data["additional_sections"] = _build_additional_sections(
                section, old_instr_id, old_timeslot_id
            )

        return JsonResponse(data)
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise e


###############################################################


def save_section(request):
    try:
        _ensure_method(request, "POST")
        try:
            section = _load_object(request, DraftSection, "section_pk")
        except JsonError as e:
            return e.as_response()

        timeslot_pk = request.POST.get("timeslot_pk", None)
        if not timeslot_pk:
            timeslot_pk = None
        instructor_pk = request.POST.get("instructor_pk", None)
        if not instructor_pk:
            instructor_pk = None

        old_instr_id = section.instructor_id
        section.instructor_id = instructor_pk
        old_timeslot_id = section.timeslot_id
        section.timeslot_id = timeslot_pk
        section.save()

        return load_section_extra(request, section, old_instr_id, old_timeslot_id)
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise e


###############################################################


def get_instructor_loads(request):
    try:
        _ensure_method(request, "POST")
        instructor = _load_object(request, TeachingProfile, "instructor_id")
        session = _load_object(request, DraftScheduleSession, "session_id")
        rl, tl = instructor.get_remaining_loads(session)
        data = {"instructor_id": instructor.pk}
        data["remaining_load"] = rl
        data["remaining_term_loads"] = tl.get("display", None)
        data["term_loads"] = tl
        return JsonResponse(data)

    except Exception as e:
        import traceback

        traceback.print_exc()
        raise e


###############################################################
