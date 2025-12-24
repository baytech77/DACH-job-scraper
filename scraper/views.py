from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from .tasks import scrape_jobs_task
from .models import Job  # For recent jobs display
from django.http import JsonResponse
from celery.result import AsyncResult
from .models import Job


def recent_jobs_api(request):
    """API for live job updates"""
    jobs = Job.objects.select_related('company').order_by('-scraped_at')[:10]
    return JsonResponse({
        'jobs': [{
            'id': job.id,
            'title': job.title,
            'company': job.company.name,
            'location': job.location,
            'sources': job.sources,
            'scraped_at': job.scraped_at.isoformat(),
            'company_email': job.company.email,
            'company_website': job.company.website
        } for job in jobs],
        'total_jobs': Job.objects.count()
    })



def dashboard(request):
     # Show 10 most recent jobs
    #recent_jobs = Job.objects.select_related('company').order_by('-scraped_at')[:10]
    #total_jobs = Job.objects.count()
    #total_companies = Job.objects.values('company').distinct().count()
    #
    #context = {
    #    'recent_jobs': recent_jobs,
    #    'total_jobs': total_jobs,
    #    'total_companies': total_companies,
    #}
    #return render(request, 'dashboard.html', context)
    task_id = request.GET.get('task_id')
    task_status = None
    if task_id:
        task_result = AsyncResult(task_id)
        task_status = {
            'id': task_id,
            'status': task_result.status,
            'result': task_result.result if task_result.ready() else None
        }
    
    recent_jobs = Job.objects.select_related('company').order_by('-scraped_at')[:10]
    context = {
        'recent_jobs': recent_jobs,
        'task_status': task_status,
    }
    return render(request, 'dashboard.html', context)

@require_http_methods(["POST"])
def start_scraping(request):
    """Fixed view - handles FORM DATA only (no DRF)"""
    platform = request.POST.get('platform')
    filtered_url = request.POST.get('filtered_url')
    num_jobs = request.POST.get('num_jobs', '20')
    
    # Validation
    errors = []
    if not platform:
        errors.append('Select a platform')
    if not filtered_url or not filtered_url.startswith(('http://', 'https://')):
        errors.append('Enter valid URL')
    try:
        num_jobs = int(num_jobs)
        if num_jobs < 1 or num_jobs > 100:
            errors.append('Jobs: 1-100 only')
    except ValueError:
        errors.append('Invalid job count')
    
    if errors:
        for error in errors:
            messages.error(request, error)
        return redirect('dashboard')
    
    # Start scraping
    task = scrape_jobs_task.delay(platform, filtered_url, num_jobs)
    messages.success(request, f'🚀 Started! Task: {task.id} | {num_jobs} jobs from {platform}')
    #messages.success(request, f'Scraping started!')
    print(f"POST data: {dict(request.POST)}")  # Should show platform, filtered_url, num_jobs
    return redirect('/')
    

def job_detail(request, job_id):
    """View single job with full details"""
    job = get_object_or_404(Job, id=job_id)
    context = {
        'job': job,
    }
    return render(request, 'job_detail.html', context)