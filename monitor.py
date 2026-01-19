"""
WhatsApp IT Job Monitor - Complete Backend
Monitors WhatsApp Web for ALL IT-related job postings
"""

import time
import json
import re
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pytesseract
from PIL import Image
import requests

class WhatsAppJobMonitor:
    def __init__(self, group_name: str, output_file: str = "jobs_data.json"):
        self.group_name = group_name
        self.output_file = output_file
        self.jobs = []
        self.processed_messages = set()
        self.driver = None
        
        # COMPREHENSIVE IT KEYWORDS - Catches ALL IT jobs
        self.it_keywords = [
            # Programming Languages
            'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'php', 
            'ruby', 'go', 'golang', 'rust', 'swift', 'kotlin', 'scala', 'perl',
            'r programming', 'matlab', 'sql', 'html', 'css', 'dart', 'elixir',
            
            # Frameworks & Libraries
            'react', 'angular', 'vue', 'svelte', 'django', 'flask', 'fastapi',
            'spring', 'node.js', 'express', 'laravel', 'rails', 'asp.net',
            'next.js', 'nuxt', 'jquery', 'bootstrap', 'tailwind',
            
            # Mobile Development
            'android', 'ios', 'flutter', 'react native', 'xamarin', 'ionic',
            'mobile app', 'mobile development',
            
            # Web Development
            'frontend', 'front-end', 'backend', 'back-end', 'fullstack', 
            'full-stack', 'web developer', 'web development', 'ui/ux',
            'responsive design', 'progressive web app', 'pwa',
            
            # DevOps & Cloud
            'devops', 'aws', 'azure', 'gcp', 'google cloud', 'kubernetes',
            'docker', 'jenkins', 'gitlab', 'github actions', 'ci/cd',
            'terraform', 'ansible', 'puppet', 'chef', 'cloudformation',
            'microservices', 'serverless', 'lambda',
            
            # Databases
            'database', 'sql', 'mysql', 'postgresql', 'mongodb', 'redis',
            'elasticsearch', 'cassandra', 'dynamodb', 'oracle', 'mariadb',
            'nosql', 'sql server', 'sqlite', 'firestore', 'bigquery',
            
            # Data Science & AI
            'data scientist', 'data analyst', 'data engineer', 'machine learning',
            'ml engineer', 'ai', 'artificial intelligence', 'deep learning',
            'neural network', 'tensorflow', 'pytorch', 'scikit-learn',
            'data mining', 'big data', 'hadoop', 'spark', 'kafka',
            'data visualization', 'tableau', 'power bi', 'looker',
            
            # Software Engineering
            'software engineer', 'software developer', 'programmer',
            'developer', 'engineer', 'coder', 'technical lead', 'tech lead',
            'architect', 'solutions architect', 'system architect',
            
            # QA & Testing
            'qa engineer', 'quality assurance', 'tester', 'test engineer',
            'automation testing', 'selenium', 'cypress', 'jest', 'mocha',
            'unit testing', 'integration testing', 'performance testing',
            
            # Security
            'cybersecurity', 'security engineer', 'infosec', 'penetration testing',
            'ethical hacking', 'security analyst', 'soc analyst', 'ciso',
            'vulnerability assessment', 'network security',
            
            # Networking & Systems
            'network engineer', 'system administrator', 'sysadmin', 'linux admin',
            'windows admin', 'network administrator', 'it support', 'helpdesk',
            'infrastructure', 'server', 'networking',
            
            # Project Management & Agile
            'scrum master', 'product owner', 'project manager', 'agile',
            'scrum', 'kanban', 'jira', 'product manager', 'technical pm',
            
            # Design
            'ui designer', 'ux designer', 'product designer', 'graphic designer',
            'web designer', 'figma', 'sketch', 'adobe xd', 'photoshop',
            
            # Blockchain & Emerging Tech
            'blockchain', 'web3', 'cryptocurrency', 'solidity', 'ethereum',
            'smart contract', 'defi', 'nft',
            
            # ERP & Business Systems
            'sap', 'oracle', 'salesforce', 'erp', 'crm', 'dynamics 365',
            'workday', 'servicenow',
            
            # General IT Terms
            'it', 'information technology', 'tech', 'technology', 'software',
            'hardware', 'computer', 'coding', 'programming', 'development',
            'digital', 'api', 'rest api', 'graphql', 'microservice',
            'version control', 'git', 'code review', 'debugging',
            
            # Job Titles
            'cto', 'cio', 'vp engineering', 'engineering manager',
            'team lead', 'senior developer', 'junior developer',
            'intern developer', 'graduate developer'
        ]
        
        # Job-related keywords (more comprehensive)
        self.job_keywords = [
            # Direct job terms
            'hiring', 'vacancy', 'vacancies', 'position', 'opening', 'opportunity',
            'job', 'role', 'career', 'recruitment', 'recruiting', 'recruit',
            
            # Application terms
            'apply', 'application', 'resume', 'cv', 'curriculum vitae',
            'cover letter', 'portfolio', 'send cv', 'submit resume',
            
            # Urgency & Status
            'urgent', 'urgently', 'immediately', 'asap', 'now hiring',
            'we are hiring', 'looking for', 'seeking', 'required',
            'wanted', 'need', 'join our team', 'join us',
            
            # Employment type
            'full-time', 'full time', 'fulltime', 'part-time', 'part time',
            'parttime', 'contract', 'freelance', 'remote', 'onsite',
            'on-site', 'hybrid', 'work from home', 'wfh', 'permanent',
            'temporary', 'internship', 'intern',
            
            # Compensation
            'salary', 'compensation', 'package', 'benefits', 'pay',
            'rate', 'per hour', 'per month', 'annual', 'ksh', 'usd',
            'competitive salary', 'attractive package',
            
            # Experience
            'experience', 'years', 'yrs', 'senior', 'junior', 'entry level',
            'mid-level', 'expert', 'fresher', 'graduate',
            
            # Location
            'nairobi', 'mombasa', 'kisumu', 'location', 'based in',
            'office', 'workplace'
        ]
        
        # Create directories
        Path("screenshots").mkdir(exist_ok=True)
        Path("extracted_images").mkdir(exist_ok=True)
        
    def setup_driver(self):
        """Setup Chrome WebDriver"""
        print("Setting up Chrome WebDriver...")
        
        options = webdriver.ChromeOptions()
        # Use absolute path for session directory
        session_dir = Path("whatsapp_session").absolute()
        options.add_argument(f'--user-data-dir={session_dir}')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        try:
            # Try with webdriver-manager first
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            print("✓ Chrome driver loaded with webdriver-manager")
        except Exception as e:
            print(f"Trying direct Chrome driver...")
            try:
                self.driver = webdriver.Chrome(options=options)
                print("✓ Chrome driver loaded directly")
            except Exception as e2:
                print(f"\n✗ Error: {e2}")
                print("\n⚠️  SOLUTION:")
                print("1. Close ALL Chrome windows")
                print("2. Delete whatsapp_session folder:")
                print("   rmdir /s whatsapp_session  (Windows)")
                print("   rm -rf whatsapp_session    (Mac/Linux)")
                print("3. Run python monitor.py again")
                return False
        
        self.driver.get('https://web.whatsapp.com')
        
        print("\n" + "="*60)
        print("SCAN QR CODE IN THE BROWSER WINDOW")
        print("="*60)
        print("\n📱 Steps:")
        print("1. Look at the Chrome window - do you see a QR code?")
        print("2. Open WhatsApp on your phone")
        print("3. Tap ⋮ (three dots) → Linked Devices")
        print("4. Tap 'Link a Device'")
        print("5. Scan the QR code")
        print("\n⏳ After scanning, WAIT for chats to appear in Chrome")
        print("⏳ When you see your chats, press ENTER here...")
        
        input()  # Wait for user to press Enter
        
        print("\n✓ Checking if WhatsApp loaded...")
        
        # Try multiple selectors to detect WhatsApp Web
        selectors = [
            '[data-testid="chat-list"]',
            '#pane-side',
            '[data-testid="conversation-panel"]',
            '[role="navigation"]',
            'div[id="app"]',
            '._3AwIN'  # WhatsApp container class
        ]
        
        for selector in selectors:
            try:
                element = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                if element:
                    print(f"✓ WhatsApp Web loaded successfully! (detected: {selector})")
                    # Give it a few more seconds to fully load
                    time.sleep(3)
                    return True
            except:
                continue
        
        # If all selectors fail, ask user
        print("\n⚠️  Could not auto-detect WhatsApp Web loading")
        print("\n❓ Can you see your WhatsApp chats in the Chrome window?")
        print("   Type 'yes' if you see chats, or 'no' if not: ", end='')
        
        response = input().strip().lower()
        
        if response in ['yes', 'y', 'yeah', 'yep']:
            print("✓ Great! Continuing with manual confirmation...")
            time.sleep(2)
            return True
        else:
            print("\n✗ WhatsApp Web not loaded")
            print("\n⚠️  Troubleshooting:")
            print("1. Make sure you scanned the QR code correctly")
            print("2. Check your phone is connected to internet")
            print("3. Try closing Chrome and running again:")
            print("   taskkill /F /IM chrome.exe")
            print("   rmdir /s whatsapp_session")
            print("   python monitor.py")
            return False
    
    def open_group(self):
        """Open WhatsApp group"""
        print(f"\nSearching for group: {self.group_name}")
        
        try:
            # Click search box
            search_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="chat-list-search"]'))
            )
            search_box.click()
            time.sleep(1)
            
            # Type in search
            search_input = self.driver.find_element(By.CSS_SELECTOR, 'div[contenteditable="true"][data-tab="3"]')
            search_input.send_keys(self.group_name)
            time.sleep(3)  # Wait for search results
            
            print("\n" + "="*60)
            print("MANUAL GROUP SELECTION")
            print("="*60)
            print(f"\n1. Look at Chrome window")
            print(f"2. Find 'SimpleHire⿧Marvel' group in the search results")
            print(f"3. CLICK on it with your mouse")
            print(f"4. Come back here and press ENTER\n")
            
            input("Press ENTER after clicking the group... ")
            
            print("✓ Group selected!")
            time.sleep(2)
            return True
                
        except Exception as e:
            print(f"✗ Error: {e}")
            print("\n⚠️  Try this:")
            print("1. In Chrome, click on SimpleHire Marvel group manually")
            print("2. Then run the script again")
            return False
    
    def is_it_job(self, text: str) -> bool:
        """Check if message is an IT job posting"""
        text_lower = text.lower()
        
        # Check for job keywords
        has_job_keyword = any(keyword in text_lower for keyword in self.job_keywords)
        
        # Check for IT keywords
        has_it_keyword = any(keyword in text_lower for keyword in self.it_keywords)
        
        # Return true if BOTH are present
        return has_job_keyword and has_it_keyword
    
    def extract_text_from_image(self, image_path: str) -> str:
        """Extract text from image using OCR"""
        try:
            img = Image.open(image_path)
            text = pytesseract.image_to_string(img)
            return text
        except Exception as e:
            print(f"Error extracting text: {e}")
            return ""
    
    def analyze_job(self, text: str, image_text: str = "") -> dict:
        """Extract job details from text"""
        combined = f"{text}\n{image_text}".lower()
        
        # Extract company
        company_patterns = [
            r'(?:company|organization|firm)[\s:]+([A-Z][A-Za-z\s&]+?)(?:\.|,|\n)',
            r'([A-Z][A-Za-z\s&]+?)(?:\s+is\s+(?:hiring|looking|seeking))'
        ]
        company = "Unknown Company"
        for pattern in company_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                company = match.group(1).strip()
                break
        
        # Extract title
        title_patterns = [
            r'(?:position|role|vacancy|hiring|looking for|seeking)[\s:]+([A-Za-z\s/]+?)(?:\n|\.|,|\||;)',
            r'([A-Za-z\s]+?(?:developer|engineer|analyst|designer|manager|administrator|architect|lead))',
        ]
        title = "IT Position"
        for pattern in title_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                break
        
        # Extract keywords that appear in the text
        found_keywords = [kw for kw in self.it_keywords if kw in combined]
        
        # Determine job type
        job_type = "fulltime"
        if any(term in combined for term in ['contract', 'contractor']):
            job_type = "contract"
        elif any(term in combined for term in ['remote', 'work from home', 'wfh']):
            job_type = "remote"
        elif any(term in combined for term in ['part-time', 'part time', 'parttime']):
            job_type = "parttime"
        elif any(term in combined for term in ['intern', 'internship']):
            job_type = "internship"
        
        return {
            "title": title[:150],
            "company": company[:100],
            "keywords": list(set(found_keywords[:15])),
            "type": job_type
        }
    
    def download_image(self, img_element, message_id: str) -> str:
        """Download image from message"""
        try:
            img_path = f"screenshots/job_{message_id}.png"
            img_element.screenshot(img_path)
            return img_path
        except Exception as e:
            print(f"Error downloading image: {e}")
            return ""
    
    def scan_existing_messages(self):
        """Scan all existing messages in the group (history)"""
        print("\n" + "="*60)
        print("SCANNING EXISTING MESSAGES...")
        print("="*60)
        print("Scrolling to load all messages...")
        
        # Scroll up to load older messages
        try:
            chat_container = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="conversation-panel-body"]')
            
            # Scroll up multiple times to load history
            for i in range(10):  # Scroll 10 times to load more messages
                self.driver.execute_script("arguments[0].scrollTop = 0", chat_container)
                time.sleep(1)
                print(f"Scrolling... {i+1}/10")
        except:
            print("⚠️  Could not scroll, will scan visible messages only")
        
        print("\nScanning all visible messages for IT jobs...")
        
        # Get all messages
        try:
            messages = self.driver.find_elements(By.CSS_SELECTOR, 'div[class*="message-"]')
            print(f"Found {len(messages)} messages to scan\n")
            
            scanned = 0
            for msg in messages:
                try:
                    msg_id = f"history_{scanned}"
                    
                    if msg_id in self.processed_messages:
                        continue
                    
                    # Extract text
                    text = ""
                    try:
                        text_elem = msg.find_element(By.CSS_SELECTOR, 'span.selectable-text')
                        text = text_elem.text
                    except:
                        pass
                    
                    if not text:
                        continue
                    
                    # Check for images
                    image_path = ""
                    image_text = ""
                    has_image = False
                    
                    try:
                        img = msg.find_element(By.CSS_SELECTOR, 'img[src*="blob:"], img[src*="http"]')
                        image_path = self.download_image(img, msg_id)
                        if image_path:
                            has_image = True
                            image_text = self.extract_text_from_image(image_path)
                    except:
                        pass
                    
                    full_text = f"{text}\n{image_text}"
                    
                    # Check if IT job
                    if self.is_it_job(full_text):
                        print(f"🎯 Found IT job: {text[:50]}...")
                        
                        analysis = self.analyze_job(text, image_text)
                        
                        job_entry = {
                            "id": len(self.jobs) + 1,
                            "title": analysis["title"],
                            "company": analysis["company"],
                            "description": text[:500],
                            "date": datetime.now().isoformat(),  # Using current time since we can't get original
                            "hasImage": has_image,
                            "imageUrl": image_path if has_image else "",
                            "type": analysis["type"],
                            "keywords": analysis["keywords"],
                            "full_text": full_text[:1000]
                        }
                        
                        self.jobs.append(job_entry)
                        self.processed_messages.add(msg_id)
                    
                    scanned += 1
                except Exception as e:
                    continue
            
            self.save_jobs()
            print(f"\n✓ Scan complete!")
            print(f"✓ Found {len(self.jobs)} IT jobs in history")
            print(f"✓ Scanned {scanned} messages\n")
            
        except Exception as e:
            print(f"Error scanning messages: {e}")
    
    def monitor_messages(self):
        """Monitor group messages"""
        print("\n" + "="*60)
        print("MONITORING NEW MESSAGES - DETECTING ALL IT JOBS")
        print("="*60)
        print(f"Group: {self.group_name}")
        print(f"IT Keywords: {len(self.it_keywords)} terms")
        print(f"Job Keywords: {len(self.job_keywords)} terms")
        print("Press Ctrl+C to stop\n")
        
        # Get current message count after scanning history
        last_count = len(self.driver.find_elements(By.CSS_SELECTOR, 'div[class*="message-"]'))
        
        try:
            while True:
                try:
                    messages = self.driver.find_elements(By.CSS_SELECTOR, 'div[class*="message-"]')
                    
                    if len(messages) > last_count:
                        new_messages = messages[last_count:]
                        
                        for msg in new_messages:
                            try:
                                msg_id = f"{int(time.time()*1000)}_{len(self.jobs)}"
                                
                                if msg_id in self.processed_messages:
                                    continue
                                
                                # Extract text
                                text = ""
                                try:
                                    text_elem = msg.find_element(By.CSS_SELECTOR, 'span.selectable-text')
                                    text = text_elem.text
                                except:
                                    pass
                                
                                # Check for images
                                image_path = ""
                                image_text = ""
                                has_image = False
                                
                                try:
                                    img = msg.find_element(By.CSS_SELECTOR, 'img[src*="blob:"], img[src*="http"]')
                                    image_path = self.download_image(img, msg_id)
                                    if image_path:
                                        has_image = True
                                        image_text = self.extract_text_from_image(image_path)
                                        print(f"📷 Image extracted")
                                except:
                                    pass
                                
                                full_text = f"{text}\n{image_text}"
                                
                                # Check if IT job
                                if self.is_it_job(full_text):
                                    print(f"\n🎯 IT JOB DETECTED!")
                                    print(f"Preview: {text[:80]}...")
                                    
                                    analysis = self.analyze_job(text, image_text)
                                    
                                    job_entry = {
                                        "id": len(self.jobs) + 1,
                                        "title": analysis["title"],
                                        "company": analysis["company"],
                                        "description": text[:500],
                                        "date": datetime.now().isoformat(),
                                        "hasImage": has_image,
                                        "imageUrl": image_path if has_image else "",
                                        "type": analysis["type"],
                                        "keywords": analysis["keywords"],
                                        "full_text": full_text[:1000]
                                    }
                                    
                                    self.jobs.append(job_entry)
                                    self.processed_messages.add(msg_id)
                                    self.save_jobs()
                                    
                                    print(f"✓ Saved: {analysis['title']} at {analysis['company']}")
                                    print(f"Total: {len(self.jobs)} jobs\n")
                            except Exception as e:
                                continue
                        
                        last_count = len(messages)
                    
                    time.sleep(2)
                except Exception as e:
                    print(f"Error in loop: {e}")
                    time.sleep(5)
        except KeyboardInterrupt:
            print("\n\n" + "="*60)
            print("MONITORING STOPPED")
            print(f"Total IT jobs found: {len(self.jobs)}")
            print(f"Saved to: {self.output_file}")
            print("="*60)
    
    def save_jobs(self):
        """Save jobs to file"""
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(self.jobs, f, indent=2, ensure_ascii=False)
    
    def load_existing_jobs(self):
        """Load existing jobs"""
        if Path(self.output_file).exists():
            with open(self.output_file, 'r', encoding='utf-8') as f:
                self.jobs = json.load(f)
                print(f"✓ Loaded {len(self.jobs)} existing jobs")
    
    def run(self):
        """Main run function"""
        print("\n" + "="*60)
        print("WhatsApp IT Job Monitor - MAXIMUM DETECTION")
        print("="*60 + "\n")
        
        self.load_existing_jobs()
        
        if not self.setup_driver():
            return
        
        try:
            if not self.open_group():
                print("Failed to open group")
                return
            
            # First, scan all existing messages (history)
            self.scan_existing_messages()
            
            # Then start monitoring new messages
            self.monitor_messages()
        finally:
            if self.driver:
                self.driver.quit()


if __name__ == "__main__":
    # CONFIGURE THIS - Your WhatsApp group name (NO EMOJIS!)
    GROUP_NAME = "SimpleHire Marvel"  # ← CHANGE THIS TO YOUR EXACT GROUP NAME
    
    print("\n⚙️  CONFIGURATION:")
    print(f"   Group Name: {GROUP_NAME}")
    print("\nStarting in 3 seconds...")
    time.sleep(3)
    
    monitor = WhatsAppJobMonitor(GROUP_NAME)
    monitor.run()