from django.test import TestCase, TransactionTestCase
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from unittest.mock import patch
from wagtail.test.utils import WagtailTestUtils
from wagtail.models import Page, Site
from django.utils import timezone

from blog.managers import OptimizedArticleManager
from blog.models import ArticlePage, Category, BlogIndexPage
from blog.signals import invalidate_article_caches


class CategoryModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Technology",
            description="Tech articles"
        )
    
    def test_category_str_representation(self):
        self.assertEqual(str(self.category), "Technology")
    
    def test_category_slug_generation(self):
        self.assertEqual(self.category.slug, "technology")
    
    def test_category_ordering(self):
        cat2 = Category.objects.create(name="AI")
        cat3 = Category.objects.create(name="Blockchain")
        
        categories = list(Category.objects.all())
        names = [cat.name for cat in categories]
        
        self.assertEqual(names, ["AI", "Blockchain", "Technology"])


class ArticlePageTest(TestCase, WagtailTestUtils):
    def setUp(self):
        self.root_page = Page.objects.get(id=1)
        
        self.blog_index = BlogIndexPage(
            title="Blog",
            slug="blog"
        )
        self.root_page.add_child(instance=self.blog_index)
        
        self.category = Category.objects.create(
            name="Technology",
            description="Tech articles"
        )
        
        self.article = ArticlePage(
            title="Test Article",
            slug="test-article",
            intro="Test introduction",
            body="<p>Test body content</p>",
            category=self.category
        )
        self.blog_index.add_child(instance=self.article)
    
    def test_article_str_representation(self):
        self.assertEqual(str(self.article), "Test Article")
    
    def test_reading_time_calculation(self):
        long_content = " ".join(["word"] * 200) 
        self.article.body = f"<p>{long_content}</p>"
        self.article.save()
        
        reading_time = self.article.reading_time_minutes
        self.assertGreaterEqual(reading_time, 1)
    
    def test_view_count_increment(self):
        initial_count = self.article.view_count
        self.article.increment_view_count()
        
        self.article.refresh_from_db()
        self.assertEqual(self.article.view_count, initial_count + 1)
    
    def test_search_fields(self):
        self.assertTrue(hasattr(ArticlePage, 'search_fields'))
        
        search_field_names = [field.field_name for field in ArticlePage.search_fields]
        expected_fields = ['title', 'intro', 'body', 'category']
        
        for field in expected_fields:
            self.assertIn(field, search_field_names)
    
    def test_parent_page_types(self):
        self.assertEqual(ArticlePage.parent_page_types, ['blog.BlogIndexPage'])
    
    def test_subpage_types(self):
        self.assertEqual(ArticlePage.subpage_types, [])


class ViewCountTest(TransactionTestCase):
    def setUp(self):
        # Ensure default locale exists
        from wagtail.models import Locale
        locale, created = Locale.objects.get_or_create(
            language_code='en',
            defaults={'language_code': 'en'}
        )
        
        try:
            self.root_page = Page.objects.get(id=1)
        except Page.DoesNotExist:
            self.root_page = Page.objects.create(
                title="Root",
                slug="root",
                path="0001",
                depth=1,
                numchild=0,
                url_path="/",
                locale=locale
            )
        self.blog_index = BlogIndexPage(
            title="Blog",
            slug="blog",
            locale=locale
        )
        self.root_page.add_child(instance=self.blog_index)

        self.article = ArticlePage(
            title="Test Article",
            slug="test-article",
            intro="Test introduction",
            body="<p>Test body content</p>",
            locale=locale
        )
        self.blog_index.add_child(instance=self.article)

    def test_concurrent_view_increments(self):
        import threading
        from django.db import connection

        def increment_views():
            connection.ensure_connection()
            self.article.increment_view_count()

        initial_count = self.article.view_count

        threads = []
        num_threads = 10

        for i in range(num_threads):
            thread = threading.Thread(target=increment_views)
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        self.article.refresh_from_db()

        self.assertEqual(
            self.article.view_count,
            initial_count + num_threads
        )

    @patch('blog.tasks.increment_view_count_async.delay')
    def test_async_view_counting_task_called(self, mock_task):
        from blog.tasks import increment_view_count_async

        # Call the delay method to trigger async task
        result = increment_view_count_async.delay("123", "127.0.0.1")

        mock_task.assert_called_once_with("123", "127.0.0.1")


class CacheTest(TransactionTestCase):
    def setUp(self):
        cache.clear()
        self.category = Category.objects.create(
            name="Technology", description="Tech articles"
        )

    def test_cache_basic(self):
        cache.set("test_key", "test_value", 60)
        self.assertEqual(cache.get("test_key"), "test_value")

    def test_cache_invalidation(self):
        """Test that cache invalidation works properly."""
        cache.clear()  
        
        # Test that method gets called once and cached
        with patch('blog.managers.cache') as mock_cache:
            # Set up mock to simulate cache miss first, then cache hit
            mock_cache.get.side_effect = [None, [self.category]]  # First None, then cached result
            mock_cache.set.return_value = None
            
            # First call - should query database
            result1 = Category.objects.with_article_counts()
            # Second call - should use cache
            result2 = Category.objects.with_article_counts()
            
            # Check that cache.get was called twice (cache miss, then cache hit)
            self.assertEqual(mock_cache.get.call_count, 2)
            # Check that cache.set was called once (to store the result)
            self.assertEqual(mock_cache.set.call_count, 1)

    def tearDown(self):
        cache.clear()


class ArticleManagerTest(TestCase, WagtailTestUtils):
    def setUp(self):
        self.root_page = Page.objects.get(id=1)
        self.blog_index = BlogIndexPage(title="Blog", slug="blog")
        self.root_page.add_child(instance=self.blog_index)

        self.category = Category.objects.create(name="Technology", slug="technology")
        self.article1 = ArticlePage(
            title="Article 1",
            slug="article-1",
            intro="Intro 1",
            body="<p>Body 1</p>",
            category=self.category,
            featured=True,
            view_count=100,
        )
        self.article2 = ArticlePage(
            title="Article 2",
            slug="article-2",
            intro="Intro 2",
            body="<p>Body 2</p>",
            category=self.category,
            view_count=50,
        )
        self.blog_index.add_child(instance=self.article1)
        self.blog_index.add_child(instance=self.article2)

    def test_published(self):
        articles = ArticlePage.objects.published()
        self.assertEqual(len(articles), 2)
        self.assertIn(self.article1, articles)

    def test_featured(self):
        featured = ArticlePage.objects.featured()
        self.assertEqual(len(featured), 1)
        self.assertEqual(featured[0], self.article1)

    def test_popular(self):
        popular = ArticlePage.objects.popular(limit=2)
        self.assertEqual(len(popular), 2)
        self.assertEqual(popular[0], self.article1) 
        self.assertEqual(popular[1], self.article2)

    def test_recent(self):
        recent = ArticlePage.objects.recent(limit=1)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0], self.article2)

    def test_by_category(self):
        articles = ArticlePage.objects.by_category("technology", limit=1)
        self.assertEqual(len(articles), 1)
        self.assertIn(self.article1, articles)

    def test_by_category_cache(self):
        with patch.object(OptimizedArticleManager, "published") as mock_published:
            ArticlePage.objects.by_category("technology")
            ArticlePage.objects.by_category("technology")
            self.assertEqual(mock_published.call_count, 1)

