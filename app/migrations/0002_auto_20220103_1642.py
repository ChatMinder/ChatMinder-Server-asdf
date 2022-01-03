# Generated by Django 3.0.8 on 2022-01-03 16:42

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Bookmark',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_marked', models.BooleanField(default=False)),
            ],
            options={
                'db_table': 'bookmark',
            },
        ),
        migrations.RemoveField(
            model_name='link',
            name='memo',
        ),
        migrations.RemoveField(
            model_name='memo',
            name='is_marked',
        ),
        migrations.AddField(
            model_name='memo',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to=''),
        ),
        migrations.AddField(
            model_name='memo',
            name='is_tag_new',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='memo',
            name='url',
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='memo',
            name='memo_text',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='memo',
            name='tag',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='app.Tag'),
        ),
        migrations.DeleteModel(
            name='Image',
        ),
        migrations.DeleteModel(
            name='Link',
        ),
        migrations.AddField(
            model_name='bookmark',
            name='memo',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.Memo'),
        ),
    ]
