from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0007_bonus_redemption_request_and_bonus_category"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="bonusitem",
            options={
                "verbose_name": "Pointify.lt pasiūlymas",
                "verbose_name_plural": "Pointify.lt pasiūlymai",
            },
        ),
    ]
