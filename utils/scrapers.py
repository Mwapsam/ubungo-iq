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
            popular_searches = [
                "electronics", "clothing", "machinery"
            ]
            
            for search_term in popular_searches[:2]:  # Test with fewer searches
                search_url = f"https://www.alibaba.com/trade/search?fsb=y&IndexArea=product_en&SearchText={search_term}"
                
                logger.info(f"Scraping URL: {search_url}")
                soup = self.get_page(search_url)
                if not soup:
                    results['errors'].append(f"Failed to get page for {search_term}")
                    continue
                
                logger.info(f"Page content length: {len(str(soup))}")
                
                # Try multiple possible selectors
                possible_selectors = [
                    'div[class*="organic-list-item"]',
                    'div[class*="item"]', 
                    'div[class*="product"]',
                    'article',
                    '.item-main',
                    '.product-item'
                ]
                
                product_cards = []
                for selector in possible_selectors:
                    cards = soup.select(selector)
                    if cards:
                        logger.info(f"Found {len(cards)} items with selector: {selector}")
                        product_cards = cards[:10]  # Take first 10
                        break
                
                if not product_cards:
                    # Log some sample HTML for debugging
                    sample_divs = soup.find_all('div')[:5]
                    div_classes = [div.get('class', []) for div in sample_divs]
                    results['errors'].append(f"No product cards found for {search_term}. Sample div classes: {div_classes}")
                    continue
                
                logger.info(f"Processing {len(product_cards)} product cards")
                
                for i, card in enumerate(product_cards[:5]):  # Limit items per search
                    try:
                        item = self.extract_alibaba_product(card, search_term)
                        if item:
                            logger.info(f"Extracted item {i+1}: {item['title']}")
                            results['items'].append(item)
                        else:
                            logger.info(f"Failed to extract item {i+1}")
                    except Exception as e:
                        error_msg = f"Error extracting product {i+1}: {e}"
                        logger.error(error_msg)
                        results['errors'].append(error_msg)
                        
        except Exception as e:
            error_msg = f"General scraping error: {e}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            
        return results
    
    def extract_alibaba_product(self, card_element, category: str) -> Optional[Dict]:
        """Extract product info from Alibaba product card."""
        try:
            # Try multiple strategies to find title and link
            title_elem = None
            title_selectors = [
                'a[class*="elements-title"]',
                'a[class*="title"]',
                'h3 a',
                'h4 a', 
                'a[href*="/product-detail/"]',
                'a[href*=".html"]'
            ]
            
            for selector in title_selectors:
                title_elem = card_element.select_one(selector)
                if title_elem:
                    break
            
            # If no specific title link, try any link
            if not title_elem:
                title_elem = card_element.find('a')
            
            if not title_elem:
                logger.info("No title element found")
                return None
                
            title = self.extract_text(title_elem)
            if not title:
                logger.info("No title text found")
                return None
                
            href = title_elem.get('href', '')
            if href.startswith('/'):
                product_url = f"https://www.alibaba.com{href}"
            elif href.startswith('http'):
                product_url = href
            else:
                product_url = f"https://www.alibaba.com/{href}"
            
            # Try multiple price selectors
            price = ""
            price_selectors = [
                'span[class*="price"]',
                '.price',
                '[class*="price"]'
            ]
            
            for selector in price_selectors:
                price_elem = card_element.select_one(selector)
                if price_elem:
                    price = self.extract_text(price_elem)
                    break
            
            # Try to find supplier/company name
            supplier = ""
            supplier_selectors = [
                'a[class*="supplier"]',
                '.supplier',
                '[class*="company"]'
            ]
            
            for selector in supplier_selectors:
                supplier_elem = card_element.select_one(selector)
                if supplier_elem:
                    supplier = self.extract_text(supplier_elem)
                    break
            
            # Generate external ID from URL or hash
            external_id = re.search(r'/([0-9]+)\.html', product_url)
            if external_id:
                external_id = external_id.group(1)
            else:
                external_id = str(abs(hash(f"{title}_{product_url}")))[:12]
            
            logger.info(f"Extracted: {title[:50]}...")
            
            return {
                'external_id': external_id,
                'title': title,
                'url': product_url,
                'description': f"Supplier: {supplier}" if supplier else title,
                'price': price,
                'category': category,
                'tags': f"b2b, wholesale, {category}",
                'raw_data': {
                    'supplier': supplier,
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


class DemoScraper(BaseScraper):
    """Enhanced demo scraper that generates comprehensive realistic data."""
    
    def scrape(self) -> Dict[str, Any]:
        """Generate comprehensive mock scraped data with all enhanced fields."""
        import random
        from decimal import Decimal
        from django.utils import timezone
        
        # Enhanced mock data by source
        mock_data = {
            'alibaba': {
                'categories': ['electronics', 'machinery', 'textiles', 'automotive', 'industrial-tools'],
                'titles': [
                    'High Quality LED Display Screen',
                    'Industrial Robot Arm Manufacturing Equipment',
                    'Cotton Fabric Wholesale Textile Material', 
                    'Auto Parts Engine Component OEM',
                    'Smart Phone Accessories Bulk Order',
                    'CNC Machining Center Equipment',
                    'Solar Panel Manufacturing Equipment',
                    'Pharmaceutical Packaging Machinery'
                ],
                'suppliers': [
                    {'name': 'Shenzhen Tech Co Ltd', 'country': 'China', 'region': 'Asia', 'years': 12, 'verified': True},
                    {'name': 'Beijing Manufacturing Corp', 'country': 'China', 'region': 'Asia', 'years': 8, 'verified': True},
                    {'name': 'Shanghai Industries Group', 'country': 'China', 'region': 'Asia', 'years': 15, 'verified': False},
                    {'name': 'Guangzhou Export Company', 'country': 'China', 'region': 'Asia', 'years': 6, 'verified': True}
                ],
                'materials': ['Aluminum Alloy', 'Stainless Steel', 'Carbon Fiber', 'ABS Plastic', 'Titanium', 'Copper'],
                'certifications': ['CE', 'ISO9001', 'RoHS', 'FCC', 'UL', 'CCC'],
                'ports': ['Shanghai', 'Shenzhen', 'Ningbo', 'Qingdao']
            },
            'etsy': {
                'categories': ['handmade-jewelry', 'custom-gifts', 'vintage-decor', 'art-collectibles', 'craft-supplies'],
                'titles': [
                    'Handcrafted Silver Ring Custom Design',
                    'Personalized Wedding Gift Set',
                    'Vintage Art Deco Home Decoration',
                    'Custom Name Necklace Jewelry',
                    'Boho Style Earrings Handmade',
                    'Organic Cotton Baby Blanket',
                    'Wooden Kitchen Utensil Set',
                    'Hand-painted Ceramic Mug'
                ],
                'suppliers': [
                    {'name': 'ArtisanCrafts Studio', 'country': 'USA', 'region': 'North America', 'years': 5, 'verified': True},
                    {'name': 'CustomCreations Workshop', 'country': 'Canada', 'region': 'North America', 'years': 3, 'verified': False},
                    {'name': 'VintageVibes Collection', 'country': 'UK', 'region': 'Europe', 'years': 7, 'verified': True},
                    {'name': 'HandmadeHaven', 'country': 'Australia', 'region': 'Oceania', 'years': 4, 'verified': True}
                ],
                'materials': ['Sterling Silver', 'Organic Cotton', 'Reclaimed Wood', 'Natural Gemstones', 'Eco-friendly Materials'],
                'certifications': ['Organic', 'Fair Trade', 'Handmade', 'Sustainable'],
                'colors': ['Natural', 'White', 'Black', 'Gold', 'Silver', 'Custom']
            },
            'globaltrade': {
                'categories': ['exporters', 'importers', 'manufacturers', 'trading-companies', 'logistics'],
                'titles': [
                    'Global Electronics Exporter',
                    'Food Product Importer',
                    'Textile Manufacturer',
                    'Chemical Products Trading Company',
                    'International Logistics Services',
                    'Medical Equipment Distributor',
                    'Agricultural Products Exporter'
                ],
                'suppliers': [
                    {'name': 'Global Trade Ltd', 'country': 'Singapore', 'region': 'Asia', 'years': 20, 'verified': True},
                    {'name': 'International Commerce Corp', 'country': 'Germany', 'region': 'Europe', 'years': 15, 'verified': True},
                    {'name': 'WorldWide Exports Inc', 'country': 'UAE', 'region': 'Middle East', 'years': 10, 'verified': False},
                    {'name': 'Pacific Trading Group', 'country': 'South Korea', 'region': 'Asia', 'years': 12, 'verified': True}
                ],
                'services': ['Export Services', 'Import Assistance', 'Quality Control', 'Logistics Management', 'Documentation'],
                'certifications': ['ISO9001', 'ISO14001', 'OHSAS18001', 'AEO'],
                'regions': ['Asia-Pacific', 'Europe', 'North America', 'Middle East', 'Africa']
            }
        }
        
        source_data = mock_data.get(self.source.website, mock_data['alibaba'])
        results = {'items': [], 'categories': [], 'trends': [], 'errors': []}
        
        # Generate 5-8 comprehensive mock items
        num_items = random.randint(5, 8)
        for i in range(num_items):
            category = random.choice(source_data['categories'])
            base_title = random.choice(source_data['titles'])
            supplier_info = random.choice(source_data['suppliers'])
            
            # Add variation to titles
            variations = ['Pro', 'Premium', 'Deluxe', 'Standard', 'Advanced', 'Industrial', 'Commercial']
            title = f"{base_title} {random.choice(variations)}"
            
            # Generate realistic pricing
            base_price = random.randint(50, 2000)
            current_price = Decimal(str(base_price + random.uniform(-20, 50)))
            original_price = current_price + Decimal(str(random.uniform(10, 100)))
            discount_pct = ((original_price - current_price) / original_price * 100) if original_price > current_price else 0
            
            # Generate MOQ and specifications
            moq = random.choice([1, 10, 50, 100, 500, 1000])
            units = random.choice(['pieces', 'sets', 'kg', 'meters', 'units', 'lots'])
            lead_time = random.randint(7, 30)
            
            # Generate bulk pricing tiers
            bulk_tiers = []
            if random.choice([True, False]):  # 50% chance of bulk pricing
                for qty in [100, 500, 1000]:
                    if qty >= moq:
                        tier_price = current_price * Decimal(str(random.uniform(0.8, 0.95)))
                        bulk_tiers.append({'quantity': qty, 'price': float(tier_price)})
            
            # Generate certifications and specifications
            certs = random.sample(source_data.get('certifications', []), random.randint(1, 3))
            material = random.choice(source_data.get('materials', ['High Quality Material']))
            dimensions = f"{random.randint(10, 100)}x{random.randint(10, 100)}x{random.randint(5, 50)}cm"
            
            # Generate customer feedback
            rating = round(random.uniform(3.5, 5.0), 1)
            rating_count = random.randint(5, 500)
            
            reviews_positive = ['Great quality', 'Fast shipping', 'Excellent service', 'Good value', 'Reliable supplier']
            reviews_negative = ['Slow delivery', 'Packaging issues', 'Communication delays', 'Quality inconsistent']
            review_highlights = random.sample(reviews_positive, random.randint(1, 3))
            complaints = random.sample(reviews_negative, random.randint(0, 2))
            
            # Generate market intelligence
            views = random.randint(50, 2000)
            sales = random.randint(10, 200)
            recent_orders = random.randint(5, 50)
            trending_rank = random.randint(1, 1000) if random.choice([True, False]) else None
            
            # Keywords and features
            keywords = [category.replace('-', ' '), 'wholesale', 'manufacturer', 'supplier', 'quality']
            features = ['High Quality', 'Factory Direct', 'Custom Design', 'OEM/ODM', 'Bulk Orders']
            
            # Shipping info
            shipping_cost = Decimal(str(random.uniform(50, 300)))
            shipping_methods = random.sample(['Air Express', 'Sea Freight', 'Land Transport'], random.randint(1, 2))
            
            external_id = f"demo_{self.source.website}_{i+1}_{random.randint(1000, 9999)}"
            
            # Build comprehensive item data
            item = {
                # Basic info
                'external_id': external_id,
                'title': title,
                'url': f"{self.source.base_url}/item/{external_id}",
                'description': f"Professional grade {category.replace('-', ' ')} from verified supplier. {' '.join(random.sample(features, 2))}.",
                'category': category,
                'tags': ', '.join(keywords),
                
                # Enhanced pricing data
                'current_price': float(current_price),
                'original_price': float(original_price),
                'discount_percentage': float(discount_pct),
                'price_currency': 'USD',
                'bulk_pricing_tiers': bulk_tiers,
                
                # Order specifications
                'minimum_order_quantity': moq,
                'order_units': units,
                'lead_time_days': lead_time,
                
                # Product specifications
                'material': material,
                'dimensions': dimensions,
                'certifications': certs,
                'quality_standards': ['ISO9001'] if 'ISO9001' in certs else [],
                'color_options': random.sample(source_data.get('colors', ['Black', 'White', 'Silver']), random.randint(1, 3)),
                'product_features': random.sample(features, random.randint(2, 4)),
                
                # Customer feedback
                'rating': rating,
                'rating_count': rating_count,
                'review_highlights': review_highlights,
                'common_complaints': complaints,
                
                # Supplier data
                'supplier_name': supplier_info['name'],
                'supplier_country': supplier_info['country'],
                'supplier_region': supplier_info['region'],
                'years_in_business': supplier_info['years'],
                'verification_status': 'Verified' if supplier_info['verified'] else 'Basic',
                'supplier_certifications': certs,
                'response_rate': float(random.uniform(80, 98)),
                'supplier_rating': round(random.uniform(4.0, 5.0), 1),
                
                # Market intelligence
                'views': views,
                'sales': sales,
                'recent_orders': recent_orders,
                'trending_rank': trending_rank,
                'search_keywords': keywords,
                'seasonal_demand': random.choice(['High', 'Medium', 'Low', 'Year-round']),
                'price_trend': random.choice(['Rising', 'Falling', 'Stable']),
                
                # Logistics
                'shipping_cost': float(shipping_cost),
                'shipping_methods': shipping_methods,
                'port_of_shipment': random.choice(source_data.get('ports', ['Main Port'])),
                
                # Media
                'image_urls': [f"{self.source.base_url}/images/{external_id}_{j}.jpg" for j in range(1, random.randint(2, 5))],
                'video_urls': [f"{self.source.base_url}/videos/{external_id}.mp4"] if random.choice([True, False]) else [],
                
                # Legacy compatibility
                'price': f"${current_price}",
                'views': views,
                'rating': rating,
                'raw_data': {
                    'scraped_from': self.source.website,
                    'demo_data': True,
                    'enhanced_version': True,
                    'generation_timestamp': timezone.now().isoformat()
                }
            }
            
            results['items'].append(item)
            
        logger.info(f"Generated {len(results['items'])} comprehensive mock items for {self.source.website}")
        return results


class ScraperFactory:
    """Factory to create appropriate scraper instances."""
    
    SCRAPERS = {
        'alibaba': AlibabaScraper,
        'globaltrade': GlobalTradeScraper,
        'etsy': EtsyScraper,
        'demo': DemoScraper,  # For testing
    }
    
    @classmethod
    def create_scraper(cls, source_config) -> Optional[BaseScraper]:
        """Create scraper instance for given source."""
        # For testing, use demo scraper for all sites to avoid anti-bot issues
        # In production, you'd use the real scrapers with proper browser automation
        
        # Check if this is a test/demo environment
        import os
        if os.environ.get('USE_DEMO_SCRAPERS', 'True').lower() == 'true':
            logger.info(f"Using demo scraper for {source_config.website} (testing mode)")
            return DemoScraper(source_config)
        
        # Production mode - use real scrapers
        scraper_class = cls.SCRAPERS.get(source_config.website)
        if scraper_class:
            return scraper_class(source_config)
        
        logger.error(f"No scraper found for website: {source_config.website}")
        return None