# scraper/models.py
from django.db import models
from django.contrib.postgres import fields as pg_fields

class Company(models.Model):
    name = models.CharField(max_length=200, unique=True)
    website = models.URLField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['name'])]
        verbose_name_plural = "Companies"

    
    def save(self, *args, **kwargs):
        # 🔥 BULLETPROOF: Never save empty names
        if self.name and len(self.name.strip()) > 1:
            self.name = self.name.strip()
            super().save(*args, **kwargs)


    def __str__(self):
        return self.name

class Job(models.Model):
    title = models.CharField(max_length=200)
    location = models.CharField(max_length=200)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='jobs')
    description = models.TextField()
    source_url = models.URLField()
    sources = pg_fields.ArrayField(models.CharField(max_length=50), default=list)  # ['linkedin', 'indeed']
    scraped_at = models.DateTimeField(auto_now_add=True)
    
    # Composite unique constraint for better duplicate detection
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['title', 'company', 'location'], 
                name='unique_job_identifier'
            )
        ]
        indexes = [
            models.Index(fields=['title', 'company']),
            models.Index(fields=['scraped_at']),
            models.Index(fields=['location']),
        ]
        verbose_name_plural = "Jobs"

    def __str__(self):
        return f"{self.title} - {self.company.name}"

    def add_source(self, source):
        if source not in self.sources:
            self.sources.append(source)
            self.save(update_fields=['sources'])
