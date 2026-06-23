from django.db import models

class ComponentData(models.Model):
    mpn = models.CharField(max_length=100)
    man = models.CharField(max_length=100)  # Manufacturer
    description = models.TextField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    batch_id = models.CharField(max_length=50, blank=True, null=True)
    datasheet_url = models.URLField(max_length=500, blank=True, null=True)
    status = models.CharField(max_length=50, blank=True, null=True)
    lifecycle = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.mpn} - {self.man}"