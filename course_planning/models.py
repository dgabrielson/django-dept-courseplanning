"""
Models for the course_planning application.
"""
#######################
from __future__ import print_function, unicode_literals

from autoslug import AutoSlugField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.encoding import python_2_unicode_compatible

from . import conf
from .managers import CourseInfoManager, CourseProgramInfoManager, ProgramManager
from .utils import has_adjacent_timeslots

#######################################################################
#######################################################################
#######################################################################


class CoursePlanningBaseModel(models.Model):
    """
    An abstract base class.
    """

    active = models.BooleanField(default=True)
    created = models.DateTimeField(
        auto_now_add=True, editable=False, verbose_name="creation time"
    )
    modified = models.DateTimeField(
        auto_now=True, editable=False, verbose_name="last modification time"
    )

    class Meta:
        abstract = True


#######################################################################
#######################################################################
#######################################################################


@python_2_unicode_compatible
class Program(CoursePlanningBaseModel):
    """
    A Program of Study.  May be specific or general.
    """

    verbose_name = models.CharField(max_length=64)
    slug = AutoSlugField(max_length=64, unique=True, populate_from="verbose_name")
    ordering = models.PositiveSmallIntegerField(default=100)
    scheduled = models.BooleanField(
        default=False,
        verbose_name="Use for scheduling",
        help_text="Use courses in this program for scheduling",
    )
    public = models.BooleanField(
        default=False, help_text="Show in main list of programs"
    )
    description = models.TextField(
        blank=True, help_text=conf.get("program:description:help_text")
    )

    objects = ProgramManager()

    class Meta:
        ordering = ("ordering", "verbose_name")
        base_manager_name = "objects"

    def __str__(self):
        return self.verbose_name

    def get_absolute_url(self):
        return reverse("courseplanning-program-detail", kwargs={"slug": self.slug})


#######################################################################

#######################################################################


@python_2_unicode_compatible
class CourseInfo(CoursePlanningBaseModel):
    """
    A description of this model.
    """

    RUN_CHOICES = (
        ("a", "all years"),
        ("o", "odd years"),
        ("e", "even years"),
        ("i", "irregular"),
    )

    course = models.OneToOneField(
        "classes.Course", on_delete=models.CASCADE, limit_choices_to={"active": True}
    )
    has_lab = models.BooleanField(default=False)
    fall = models.BooleanField(default=False)
    winter = models.BooleanField(default=False)
    summer = models.BooleanField(default=False)
    runs = models.CharField(max_length=2, choices=RUN_CHOICES, default="a")

    objects = CourseInfoManager()

    class Meta:
        ordering = ("course",)
        verbose_name = "Course information"
        verbose_name_plural = "Course information"
        base_manager_name = "objects"

    def __str__(self):
        return str(self.course)

    # def get_absolute_url(self):
    #     return reverse('course_planning-course_planningmodel-detail', kwargs={'slug': self.slug})


#######################################################################


@python_2_unicode_compatible
class CourseProgramInfo(CoursePlanningBaseModel):
    """
    Information about this course in a particular program
    """

    CONSTRAINT_CHOICES = (("o", "Optional"), ("c", "Recommended"), ("r", "Required"))
    USUAL_YEAR_CHOICES = (
        ("0", "Not applicable"),
        ("1", "1"),
        ("2", "2"),
        ("3", "3"),
        ("3.5", "3/4"),
        ("4", "4"),
        ("7", "Masters"),
        ("8", "PhD"),
    )

    course = models.ForeignKey(
        CourseInfo, on_delete=models.CASCADE, limit_choices_to={"active": True}
    )
    program = models.ForeignKey(
        Program, on_delete=models.CASCADE, limit_choices_to={"active": True}
    )
    usual_year = models.CharField(max_length=8, choices=USUAL_YEAR_CHOICES, default="0")
    constraint = models.CharField(max_length=2, choices=CONSTRAINT_CHOICES, default="o")

    objects = CourseProgramInfoManager()

    class Meta:
        ordering = ("usual_year", "course")
        unique_together = (("course", "program"),)
        verbose_name = "Course program information"
        verbose_name_plural = "Course program information"
        base_manager_name = "objects"

    def __str__(self):
        return str(self.course)

    # def get_absolute_url(self):
    #     return reverse('course_planning-course_planningmodel-detail', kwargs={'slug': self.slug})


