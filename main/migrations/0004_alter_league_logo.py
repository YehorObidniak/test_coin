# Generated by Django 5.0.4 on 2024-04-29 14:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_alter_player_last_seen'),
    ]

    operations = [
        migrations.AlterField(
            model_name='league',
            name='logo',
            field=models.CharField(blank=True, max_length=1023, null=True),
        ),
    ]