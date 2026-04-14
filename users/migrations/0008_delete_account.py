from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0007_account"),
    ]

    operations = [
        migrations.DeleteModel(
            name="Account",
        ),
    ]