#######################################################################


@python_2_unicode_compatible
class TeachingProfile(CoursePlanningBaseModel):

    person = models.OneToOneField(
        "people.Person",
        on_delete=models.CASCADE,
        limit_choices_to={"active": True},
        db_index=True,
    )
    agreed_load = models.PositiveSmallIntegerField(
        default=3, help_text="For the upcoming regular session only"
    )
    preference_same_day = models.BooleanField(
        default=False,
        help_text="Select this if you would prefer to have all of your teaching on the same day",
    )
    preference_no_back_to_back = models.BooleanField(
        default=False,
        help_text="Select this if you would prefer not to have any back to back teaching",
    )
    last_reviewed = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return "{}".format(self.person)

    class Meta:
        ordering = ("person",)

    def get_absolute_url(self):
        return reverse("courseplanning-teaching-profile")

    def get_semesterteachingpreferences(self):
        return self.semesterteachingpreference_set.filter(active=True)

    def get_favourite_coursepreferences(self, min_score=4):
        return (
            self.courseteachingpreference_set.filter(active=True)
            .exclude(score__lt=min_score)
            .order_by("-score", "course")
        )

    def get_favourite_timeslotpreferences(self, min_score=4):
        return (
            self.timeslotteachingpreference_set.filter(active=True)
            .exclude(score__lt=min_score)
            .order_by("-score", "timeslot")
        )

    def get_score(self, course_id, timeslot_id, jitter=0):
        """
        See also .schedule.utils.auto:_build_ranking_matrix(...)
        The score calculations should always align.
        """
        try:
            c_score = self.courseteachingpreference_set.get(course_id=course_id).score
        except CourseTeachingPreference.DoesNotExist:
            c_score = 0
        try:
            t_score = self.timeslotteachingpreference_set.get(
                timeslot_id=timeslot_id
            ).score
        except TimeslotTeachingPreference.DoesNotExist:
            t_score = 0
        score = c_score * (t_score * c_score + jitter)
        return score

    def get_remaining_loads(self, session):
        """
        Return the **remaining** loads as a pair:
        ``total_remaining, semester_remaining``
        """
        session_qs = self.draftsection_set.filter(active=True, session=session)
        total_load = self.agreed_load - session_qs.count()
        semesterprefs_qs = self.semesterteachingpreference_set.filter(active=True)
        term_data = {
            v["semester"]: v["preferred_load"]
            for v in semesterprefs_qs.values("semester", "preferred_load")
        }
        for code in term_data:
            term_data[code] -= session_qs.filter(semester=code).count()
        code_display = dict(SemesterTeachingPreference.SEMESTER_CHOICES)
        display = " / ".join(
            ["{}:{:.1f}".format(code_display[c][0], term_data[c]) for c in term_data]
        )
        term_data["display"] = display

        return total_load, term_data

    def has_back_to_back(self, session, semester_code):
        """
        Return ``True`` only when the preference is NOT for back to back
        teaching.
        """
        result = False
        if self.preference_no_back_to_back:
            from classes.models import Timeslot

            timeslot_id_list = (
                self.draftsection_set.filter(
                    active=True, session=session, semester=semester_code
                )
                .exclude(timeslot__isnull=True)
                .values_list("timeslot_id", flat=True)
            )
            online = Timeslot.objects.Online()
            timeslot_qs = Timeslot.objects.filter(pk__in=timeslot_id_list).exclude(
                pk=online.pk
            )
            if timeslot_qs.exists():
                result = has_adjacent_timeslots(timeslot_qs)
        return result

    def has_different_days(self, session, semester_code):
        """
        Return ``True`` only when the preference is for same day teaching.
        """
        result = False
        if self.preference_same_day:
            from classes.models import Timeslot

            timeslot_id_list = (
                self.draftsection_set.filter(
                    active=True, session=session, semester=semester_code
                )
                .exclude(timeslot__isnull=True)
                .values_list("timeslot_id", flat=True)
            )
            online = Timeslot.objects.Online()
            timeslot_qs = Timeslot.objects.filter(pk__in=timeslot_id_list).exclude(
                pk=online.pk
            )
            if timeslot_qs.exists():
                ref_day = timeslot_qs[0].day
                for timeslot in timeslot_qs:
                    if timeslot.day != ref_day:
                        if (
                            timeslot.day in ref_day
                        ):  # timeslot is substring of reference
                            pass
                        elif (
                            ref_day in timeslot.day
                        ):  # reference is substring of timeslot
                            ref_day = timeslot.day
                        else:  # different!
                            result = True
                            break
        return result

    def get_timeslot_conflicts(self, session, semester_code):
        """
        Returns a list of any duplicate timeslot id's that have been assigned.
        Note: Online does not count.
        """
        from classes.models import Timeslot

        timeslot_id_list = list(
            self.draftsection_set.filter(
                active=True, session=session, semester=semester_code
            )
            .exclude(timeslot__isnull=True)
            .values_list("timeslot_id", flat=True)
        )
        timeslot_id_set = set(timeslot_id_list)
        online = Timeslot.objects.Online()
        result = []
        if len(timeslot_id_set) != len(timeslot_id_list):
            for tid in timeslot_id_set:
                if tid != online.pk and timeslot_id_list.count(tid) > 1:
                    result.append(tid)
        return result


