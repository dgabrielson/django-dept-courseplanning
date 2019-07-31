# Generated by Django 2.2 on 2019-04-30 13:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("course_planning", "0022_auto_usual_year_data")]

    operations = [
        migrations.AlterModelOptions(
            name="courseprograminfo",
            options={
                "base_manager_name": "objects",
                "ordering": ("usual_year", "course"),
                "verbose_name": "Course program information",
                "verbose_name_plural": "Course program information",
            },
        ),
        migrations.RemoveField(
            model_name="courseprograminfo", name="usual_program_year"
        ),
        migrations.AlterField(
            model_name="courseprograminfo",
            name="usual_year",
            field=models.CharField(
                choices=[
                    ("0", "Not applicable"),
                    ("1", "1"),
                    ("2", "2"),
                    ("3", "3"),
                    ("3.5", "3/4"),
                    ("4", "4"),
                    ("7", "Masters"),
                    ("8", "PhD"),
                ],
                default="0",
                max_length=8,
            ),
        ),
    ]