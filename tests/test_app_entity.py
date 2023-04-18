from django.db import models


class AppEntityTest(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)