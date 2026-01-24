from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="pointtransaction",
            name="pointtransaction_type_constraints",
        ),
        migrations.AddConstraint(
            model_name="pointtransaction",
            constraint=models.CheckConstraint(
                check=(
                    (Q(tx_type="REDEEM") & Q(bonus_item__isnull=False) & Q(points_delta__lt=0))
                    | (Q(tx_type="AWARD") & Q(bonus_item__isnull=True) & Q(points_delta__gt=0))
                    | (Q(tx_type="ADMIN_ADJUST") & Q(bonus_item__isnull=True) & Q(points_delta__gt=0))
                ),
                name="pointtransaction_type_constraints",
            ),
        ),
    ]
