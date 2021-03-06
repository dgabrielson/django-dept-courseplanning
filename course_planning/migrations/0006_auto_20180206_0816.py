# Generated by Django 2.0.1 on 2018-02-06 14:16

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("course_planning", "0005_program_public")]

    operations = [
        migrations.AlterModelOptions(
            name="semesterteachingpreference", options={"ordering": ("semester",)}
        ),
        migrations.AlterField(
            model_name="courseteachingpreference",
            name="course",
            field=models.ForeignKey(
                limit_choices_to={
                    "active": True,
                    "courseinfo__courseprograminfo__program__active": True,
                    "courseinfo__courseprograminfo__program__scheduled": True,
                    "department__active": True,
                    "department__advertised": True,
                },
                on_delete=django.db.models.deletion.CASCADE,
                to="classes.Course",
            ),
        ),
    ]
