from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from .tasks import scrape_jobs_task
from .models import Job
from django.http import JsonResponse
from celery.result import AsyncResult
from scraper.services import JobScraper  # Import URL generator
from django_countries import countries
from django.http import JsonResponse

def task_status_api(request, task_id):
    """🔄 AJAX endpoint for LIVE task status + jobs"""
    try:
        task_result = AsyncResult(task_id)
        status = task_result.status
        
        # 🔥 Get LATEST jobs (refreshes automatically)
        recent_jobs = Job.objects.select_related('company').order_by('-scraped_at')[:12]
        
        return JsonResponse({
            'status': status,
            'result': task_result.result if task_result.ready() else None,
            'jobs_count': recent_jobs.count(),
            'total_jobs': Job.objects.count(),
            'jobs': [{
                'title': job.title[:60],
                'company': job.company.name,
                'location': job.location,
                'sources': job.sources,
                'scraped_at': job.scraped_at.isoformat() if job.scraped_at else None,
                'email': job.company.email,
            } for job in recent_jobs]
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


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
    task_id = request.GET.get('task_id')
    task_status = None
    if task_id:
        task_result = AsyncResult(task_id)
        task_status = {
            'id': task_id,
            'status': task_result.status,
            'result': task_result.result if task_result.ready() else None
        }
    
    recent_jobs = Job.objects.select_related('company').order_by('-scraped_at')[:12]
    context = {
        'recent_jobs': recent_jobs,
        'task_status': task_status,
        'countries': countries,
        'task_id': task_id,
    }
    return render(request, 'dashboard.html', context)

@require_http_methods(["POST"])
def start_scraping(request):
    """🔥 SMART SCRAPER - Keywords + Location → Auto URLs!"""
    # 🔥 NEW FIELDS: keywords + location instead of filtered_url
    keywords = request.POST.get('keywords', '').strip()
    location = request.POST.get('location', '').strip()
    platform = request.POST.get('platform', 'indeed')
    num_jobs = request.POST.get('num_jobs', '5')
    
    print(f"📥 Received: keywords='{keywords}', location='{location}', platform='{platform}'")
    
    # 🔥 VALIDATION
    errors = []
    if not keywords:
        errors.append('Enter job keywords (e.g. python, c++, backend)')
    if not location:
        errors.append('Select or enter location')
    if platform not in ['indeed', 'linkedin', 'glassdoor']:
        errors.append('Invalid platform')
    
    try:
        num_jobs = int(num_jobs)
        if num_jobs < 1 or num_jobs > 50:
            errors.append('Jobs: 1-50 only')
    except ValueError:
        errors.append('Invalid job count')
    
    if errors:
        for error in errors:
            messages.error(request, error)
        return redirect('dashboard')
    
    # 🔥 AUTO-GENERATE URL using JobScraper utility
    try:
        filtered_url = JobScraper.generate_search_url(keywords, location, platform)
        print(f"🌐 AUTO-GENERATED URL: {filtered_url}")
    except Exception as e:
        messages.error(request, f'URL generation failed: {e}')
        return redirect('dashboard')
    
    # 🔥 START SCRAPING with generated URL
    task = scrape_jobs_task.delay(platform, filtered_url, num_jobs)
    messages.success(request, 
        f'🚀 Scraping {num_jobs} {keywords} jobs in {location} from {platform}! '
        f'Task: <code>{task.id}</code><br>URL: <code>{filtered_url[:80]}...</code>'
    )
    
    return redirect('/?task_id=' + task.id)

def job_detail(request, job_id):
    """View single job with full details"""
    job = get_object_or_404(Job, id=job_id)
    context = {'job': job}
    return render(request, 'job_detail.html', context)
