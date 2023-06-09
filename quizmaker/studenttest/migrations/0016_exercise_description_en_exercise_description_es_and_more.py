# Generated by Django 4.2.1 on 2023-06-01 13:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('studenttest', '0015_userexercise_stars'),
    ]

    operations = [
        migrations.AddField(
            model_name='exercise',
            name='description_en',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='exercise',
            name='description_es',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='exercise',
            name='description_fr',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='exercise',
            name='description_it',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='exercise',
            name='expected_answer_en',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='exercise',
            name='expected_answer_es',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='exercise',
            name='expected_answer_fr',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='exercise',
            name='expected_answer_it',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='exercise',
            name='title_en',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='exercise',
            name='title_es',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='exercise',
            name='title_fr',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='exercise',
            name='title_it',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='test',
            name='description_en',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='test',
            name='description_es',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='test',
            name='description_fr',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='test',
            name='description_it',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='test',
            name='name_en',
            field=models.CharField(max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='test',
            name='name_es',
            field=models.CharField(max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='test',
            name='name_fr',
            field=models.CharField(max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='test',
            name='name_it',
            field=models.CharField(max_length=200, null=True),
        ),
    ]
