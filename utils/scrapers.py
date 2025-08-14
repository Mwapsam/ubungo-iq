"""
Web scrapers for various e-commerce and B2B platforms.
"""
import re
import time
import logging
import requests
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from django.utils import timezone

logger = logging.getLogger(__name__)


class BaseScraper:
    """Base class for all website scrapers."""
    
    def __init__(self, source_config):
        self.source = source_config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': source_config.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
    def delay(self):
        """Add delay between requests."""
        time.sleep(self.source.request_delay_seconds)
    
    def get_page(self, url: str, **kwargs) -> Optional[BeautifulSoup]:
        """Fetch and parse a webpage."""
        try:
            self.delay()
            response = self.session.get(url, timeout=30, **kwargs)
            response.raise_for_status()
            
            return BeautifulSoup(response.content, 'html.parser')
            
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def extract_text(self, element, default: str = "") -> str:
        """Safely extract text from BeautifulSoup element."""
        if element:
            return element.get_text(strip=True)
        return default
    
    def extract_number(self, text: str) -> Optional[int]:
        """Extract first number from text."""
        if not text:
            return None
        
        match = re.search(r'[\d,]+', text.replace(',', ''))
        if match:
            return int(match.group().replace(',', ''))
        return None
    
    def extract_price(self, text: str) -> Optional[str]:
        """Extract price from text."""
        if not text:
            return None
            
        # Look for price patterns like $1.99, €2.50, £3.00, ¥100
        price_patterns = [
            r'[$€£¥]\s*[\d,]+\.?\d*',
            r'[\d,]+\.?\d*\s*[$€£¥]',
            r'USD\s*[\d,]+\.?\d*',
            r'[\d,]+\.?\d*\s*USD',
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group().strip()
        
        return text[:50] if text else None  # Return first 50 chars as fallback
    
    def scrape(self) -> Dict[str, Any]:
        """Override in subclasses to implement specific scraping logic."""
        raise NotImplementedError


class AlibabaScraper(BaseScraper):
    """Scraper for Alibaba B2B platform."""
    
    def scrape(self) -> Dict[str, Any]:
        """Scrape Alibaba for B2B products and suppliers."""
        results = {
            'items': [],
            'categories': [],
            'trends': [],
            'errors': []
        }
        
        try:
            # Scrape popular categories first
            categories_url = "https://www.alibaba.com/trade/search"
            popular_searches = [
                "electronics", "clothing", "machinery", "home-garden", 
                "sports-entertainment", "automobiles", "beauty-personal-care"
            ]
            
            for search_term in popular_searches[:3]:  # Limit for demo
                search_url = f"https://www.alibaba.com/trade/search?fsb=y&IndexArea=product_en&CatId=&SearchText={search_term}"
                
                soup = self.get_page(search_url)
                if not soup:
                    continue
                
                # Extract product listings
                product_cards = soup.find_all('div', {'class': re.compile(r'organic-list-item')})
                
                for card in product_cards[:10]:  # Limit items per search
                    try:
                        item = self.extract_alibaba_product(card, search_term)
                        if item:
                            results['items'].append(item)
                    except Exception as e:
                        results['errors'].append(f"Error extracting product: {e}")
                        
        except Exception as e:
            results['errors'].append(f"General scraping error: {e}")
            
        return results
    
    def extract_alibaba_product(self, card_element, category: str) -> Optional[Dict]:
        """Extract product info from Alibaba product card."""
        try:
            # Title and link
            title_elem = card_element.find('a', {'class': re.compile(r'elements-title-normal')})
            if not title_elem:
                return None
                
            title = self.extract_text(title_elem)
            product_url = urljoin("https://www.alibaba.com", title_elem.get('href', ''))
            
            # Price
            price_elem = card_element.find('span', {'class': re.compile(r'price-current')})
            price = self.extract_text(price_elem) if price_elem else ""
            
            # Supplier info
            supplier_elem = card_element.find('a', {'class': re.compile(r'supplier')})
            supplier = self.extract_text(supplier_elem) if supplier_elem else ""
            
            # MOQ (Minimum Order Quantity)
            moq_elem = card_element.find('span', string=re.compile(r'piece|pieces|unit'))
            moq = self.extract_text(moq_elem) if moq_elem else ""
            
            # Generate external ID from URL
            external_id = re.search(r'/([0-9]+)\.html', product_url)
            external_id = external_id.group(1) if external_id else str(hash(product_url))
            
            return {
                'external_id': external_id,
                'title': title,
                'url': product_url,
                'description': f"Supplier: {supplier}. MOQ: {moq}",
                'price': price,
                'category': category,
                'tags': f"b2b, wholesale, {category}",
                'raw_data': {
                    'supplier': supplier,
                    'moq': moq,
                    'scraped_from': 'alibaba'
                }
            }
            
        except Exception as e:
            logger.error(f"Error extracting Alibaba product: {e}")
            return None


class GlobalTradeScraper(BaseScraper):
    """Scraper for GlobalTrade.net platform."""
    
    def scrape(self) -> Dict[str, Any]:
        """Scrape GlobalTrade for trade services and suppliers."""
        results = {
            'items': [],
            'categories': [],
            'trends': [],
            'errors': []
        }
        
        try:
            # Sample categories to scrape
            categories = ["exporters", "importers", "manufacturers", "suppliers"]
            
            for category in categories[:2]:  # Limit for demo
                category_url = f"https://www.globaltrade.net/{category}/"
                
                soup = self.get_page(category_url)
                if not soup:
                    continue
                
                # Find company/service listings
                listings = soup.find_all('div', {'class': re.compile(r'company|listing|item')})
                
                for listing in listings[:8]:  # Limit items
                    try:
                        item = self.extract_globaltrade_item(listing, category)
                        if item:
                            results['items'].append(item)
                    except Exception as e:
                        results['errors'].append(f"Error extracting item: {e}")
                        
        except Exception as e:
            results['errors'].append(f"GlobalTrade scraping error: {e}")
            
        return results
    
    def extract_globaltrade_item(self, listing_element, category: str) -> Optional[Dict]:
        """Extract company/service info from GlobalTrade listing."""
        try:
            # Company name and link
            name_elem = listing_element.find('a')
            if not name_elem:
                return None
                
            title = self.extract_text(name_elem)
            if not title:
                return None
                
            url = urljoin("https://www.globaltrade.net", name_elem.get('href', ''))
            
            # Description
            desc_elem = listing_element.find('p') or listing_element.find('div', string=True)
            description = self.extract_text(desc_elem)
            
            # Location/country
            location_elem = listing_element.find('span', string=re.compile(r'Country|Location'))
            location = self.extract_text(location_elem) if location_elem else ""
            
            # Generate external ID
            external_id = str(hash(f"{title}_{url}"))[:12]
            
            return {
                'external_id': external_id,
                'title': title,
                'url': url,
                'description': f"{description} Location: {location}",
                'price': "",  # Not applicable for services
                'category': f"trade-{category}",
                'tags': f"trade, {category}, b2b, international",
                'raw_data': {
                    'location': location,
                    'service_type': category,
                    'scraped_from': 'globaltrade'
                }
            }
            
        except Exception as e:
            logger.error(f"Error extracting GlobalTrade item: {e}")
            return None


class EtsyScraper(BaseScraper):
    """Scraper for Etsy marketplace."""
    
    def scrape(self) -> Dict[str, Any]:
        """Scrape Etsy for trending products and shops."""
        results = {
            'items': [],
            'categories': [],
            'trends': [],
            'errors': []
        }
        
        try:
            # Popular Etsy categories
            trending_searches = [
                "handmade jewelry", "custom gifts", "vintage decor", 
                "digital prints", "craft supplies"
            ]
            
            for search_term in trending_searches[:3]:  # Limit searches
                search_url = f"https://www.etsy.com/search?q={search_term.replace(' ', '%20')}"
                
                soup = self.get_page(search_url)
                if not soup:
                    continue
                
                # Extract product listings
                product_items = soup.find_all('div', {'data-test-id': 'listing-card'})
                
                for item in product_items[:8]:  # Limit items per search
                    try:
                        product = self.extract_etsy_product(item, search_term)
                        if product:
                            results['items'].append(product)
                    except Exception as e:
                        results['errors'].append(f"Error extracting Etsy product: {e}")
                        
        except Exception as e:
            results['errors'].append(f"Etsy scraping error: {e}")
            
        return results
    
    def extract_etsy_product(self, item_element, category: str) -> Optional[Dict]:
        """Extract product info from Etsy product card."""
        try:
            # Title and link
            title_elem = item_element.find('a', {'data-test-id': 'listing-link'})
            if not title_elem:
                return None
                
            title = title_elem.get('title') or self.extract_text(title_elem)
            product_url = urljoin("https://www.etsy.com", title_elem.get('href', ''))
            
            # Price
            price_elem = item_element.find('span', {'class': re.compile(r'price')})
            price = self.extract_text(price_elem) if price_elem else ""
            
            # Shop/seller
            shop_elem = item_element.find('span', string=re.compile(r'Ad by|From'))
            shop = self.extract_text(shop_elem) if shop_elem else ""
            
            # Rating/reviews
            rating_elem = item_element.find('span', {'class': re.compile(r'rating|review')})
            rating = self.extract_text(rating_elem) if rating_elem else ""
            
            # Extract ID from URL
            external_id = re.search(r'/listing/([0-9]+)', product_url)
            external_id = external_id.group(1) if external_id else str(hash(product_url))[:12]
            
            return {
                'external_id': external_id,
                'title': title,
                'url': product_url,
                'description': f"Shop: {shop}. Rating: {rating}",
                'price': price,
                'category': f"etsy-{category.replace(' ', '-')}",
                'tags': f"handmade, etsy, {category}",
                'raw_data': {
                    'shop': shop,
                    'rating': rating,
                    'scraped_from': 'etsy'
                }
            }
            
        except Exception as e:
            logger.error(f"Error extracting Etsy product: {e}")
            return None


class ScraperFactory:
    """Factory to create appropriate scraper instances."""
    
    SCRAPERS = {
        'alibaba': AlibabaScraper,
        'globaltrade': GlobalTradeScraper,
        'etsy': EtsyScraper,
    }
    
    @classmethod
    def create_scraper(cls, source_config) -> Optional[BaseScraper]:
        """Create scraper instance for given source."""
        scraper_class = cls.SCRAPERS.get(source_config.website)
        if scraper_class:
            return scraper_class(source_config)
        
        logger.error(f"No scraper found for website: {source_config.website}")
        return None