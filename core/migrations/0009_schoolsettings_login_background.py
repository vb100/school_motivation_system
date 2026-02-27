from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0008_alter_bonusitem_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="schoolsettings",
            name="login_background",
            field=models.ImageField(blank=True, upload_to="school_backgrounds/"),
        ),
    ]
