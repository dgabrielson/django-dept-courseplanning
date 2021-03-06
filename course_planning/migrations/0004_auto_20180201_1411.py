# Generated by Django 2.0.1 on 2018-02-01 20:11

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("course_planning", "0003_teachingprofile_agreed_load")]

    operations = [
        migrations.CreateModel(
            name="SemesterTeachingPreference",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("active", models.BooleanField(default=True)),
                (
                    "created",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="creation time"
                    ),
                ),
                (
                    "modified",
                    models.DateTimeField(
                        auto_now=True, verbose_name="last modification time"
                    ),
                ),
                (
                    "semester",
                    models.CharField(
                        choices=[("1", "Winter"), ("3", "Fall")], max_length=2
                    ),
                ),
                (
                    "preferred_load",
                    models.FloatField(
                        default=1.5,
                        validators=[
                            django.core.validators.MaxValueValidator(9),
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.DecimalValidator(
                                decimal_places=1, max_digits=2
                            ),
                        ],
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="TeachingSurveyAnswer",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("active", models.BooleanField(default=True)),
                (
                    "created",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="creation time"
                    ),
                ),
                (
                    "modified",
                    models.DateTimeField(
                        auto_now=True, verbose_name="last modification time"
                    ),
                ),
                ("answer", models.CharField(blank=True, max_length=1024)),
            ],
        ),
        migrations.CreateModel(
            name="TeachingSurveyQuestion",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("active", models.BooleanField(default=True)),
                (
                    "created",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="creation time"
                    ),
                ),
                (
                    "modified",
                    models.DateTimeField(
                        auto_now=True, verbose_name="last modification time"
                    ),
                ),
                (
                    "question",
                    models.CharField(
                        help_text="Text of the question?", max_length=1024
                    ),
                ),
            ],
            options={"abstract": False},
        ),
        migrations.AlterField(
            model_name="teachingprofile",
            name="person",
            field=models.ForeignKey(
                limit_choices_to={"active": True},
                on_delete=django.db.models.deletion.CASCADE,
                to="people.Person",
            ),
        ),
        migrations.AddField(
            model_name="teachingsurveyanswer",
            name="profile",
            field=models.ForeignKey(
                limit_choices_to={"active": True},
                on_delete=django.db.models.deletion.CASCADE,
                to="course_planning.TeachingProfile",
            ),
        ),
        migrations.AddField(
            model_name="teachingsurveyanswer",
            name="question",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="course_planning.TeachingSurveyQuestion",
            ),
        ),
        migrations.AddField(
            model_name="semesterteachingpreference",
            name="profile",
            field=models.ForeignKey(
                limit_choices_to={"active": True},
                on_delete=django.db.models.deletion.CASCADE,
                to="course_planning.TeachingProfile",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="teachingsurveyanswer", unique_together={("profile", "question")}
        ),
        migrations.AlterUniqueTogether(
            name="semesterteachingpreference", unique_together={("semester", "profile")}
        ),
    ]
