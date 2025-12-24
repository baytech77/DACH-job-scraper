from django.contrib import admin
from .models import Job, Company

# Register your models here.

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ['title', 'company', 'location', 'scraped_at', 'get_sources']
    list_filter = ['scraped_at', 'company', 'location']
    search_fields = ['title', 'company__name', 'description']
    readonly_fields = ['sources', 'scraped_at']
    
    def get_sources(self, obj):
        return ', '.join(obj.sources)
    get_sources.short_description = 'Sources'

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'website', 'created_at']
    search_fields = ['name']
