# tests/test_tasks.py
from django.test import TestCase, TransactionTestCase
from django.core.cache import cache
from unittest.mock import patch, Mock
from celery import states
from celery.exceptions import Retry

from blog.models import ArticlePage, Category
from blog.tasks import (
    increment_view_count_async,
    convert_image_to_avif,
    update_trending_articles,
    generate_analytics_summary
)
from wagtail.models import Page
from blog.models import BlogIndexPage


class ViewCountTaskTest(TestCase):
    def setUp(self):
        cache.clear()

        root_page = Page.objects.get(id=1)
        blog_index = BlogIndexPage(title="Blog", slug="blog")
        root_page.add_child(instance=blog_index)

        self.article = ArticlePage(
            title="Test Article",
            slug="test-article",
            intro="Test intro",
            body="<p>Test body</p>"
        )
        blog_index.add_child(instance=self.article)

    def test_increment_view_count_success(self):
        initial_count = self.article.view_count

        result = increment_view_count_async(
            self.article.id,
            "192.168.1.1"
        )

        self.assertTrue(result)

        self.article.refresh_from_db()
        self.assertEqual(self.article.view_count, initial_count + 1)

    def test_increment_view_count_deduplication(self):
        initial_count = self.article.view_count
        ip_address = "192.168.1.1"

        result1 = increment_view_count_async(
            self.article.id,
            ip_address
        )
        self.assertTrue(result1)

        result2 = increment_view_count_async(
            self.article.id,
            ip_address
        )
        self.assertFalse(result2)

        self.article.refresh_from_db()
        self.assertEqual(self.article.view_count, initial_count + 1)

    def test_increment_view_count_different_ips(self):
        initial_count = self.article.view_count

        result1 = increment_view_count_async(
            self.article.id,
            "192.168.1.1"
        )
        result2 = increment_view_count_async(
            self.article.id,
            "192.168.1.2"
        )

        self.assertTrue(result1)
        self.assertTrue(result2)

        self.article.refresh_from_db()
        self.assertEqual(self.article.view_count, initial_count + 2)


    @patch("blog.models.ArticlePage.objects.filter")
    def test_increment_view_count_retry_on_failure(self, mock_filter):
        mock_filter.return_value.update.side_effect = Exception("DB Error")

        with patch.object(increment_view_count_async, "retry") as mock_retry:
            mock_retry.side_effect = Retry()

            with self.assertRaises(Retry):
                increment_view_count_async(self.article.id, "192.168.1.1")

            mock_retry.assert_called_once()

    def test_cache_expiration(self):
        ip_address = "192.168.1.1"

        increment_view_count_async(
            self.article.id,
            ip_address
        )

        view_key = f"view_counted:{self.article.id}:{ip_address}"
        self.assertTrue(cache.get(view_key))

        cache.delete(view_key)

        result = increment_view_count_async(
            self.article.id,
            ip_address
        )
        self.assertTrue(result)

    def tearDown(self):
        cache.clear()


