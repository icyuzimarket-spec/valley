from django.db import migrations

PLANS = [
    # level, price, daily_income, all_return, duration_days
    (1, 10000, 1200, 60000, 50),
    (2, 20000, 2400, 120000, 50),
    (3, 30000, 3600, 180000, 50),
    (4, 40000, 4800, 240000, 50),
    (5, 50000, 6000, 300000, 50),
    (6, 70000, 8400, 420000, 50),
    (7, 80000, 9600, 480000, 50),
    (8, 100000, 12000, 600000, 50),
    (9, 120000, 14400, 720000, 50),
    (10, 150000, 18000, 900000, 50),
    (11, 200000, 24000, 1200000, 50),
    (12, 300000, 36000, 1800000, 50),
    (13, 500000, 60000, 3000000, 50),
]


def seed_plans(apps, schema_editor):
    Plan = apps.get_model("investments", "Plan")
    for level, price, daily_income, all_return, duration_days in PLANS:
        Plan.objects.get_or_create(
            level=level,
            defaults={
                "price": price,
                "daily_income": daily_income,
                "all_return": all_return,
                "duration_days": duration_days,
                "is_active": True,
            },
        )


def unseed_plans(apps, schema_editor):
    Plan = apps.get_model("investments", "Plan")
    Plan.objects.filter(level__in=[p[0] for p in PLANS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("investments", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_plans, unseed_plans),
    ]
