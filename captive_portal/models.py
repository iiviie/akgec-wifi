from django.db import models

# Create your models here.
from django.db import models
import hashlib


# Define the StudentModel with bcrypt hashing for passwords
class StudentModel(models.Model):
    username = models.CharField(max_length=100, db_index=True)
    email = models.EmailField(null=True, blank=True)
    password = models.CharField(max_length=100)

    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        # Hash the password using bcrypt before saving
        self.password = hashlib.md5(self.password.encode()).hexdigest()

        super(StudentModel, self).save(*args, **kwargs)
