# Generated by Django 2.1.4 on 2018-12-10 20:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("course_planning", "0017_merge_20180418_1053")]

    operations = [
        migrations.AddField(
            model_name="courseprograminfo",
            name="contraint",
            field=models.CharField(
                choices=[("o", "Optional"), ("c", "Recommended"), ("r", "Required")],
                default="o",
                max_length=2,
            ),
        )
    ]
