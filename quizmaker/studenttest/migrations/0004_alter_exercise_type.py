# Generated by Django 4.2.1 on 2023-05-10 10:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('studenttest', '0003_multiplechoiceexercise_textanswer_exercise_type_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='exercise',
            name='type',
            field=models.CharField(blank=True, choices=[('O', 'Open question'), ('M', 'Multiple choice question'), ('C', 'Coding question')], max_length=1, null=True),
        ),
    ]
