# Generated by Django 4.2.1 on 2023-08-17 19:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='organizationsettings',
            name='localai_api_key',
            field=models.CharField(
                blank=True,
                default=None,
                help_text='LocalAI API key to use with LocalAI backend',
                max_length=256,
                null=True),
        ),
        migrations.AddField(
            model_name='organizationsettings',
            name='localai_base_url',
            field=models.CharField(
                blank=True,
                default=None,
                help_text='LocalAI base URL to use with LocalAI backend',
                max_length=256,
                null=True),
        ),
    ]
