# Generated by Django 4.1.3 on 2023-03-05 00:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('websites', '0002_maladie'),
    ]

    operations = [
        migrations.AddField(
            model_name='maladie',
            name='is_active',
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
    ]
