# Generated by Django 4.2.3 on 2024-07-18 14:59

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('agent', '0008_message_has_action'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='message',
            name='has_action',
        ),
    ]
