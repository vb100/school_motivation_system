from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_schoolsettings"),
    ]

    operations = [
        migrations.AddField(
            model_name="schoolsettings",
            name="logo",
            field=models.ImageField(blank=True, upload_to="school_logos/"),
        ),
    ]
