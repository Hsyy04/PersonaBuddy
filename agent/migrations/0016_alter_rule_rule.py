# Generated by Django 4.1 on 2024-08-04 08:16

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("agent", "0015_personalitiesclick"),
    ]

    operations = [
        migrations.AlterField(
            model_name="rule",
            name="rule",
            field=models.CharField(max_length=100, verbose_name="规则"),
        ),
    ]
