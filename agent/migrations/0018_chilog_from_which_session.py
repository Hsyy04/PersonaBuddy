# Generated by Django 4.1 on 2024-08-04 15:39

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("agent", "0017_alter_chilog_options_alter_gencontentlog_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="chilog",
            name="from_which_session",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="agent.session",
            ),
        ),
    ]