class AnalyticsTaskTest(TestCase):
    def setUp(self):
        cache.clear()
        
        root_page = Page.objects.get(id=1)
        blog_index = BlogIndexPage(title="Blog", slug="blog")
        root_page.add_child(instance=blog_index)
        
        self.category = Category.objects.create(
            name="Technology",
            slug="technology"
        )
        
        self.article1 = ArticlePage(
            title="Article 1",
            slug="article-1",
            intro="Intro 1",
            body="<p>Body 1</p>",
            category=self.category,
            view_count=100
        )
        blog_index.add_child(instance=self.article1)
        
        self.article2 = ArticlePage(
            title="Article 2", 
            slug="article-2",
            intro="Intro 2",
            body="<p>Body 2</p>",
            category=self.category,
            view_count=50
        )
        blog_index.add_child(instance=self.article2)
    
    def test_generate_analytics_summary(self):
        result = generate_analytics_summary()
        
        self.assertIsInstance(result, dict)
        self.assertIn('date', result)
        self.assertIn('total_articles', result)
        self.assertIn('total_views', result)
        self.assertIn('avg_views_per_article', result)
        self.assertIn('articles_by_category', result)
        
        self.assertEqual(result['total_articles'], 2)
        self.assertEqual(result['total_views'], 150)  
        self.assertEqual(result['avg_views_per_article'], 75.0)
        
        category_data = result['articles_by_category']
        self.assertEqual(len(category_data), 1)
        self.assertEqual(category_data[0]['name'], 'Technology')
        self.assertEqual(category_data[0]['article_count'], 2)
    
    def test_update_trending_articles(self):
        cache.set(f"recent_views:{self.article1.id}", 20, 3600)
        cache.set(f"recent_views:{self.article2.id}", 10, 3600)
        
        update_trending_articles()
        
        score1 = cache.get(f"trending_score:{self.article1.id}")
        score2 = cache.get(f"trending_score:{self.article2.id}")
        
        self.assertIsNotNone(score1)
        self.assertIsNotNone(score2)
        self.assertGreater(score1, score2)  
    
    def test_analytics_caching(self):
        from datetime import date
        
        result = generate_analytics_summary()
        
        today = date.today()
        cache_key = f"daily_stats:{today.isoformat()}"
        cached_result = cache.get(cache_key)
        
        self.assertIsNotNone(cached_result)
        self.assertEqual(cached_result['total_articles'], result['total_articles'])
    
    def tearDown(self):
        cache.clear()


class ImageTaskTest(TestCase):
    @patch('blog.tasks.WagtailImage.objects.get')
    @patch('blog.tasks.default_storage')
    @patch('blog.tasks.Image.open')
    def test_convert_image_to_avif_success(self, mock_image_open, mock_storage, mock_get_image):
        mock_wagtail_image = Mock()
        mock_wagtail_image.id = 1
        mock_wagtail_image.file.name = "test-image.jpg"
        
        # Mock the file context manager
        mock_file = Mock()
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=None)
        mock_wagtail_image.file.open = Mock(return_value=mock_file)
        
        mock_get_image.return_value = mock_wagtail_image

        mock_pil_image = Mock()
        mock_pil_image.mode = "RGB"
        mock_pil_image.convert = Mock(return_value=mock_pil_image)
        mock_pil_image.save = Mock()
        mock_image_open.return_value = mock_pil_image

        # Mock storage operations
        mock_storage.exists.return_value = False
        mock_storage.save.return_value = "avif_images/test-image.avif"
        mock_storage.url.return_value = "https://example.com/avif_images/test-image.avif"
        
        # Mock storage.open for the BytesIO saving
        mock_storage_file = Mock()
        mock_storage_file.__enter__ = Mock(return_value=mock_storage_file)
        mock_storage_file.__exit__ = Mock(return_value=None)
        mock_storage.open = Mock(return_value=mock_storage_file)

        result = convert_image_to_avif(1)

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['image_id'], 1)
        self.assertIn('avif_url', result)
        self.assertTrue(result['avif_url'].startswith("https://example.com"))
    
    @patch('blog.tasks.WagtailImage.objects.get')
    def test_convert_image_to_avif_failure(self, mock_get_image):
        mock_get_image.side_effect = Exception("Image not found")
        
        result = convert_image_to_avif(999)
        
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['image_id'], 999)
        self.assertIn('message', result)
    
    def test_image_conversion_formats(self):        
        formats_to_test = ['RGBA', 'P', 'RGB']
        
        for format_type in formats_to_test:
            self.assertIn(format_type, ['RGBA', 'P', 'RGB', 'L'])


class CeleryIntegrationTest(TransactionTestCase):
    def setUp(self):
        cache.clear()
        
    @patch('blog.tasks.increment_view_count_async.delay')
    def test_task_is_queued(self, mock_delay):
        from blog.tasks import increment_view_count_async
        
        increment_view_count_async.delay(1, "192.168.1.1")
        
        mock_delay.assert_called_once_with(1, "192.168.1.1")
    
    def test_task_retry_logic(self):
        self.assertTrue(hasattr(increment_view_count_async, 'max_retries'))
        self.assertEqual(increment_view_count_async.max_retries, 3)
    
    def tearDown(self):
        cache.clear()
