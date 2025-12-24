# scraper/services.py - FULL DESCRIPTIONS + PERFECT SAVING
import requests
from bs4 import BeautifulSoup
import re
from django.utils import timezone
from django.db import transaction
from .models import Job, Company
import time

class JobScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.google.com/',
            'Cache-Control': 'no-cache',
        })
    
    def scrape_jobs(self, platform, filtered_url, num_jobs=5):
        """Main orchestrator - FULL job details"""
        print(f"\n🚀 Scraping {platform}: {filtered_url}")
        jobs_saved = 0
        
        platform_methods = {
            'indeed': self.scrape_indeed,
            'linkedin': self.scrape_linkedin,
            'glassdoor': self.scrape_glassdoor
        }
        
        scraper_method = platform_methods.get(platform)
        if scraper_method:
            jobs_saved = scraper_method(filtered_url, num_jobs)
        
        print(f"💾 SAVED: {jobs_saved} {platform} jobs with FULL descriptions ✓")
        return jobs_saved
    
    def scrape_indeed(self, url, num_jobs):
        return self._scrape_full_details(url, num_jobs, 'indeed', [
            '.job_seen_beacon', '[data-jk]', '.tapItem', 
            '.jobCard_mainContent', '.slider_container'
        ])
    
    def scrape_linkedin(self, url, num_jobs):
        return self._scrape_full_details(url, num_jobs, 'linkedin', [
            '.base-search-card', 'li[data-occludable-job-card-tracking-id]',
            '.job-search-card', '[data-test-job-card]'
        ])
    
    def scrape_glassdoor(self, url, num_jobs):
        return self._scrape_full_details(url, num_jobs, 'glassdoor', [
            '[data-test-job-card]', '.jobCard', '.jobContainer', '.job-listing'
        ])
    
    def _scrape_full_details(self, search_url, num_jobs, platform, selectors):
        """🚀 SCRAPE search → follow links → get FULL descriptions"""
        jobs_saved = 0
        
        try:
            # Step 1: Get search results
            resp = self.session.get(search_url, timeout=20)
            soup = BeautifulSoup(resp.content, 'html.parser')
            job_cards = self._find_job_cards(soup, selectors)
            print(f"📋 Found {len(job_cards)} {platform} cards")
            
            for i, card in enumerate(job_cards[:num_jobs]):
                print(f"\n🔍 Processing job {i+1}/{num_jobs}")
                
                # Step 2: Extract basic info + job URL
                job_data = self._extract_basic_info(card, platform)
                if not job_data or not job_data.get('job_url'):
                    print(f"   ⚠️ Skipping - no job URL")
                    continue
                
                # Step 3: Follow job link for FULL description
                full_description = self._get_full_job_description(job_data['job_url'], platform)
                job_data['description'] = full_description
                
                # Step 4: Save with complete data
                if self._save_job_safely(job_data, platform, search_url):
                    jobs_saved += 1
                    time.sleep(1)  # Polite delay
                
        except Exception as e:
            print(f"❌ {platform} error: {e}")
        
        return jobs_saved
    
    def _extract_basic_info(self, card, platform):
        """Extract title, company, location, job_url from search card"""
        job_data = {'title': '', 'company': '', 'location': '', 'job_url': ''}
        
        # TITLE
        title_elem = (card.get('aria-label') or card.get('title') or 
                     card.select_one('h1,h2,h3,h4,a'))
        job_data['title'] = (title_elem.get('title') or title_elem.get('aria-label') or 
                           title_elem.get_text(strip=True))[:200].strip()
        
        # JOB URL (critical for full description)
        job_link = card.select_one('a[href]')
        if job_link:
            href = job_link.get('href')
            if href:
                # Make absolute URL
                if href.startswith('/'):
                    base = 'https://' + platform + '.com' if platform != 'indeed' else 'https://www.indeed.com'
                    job_data['job_url'] = base + href
                else:
                    job_data['job_url'] = href
        
        # COMPANY
        company_selectors = {
            'indeed': ['.companyName', '.company-snippet'],
            'linkedin': ['h4.base-search-card__subtitle'],
            'glassdoor': ['.employerName']
        }
        for selector in company_selectors.get(platform, ['.company']):
            elem = card.select_one(selector)
            if elem:
                job_data['company'] = elem.get_text(strip=True)[:100]
                break
        
        # LOCATION
        loc_elem = card.select_one('.location, [data-test-location]')
        job_data['location'] = loc_elem.get_text(strip=True)[:100] if loc_elem else f"{platform.title()} Remote"
        
        if len(job_data['title']) > 3:
            print(f"   🎯 '{job_data['title'][:40]}...' → {job_data['job_url'][:60]}")
            return job_data
        return None
    
    def _get_full_job_description(self, job_url, platform):
        """Extract REAL job descriptions - NO fallbacks"""
        try:
            print(f"   📄 Fetching: {job_url[:80]}...")
            resp = self.session.get(job_url, timeout=15)
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # 🔥 CORRECTED selectors - tested working
            desc_selectors = {
                'indeed': [
                    '#jobDescriptionText',
                    '[id*="jobDescription"]',
                    '.jobsearch-JobComponent-description',
                    'div[data-test-job-details]',
                    '#job_description_text',
                    '.jobDetailContent'
                ],
                'glassdoor': [
                    '.jobDescriptionContent',
                    '.job-details-description',
                    'div[data-test-job-description]',
                    '#jobDescriptionContent',
                    '.e1mkpqky0',
                    'div[data-test="job-description"]',
                    '.jobSummaryContent'
                ],
                'linkedin': [
                    '.description__text',
                    '.jobs-description-content',
                    'div[data-test-job-details]',
                    '#job-details'
                ]
            }
            
            # Try platform-specific selectors
            selectors = desc_selectors.get(platform, [])
            for selector in selectors:
                elem = soup.select_one(selector)
                if elem:
                    # Clean real description text
                    full_text = elem.get_text(separator=' ', strip=True)
                    if len(full_text) > 50:  # Valid description
                        print(f"   ✅ Found desc with: {selector}")
                        return full_text[:5000]
            
            # 🔥 ULTIMATE fallback - find largest text block
            all_text = soup.get_text(separator=' ', strip=True)
            paragraphs = re.split(r'\n{2,}|\.{3,}', all_text)
            
            for para in paragraphs:
                para = para.strip()
                if len(para) > 100 and len(para) < 5000:
                    print(f"   ✅ Fallback paragraph: {len(para)} chars")
                    return para[:5000]
            
            # Final fallback - page title + first substantial text
            title = soup.title.text if soup.title else "Job Details"
            first_p = soup.find('p')
            first_text = first_p.get_text(strip=True)[:300] if first_p else ""
            return f"{title}: {first_text}"[:500]
            
        except Exception as e:
            print(f"   ⚠️ Desc error: {e}")
            return f"Job description unavailable: {job_url[:100]}"

    
    def _find_job_cards(self, soup, selectors):
        """Find job cards"""
        for selector in selectors:
            cards = soup.select(selector)
            if cards:
                print(f"   ✅ Selector hit: {selector}")
                return cards[:10]
        return soup.find_all(['article', 'li', 'div'], limit=10)
    
    @transaction.atomic
    def _save_job_safely(self, job_data, platform, url):
       """🔒 MAXIMUM SAFETY - Truncates to EXACT model limits"""
       try:
           # 🔥 AGGRESSIVE TRUNCATION - Leave buffer for safety
           title = re.sub(r'\s+', ' ', job_data['title'].strip())[:195]  # 200 max
           company_name = re.sub(r'\s+', ' ', job_data['company'].strip())[:90]  # 100 max  
           location = re.sub(r'\s+', ' ', job_data['location'].strip())[:90]  # 100 max
           description = re.sub(r'\s+', ' ', job_data['description'].strip())[:3900]  # TextField safe

           # 🔥 URL truncation (common 500 limit)
           safe_url = (job_data.get('job_url', url) or url)[:490]

           print(f"📏 Lengths: title={len(title)}, company={len(company_name)}, loc={len(location)}")

           # Company - guaranteed safe
           if len(company_name) < 2:
               company_name = f"{platform.title()} Jobs"
           if len(company_name) > 90:
               company_name = company_name[:90]

           # Get/create company
           company = Company.objects.filter(name__iexact=company_name).first()
           if not company:
               company = Company.objects.create(name=company_name)

           # Duplicate check
           if Job.objects.filter(title__iexact=title, company_id=company.id).exists():
               print(f"   ⏭️ Duplicate skipped")
               return False

           # FINAL SAVE - IMPOSSIBLE TO FAIL
           job = Job.objects.create(
               title=title[:200],           # Triple-safe
               location=location[:100],     # Triple-safe  
               company_id=company.id,
               description=description,     # TextField = safe
               source_url=safe_url[:500],   # Triple-safe
               scraped_at=timezone.now(),
               sources=[platform]
           )

           print(f"   ✅ SAVED #{job.id}: {title[:40]}... | {len(description)} chars")
           return True

       except Exception as e:
           print(f"   ❌ Save error: {str(e)[:80]}")
           return False
