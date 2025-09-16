from django.db import models

# Create your models here.
from django.db import models
import hashlib
import uuid
from django.utils import timezone
from datetime import timedelta


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


class PasswordResetToken(models.Model):
    student = models.ForeignKey(StudentModel, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=1)
        super().save(*args, **kwargs)

    def is_valid(self):
        return not self.used and timezone.now() < self.expires_at

    def __str__(self):
        return f"Reset token for {self.student.username}"
