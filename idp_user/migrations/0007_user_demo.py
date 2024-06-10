from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('idp_user', '0006_userrole_organization_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_demo',
            field=models.BooleanField(default=False, help_text='Whether this user is a demo user.'),
        ),
    ]
