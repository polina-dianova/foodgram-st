# Generated by Django 5.1.4 on 2025-01-11 21:14

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_alter_ingredient_options_alter_recipe_options_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='subscription',
            options={'ordering': ['id'], 'verbose_name': 'Subscription', 'verbose_name_plural': 'Subscriptions'},
        ),
    ]
