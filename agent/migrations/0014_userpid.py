# Generated by Django 4.2.3 on 2024-07-22 05:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("agent", "0013_record_sum_content"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserPid",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "pid",
                    models.CharField(default="P00", max_length=10, verbose_name="参与者"),
                ),
            ],
        ),
    ]
