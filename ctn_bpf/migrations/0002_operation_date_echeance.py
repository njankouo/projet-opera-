# Generated by Django 4.2.1 on 2023-10-02 14:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ctn_bpf', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='operation',
            name='date_echeance',
            field=models.DateField(null=True),
        ),
    ]