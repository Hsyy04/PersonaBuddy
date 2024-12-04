# Generated by Django 4.1 on 2024-08-04 16:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("agent", "0018_chilog_from_which_session"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="chilog",
            name="from_which_session",
        ),
        migrations.AddField(
            model_name="gencontentlog",
            name="from_which_session",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="agent.session",
            ),
        ),
    ]
