# Generated by Django 2.0.1 on 2018-02-05 17:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("course_planning", "0004_auto_20180201_1411")]

    operations = [
        migrations.AddField(
            model_name="program",
            name="public",
            field=models.BooleanField(
                default=False, help_text="Show in main list of programs"
            ),
        )
    ]