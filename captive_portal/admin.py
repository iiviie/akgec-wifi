from django.contrib import admin
from .models import StudentModel
from import_export.admin import ImportExportModelAdmin


# Register your model with ImportExportModelAdmin
class StudentModelAdmin(ImportExportModelAdmin):
    pass


admin.site.register(StudentModel, StudentModelAdmin)