#######################################################################


class TeachingProfileRelatedModel(CoursePlanningBaseModel):
    """
    An abstract base model for anything that needs a ForeignKey
    to the teaching profile
    """

    profile = models.ForeignKey(
        TeachingProfile, on_delete=models.CASCADE, limit_choices_to={"active": True}
    )

    class Meta:
        abstract = True


#######################################################################


@python_2_unicode_compatible
class CourseTeachingPreference(TeachingProfileRelatedModel):

    course = models.ForeignKey(
        "classes.Course",
        on_delete=models.CASCADE,
        limit_choices_to={
            "active": True,
            "department__active": True,
            "department__advertised": True,
            "courseinfo__courseprograminfo__program__active": True,
            "courseinfo__courseprograminfo__program__scheduled": True,
        },
    )
    score = models.PositiveSmallIntegerField(
        default=5, validators=[MaxValueValidator(9)]
    )

    def __str__(self):
        return "{} / {}".format(self.course, self.score)

    class Meta:
        ordering = ("profile", "course")


#######################################################################


@python_2_unicode_compatible
class TimeslotTeachingPreference(TeachingProfileRelatedModel):

    timeslot = models.ForeignKey(
        "classes.Timeslot",
        on_delete=models.CASCADE,
        limit_choices_to={"active": True, "scheduled": True},
    )
    score = models.PositiveSmallIntegerField(
        default=5, validators=[MaxValueValidator(9)]
    )

    def __str__(self):
        return "{} / {}".format(self.timeslot, self.score)

    class Meta:
        ordering = ("profile", "timeslot")


#######################################################################


@python_2_unicode_compatible
class SemesterTeachingPreference(TeachingProfileRelatedModel):
    SEMESTER_CHOICES = (
        ("1", "Winter"),
        # ('2', 'Summer'),
        # ('2a', 'Summer (May-June)'),
        # ('2d', 'Summer (May)'),
        # ('2g', 'Summer (June)'),
        # ('2j', 'Summer (July-August)'),
        # ('2m', 'Summer (July)'),
        # ('2p', 'Summer (August)'),
        ("3", "Fall"),
    )

    semester = models.CharField(max_length=2, choices=SEMESTER_CHOICES)
    preferred_load = models.FloatField(
        default=1.5, validators=[MaxValueValidator(9), MinValueValidator(0)]
    )

    # NOTE: form validation should ensure that sum of semester.preferred_load
    #   values == profile.agreed_load

    def __str__(self):
        return "{} / {}".format(self.get_semester_display(), self.preferred_load)

    class Meta:
        unique_together = (("semester", "profile"),)
        ordering = ("profile", "-semester")


#######################################################################


@python_2_unicode_compatible
class TeachingSurveyQuestion(CoursePlanningBaseModel):

    question = models.CharField(max_length=1024, help_text="Text of the question?")

    def __str__(self):
        return self.question


