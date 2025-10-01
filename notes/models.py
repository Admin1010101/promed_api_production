from django.db import models
from patients.models import Patient

# Create your models here.
class Notes(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    title = models.CharField(max_length=250)
    body = models.TextField()
    document = models.FileField(upload_to='notes_docs/', null=True, blank=True)
    # date_create = models.DateTimeField(auto_now_add=True)
    # data_updated = models.DateTimeField(auto_now=True)

    
    # def __str__(self):
    #     return str(f'{self.patient} | {self.title}')
