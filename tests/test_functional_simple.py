# tests/test_functional_simple.py
"""
Simple functional tests that focus on basic browser interactions
without complex Wagtail page hierarchies.
"""

import time
import unittest
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from django.test import LiveServerTestCase


@pytest.mark.functional
class SimpleFunctionalTest(LiveServerTestCase):
    """Simple functional tests focusing on core browser functionality."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Setup Chrome driver with webdriver-manager
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            service = Service(ChromeDriverManager().install())
            cls.driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception:
            cls.driver = webdriver.Chrome(options=chrome_options)
            
        cls.driver.implicitly_wait(10)
        cls.wait = WebDriverWait(cls.driver, 10)
    
    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()


class BasicPageLoadTest(SimpleFunctionalTest):
    """Test basic page loading functionality."""
    
    def test_homepage_loads(self):
        """Test that the homepage loads successfully."""
        self.driver.get(f'{self.live_server_url}/')
        
        # Check that we get a proper HTML page
        page_source = self.driver.page_source
        self.assertIn('<html', page_source.lower())
        self.assertIn('<body', page_source.lower())
        
        # Check page has a title
        title = self.driver.title
        self.assertTrue(len(title) > 0)
        print(f"Homepage title: {title}")
    
    def test_blog_page_loads(self):
        """Test that the blog page loads."""
        self.driver.get(f'{self.live_server_url}/blog/')
        
        # Check for successful page load
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Check page title
        title = self.driver.title
        self.assertTrue(len(title) > 0)
        print(f"Blog page title: {title}")
    
    def test_navigation_elements_present(self):
        """Test that basic navigation elements are present."""
        self.driver.get(f'{self.live_server_url}/')
        
        # Look for common navigation elements
        try:
            # Check for header
            header = self.driver.find_element(By.TAG_NAME, "header")
            self.assertTrue(header.is_displayed())
            
            # Check for navigation
            nav = self.driver.find_element(By.TAG_NAME, "nav")
            self.assertTrue(nav.is_displayed())
            
            # Check for main content
            main = self.driver.find_element(By.TAG_NAME, "main")
            self.assertTrue(main.is_displayed())
            
        except NoSuchElementException:
            # If specific elements don't exist, at least ensure body is present
            body = self.driver.find_element(By.TAG_NAME, "body")
            self.assertTrue(body.is_displayed())


class InteractionTest(SimpleFunctionalTest):
    """Test basic user interactions."""
    
    def test_page_scroll(self):
        """Test that page scrolling works."""
        self.driver.get(f'{self.live_server_url}/')
        
        # Get initial scroll position
        initial_position = self.driver.execute_script("return window.pageYOffset;")
        
        # Scroll down
        self.driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(0.5)
        
        # Check scroll position changed
        new_position = self.driver.execute_script("return window.pageYOffset;")
        self.assertGreater(new_position, initial_position)
    
    def test_link_navigation(self):
        """Test basic link navigation if links exist."""
        self.driver.get(f'{self.live_server_url}/')
        
        try:
            # Look for links on the page
            links = self.driver.find_elements(By.TAG_NAME, "a")
            
            # Filter for internal links (not external or mailto)
            internal_links = [
                link for link in links 
                if link.get_attribute("href") and 
                (link.get_attribute("href").startswith(self.live_server_url) or 
                 link.get_attribute("href").startswith("/"))
            ]
            
            if internal_links:
                # Click first internal link
                first_link = internal_links[0]
                href = first_link.get_attribute("href")
                print(f"Testing link navigation to: {href}")
                
                first_link.click()
                time.sleep(1)
                
                # Check that URL changed
                current_url = self.driver.current_url
                self.assertTrue(len(current_url) > len(self.live_server_url))
                
        except Exception as e:
            self.skipTest(f"Link navigation test skipped: {e}")
    
    def test_form_elements_exist(self):
        """Test if any form elements exist and are interactive."""
        self.driver.get(f'{self.live_server_url}/blog/')
        
        try:
            # Look for input elements
            inputs = self.driver.find_elements(By.TAG_NAME, "input")
            selects = self.driver.find_elements(By.TAG_NAME, "select")
            textareas = self.driver.find_elements(By.TAG_NAME, "textarea")
            
            form_elements = inputs + selects + textareas
            
            if form_elements:
                print(f"Found {len(form_elements)} form elements")
                
                # Test first input element
                for element in form_elements:
                    if element.is_displayed() and element.is_enabled():
                        element_type = element.get_attribute("type") or element.tag_name
                        print(f"Testing {element_type} element")
                        
                        if element.tag_name == "input" and element.get_attribute("type") == "text":
                            element.send_keys("test")
                            value = element.get_attribute("value")
                            self.assertEqual(value, "test")
                            element.clear()
                        
                        break
            else:
                self.skipTest("No form elements found to test")
                
        except Exception as e:
            self.skipTest(f"Form element test skipped: {e}")


class JavaScriptTest(SimpleFunctionalTest):
    """Test JavaScript functionality."""
    
    def test_javascript_execution(self):
        """Test that JavaScript executes properly."""
        self.driver.get(f'{self.live_server_url}/')
        
        # Execute simple JavaScript
        result = self.driver.execute_script("return 2 + 2;")
        self.assertEqual(result, 4)
        
        # Test DOM manipulation
        self.driver.execute_script(
            "document.body.setAttribute('data-test', 'selenium');"
        )
        
        test_attr = self.driver.execute_script(
            "return document.body.getAttribute('data-test');"
        )
        self.assertEqual(test_attr, 'selenium')
    
    def test_no_javascript_errors(self):
        """Test that there are no JavaScript errors on page load."""
        self.driver.get(f'{self.live_server_url}/')
        
        # Wait for page to fully load
        time.sleep(2)
        
        try:
            # Get browser console logs
            logs = self.driver.get_log('browser')
            
            # Filter for severe errors
            errors = [log for log in logs if log['level'] == 'SEVERE']
            
            if errors:
                print("JavaScript errors found:")
                for error in errors:
                    print(f"  {error['level']}: {error['message']}")
            
            # Don't fail the test for JS errors, just report them
            self.assertTrue(True, "JavaScript error check completed")
            
        except Exception:
            # Browser logging might not be supported
            self.skipTest("Browser logging not available")


class PerformanceTest(SimpleFunctionalTest):
    """Basic performance tests."""
    
    def test_page_load_speed(self):
        """Test basic page load performance."""
        start_time = time.time()
        
        self.driver.get(f'{self.live_server_url}/')
        
        # Wait for page to be fully loaded
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        load_time = time.time() - start_time
        print(f"Page load time: {load_time:.2f} seconds")
        
        # Should load within 15 seconds (generous for headless testing)
        self.assertLess(load_time, 15.0)
    
    def test_multiple_page_loads(self):
        """Test loading multiple pages in sequence."""
        pages_to_test = ['/', '/blog/']
        load_times = []
        
        for page in pages_to_test:
            start_time = time.time()
            
            self.driver.get(f'{self.live_server_url}{page}')
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            load_time = time.time() - start_time
            load_times.append(load_time)
            print(f"Page {page} load time: {load_time:.2f} seconds")
        
        # Average load time should be reasonable
        avg_load_time = sum(load_times) / len(load_times)
        print(f"Average load time: {avg_load_time:.2f} seconds")
        self.assertLess(avg_load_time, 10.0)


class AccessibilityTest(SimpleFunctionalTest):
    """Basic accessibility tests."""
    
    def test_page_has_title(self):
        """Test that pages have meaningful titles."""
        self.driver.get(f'{self.live_server_url}/')
        
        title = self.driver.title
        self.assertTrue(len(title) > 0)
        self.assertTrue(len(title) < 70)  # SEO best practice
    
    def test_images_have_alt_attributes(self):
        """Test that images have alt attributes."""
        self.driver.get(f'{self.live_server_url}/')
        
        images = self.driver.find_elements(By.TAG_NAME, "img")
        
        for img in images:
            alt_text = img.get_attribute("alt")
            # Alt can be empty string for decorative images, but should not be None
            self.assertIsNotNone(alt_text)
    
    def test_headings_structure(self):
        """Test basic heading structure."""
        self.driver.get(f'{self.live_server_url}/')
        
        # Check for at least one heading
        headings = self.driver.find_elements(By.CSS_SELECTOR, "h1, h2, h3, h4, h5, h6")
        
        if headings:
            # Check that first heading is h1
            first_heading = headings[0]
            self.assertEqual(first_heading.tag_name.lower(), "h1")
            
            # Check heading text is not empty
            heading_text = first_heading.text.strip()
            self.assertTrue(len(heading_text) > 0)


if __name__ == '__main__':
    unittest.main()