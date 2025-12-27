# scraper/tasks.py
from celery import shared_task

@shared_task(bind=True)
def scrape_jobs_task(self, platform, filtered_url, num_jobs):
    print(f"🚀 Pure Python scraping: {platform}")
    try:
        from .services import JobScraper
        scraper = JobScraper()
        jobs_saved = scraper.scrape_jobs(platform, filtered_url, num_jobs)
        print(f"✅ {jobs_saved} jobs scraped!")
        return jobs_saved
    except Exception as e:
        print(f"❌ Error: {e}")
        raise e