#######################################################################


@python_2_unicode_compatible
class TeachingSurveyAnswer(TeachingProfileRelatedModel):

    question = models.ForeignKey(TeachingSurveyQuestion, on_delete=models.CASCADE)
    answer = models.CharField(max_length=1024, blank=True)

    class Meta:
        unique_together = (("profile", "question"),)
        ordering = ("profile", "question")

    def __str__(self):
        return "{} {}".format(self.question, self.answer)


#######################################################################


@python_2_unicode_compatible
class DraftScheduleSession(CoursePlanningBaseModel):
    RUN_CHOICES = (("o", "odd year"), ("e", "even year"))

    verbose_name = models.CharField(
        max_length=128, help_text='e.g., "Regular Session 2018-2019"'
    )
    slug = AutoSlugField(max_length=128, unique=True, populate_from="verbose_name")

    start_date = models.DateField()
    end_date = models.DateField()
    initialized = models.BooleanField(default=False)

    def __str__(self):
        return self.verbose_name

    def admin_change_link(self):
        return reverse(
            "admin:{}_{}_change".format(self._meta.app_label, self._meta.model_name),
            args=[self.pk],
        )

    def get_section_queryset(self, year_offset):
        """
        Note: NOT the same logic used in ``schedule.initialize``.
        """
        from classes.models import Section

        start = self.start_date.replace(year=self.start_date.year + year_offset)
        end = self.end_date.replace(year=self.end_date.year + year_offset)
        qs = Section.objects.filter(
            course__department__advertised=True,
            course__department__active=True,
            course__active=True,
            active=True,
            sectionschedule__active=True,
            sectionschedule__date_range__active=True,
            sectionschedule__date_range__start__gte=start,
            sectionschedule__date_range__finish__lte=end,
        ).distinct()
        qs = qs.filter(section_type__in=conf.get("valid_section_types"))
        return qs

    def current_actual_sections(self):
        return self.get_section_queryset(year_offset=0)

    def next_actual_sections(self):
        return self.get_section_queryset(year_offset=1)

    def prev_actual_sections(self):
        return self.get_section_queryset(year_offset=-1)

    def two_years_ago_actual_sections(self):
        return self.get_section_queryset(year_offset=-2)


#######################################################################


@python_2_unicode_compatible
class DraftSection(CoursePlanningBaseModel):

    # fixed information
    verbose_name = models.CharField(
        max_length=16, help_text='e.g., "A01"', verbose_name="section"
    )
    # or should this be a course info?
    course = models.ForeignKey(
        "classes.Course",
        on_delete=models.CASCADE,
        limit_choices_to={
            "active": True,
            "department__active": True,
            "department__advertised": True,
        },
    )
    session = models.ForeignKey(DraftScheduleSession, on_delete=models.CASCADE)
    semester = models.CharField(
        max_length=2, choices=SemesterTeachingPreference.SEMESTER_CHOICES
    )

    # variable Information
    timeslot = models.ForeignKey(
        "classes.Timeslot",
        on_delete=models.CASCADE,
        limit_choices_to={"active": True, "scheduled": True},
        null=True,
        blank=True,
    )
    # Or should this be to a person that has a teaching profile?
    instructor = models.ForeignKey(
        TeachingProfile, on_delete=models.CASCADE, null=True, blank=True
    )

    class Meta:
        unique_together = (("course", "verbose_name", "session", "semester"),)
        ordering = ("session", "-semester", "course", "verbose_name")

    def __str__(self):
        return str(self.course.label) + " " + self.verbose_name

    def real_section(self):
        """
        Attempt to match this section to an actual Section object;
        """
        from classes.models import Section

        # probably need a better heuristic map for this:
        year = (
            self.session.start_date.year
            if self.semester != "1"
            else self.session.end_date.year
        )
        qs = Section.objects.filter(
            active=True,
            course=self.course,
            section_name__iexact=self.verbose_name,
            term__term=self.semester,
            term__year=year,
        )
        if qs.count() > 0:
            return qs.first()


#######################################################################
#######################################################################
#######################################################################
