# notes/models.py
from django.db import models
from patients.models import Patient

class Notes(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    title = models.CharField(max_length=250)
    body = models.TextField()
    document = models.FileField(upload_to='notes_docs/', null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    date_updated = models.DateTimeField(auto_now=True, blank=True, null=True)
    
    def __str__(self):
        return f'{self.patient} | {self.title}'
    
    class Meta:
        ordering = ['-date_created']  # Most recent first
        verbose_name = 'Note'
        verbose_name_plural = 'Notes'