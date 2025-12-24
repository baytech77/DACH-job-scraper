from django.urls import path, include
from .views import dashboard, start_scraping, job_detail, recent_jobs_api


# scraper/urls.py
urlpatterns = [
    path('', dashboard, name='dashboard'),
     path('job/<int:job_id>/', job_detail, name='job_detail'),
    path('start-scraping/', start_scraping, name='start_scraping'),
    path('api/recent-jobs/', recent_jobs_api, name='recent_jobs_api'),

]