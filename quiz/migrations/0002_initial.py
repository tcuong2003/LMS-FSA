# Generated by Django 5.0.9 on 2024-10-25 07:39

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('quiz', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='quiz',
            name='created_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='question',
            name='quiz',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='questions', to='quiz.quiz'),
        ),
        migrations.AddField(
            model_name='studentanswer',
            name='question',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='quiz.question'),
        ),
        migrations.AddField(
            model_name='studentanswer',
            name='selected_option',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='quiz.answeroption'),
        ),
        migrations.AddField(
            model_name='aigrading',
            name='answer',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='quiz.studentanswer'),
        ),
        migrations.AddField(
            model_name='studentquizattempt',
            name='quiz',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='quiz.quiz'),
        ),
        migrations.AddField(
            model_name='studentquizattempt',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='studentanswer',
            name='attempt',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='quiz.studentquizattempt'),
        ),
    ]
