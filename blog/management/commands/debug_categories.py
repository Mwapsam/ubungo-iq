from django.core.management.base import BaseCommand
from blog.models import Category, ArticlePage
from django.db.models import Count, Q


class Command(BaseCommand):
    help = 'Debug categories and their article counts'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Category Debug Information ==='))
        
        # Get all categories
        all_categories = Category.objects.all().order_by('name')
        self.stdout.write(f'Total categories in database: {all_categories.count()}')
        
        if not all_categories.exists():
            self.stdout.write(self.style.WARNING('No categories found in database!'))
            self.stdout.write('You can create categories in Django Admin or Wagtail Admin.')
            return
        
        # Get categories with article counts
        categories_with_counts = Category.objects.annotate(
            article_count=Count('articles', filter=Q(articles__live=True))
        ).order_by('name')
        
        self.stdout.write('\n=== All Categories ===')
        for category in all_categories:
            # Get the annotated version
            annotated_cat = categories_with_counts.get(id=category.id)
            article_count = annotated_cat.article_count if annotated_cat else 0
            
            self.stdout.write(f'- {category.name} (slug: {category.slug})')
            self.stdout.write(f'  Color: {category.color}')
            self.stdout.write(f'  Description: {category.description or "None"}')
            self.stdout.write(f'  Article count: {article_count}')
            
            if article_count == 0:
                self.stdout.write(self.style.WARNING(f'  ⚠️  No live articles in this category'))
            
            self.stdout.write('')
        
        # Check for articles without categories
        uncategorized_articles = ArticlePage.objects.live().filter(category__isnull=True)
        uncategorized_count = uncategorized_articles.count()
        
        if uncategorized_count > 0:
            self.stdout.write(self.style.WARNING(f'Found {uncategorized_count} articles without categories:'))
            for article in uncategorized_articles:
                self.stdout.write(f'- {article.title}')
        
        self.stdout.write(self.style.SUCCESS('\n=== Summary ==='))
        self.stdout.write(f'Total categories: {all_categories.count()}')
        self.stdout.write(f'Categories with articles: {categories_with_counts.filter(article_count__gt=0).count()}')
        self.stdout.write(f'Articles without categories: {uncategorized_count}')
        
        # API simulation
        self.stdout.write(self.style.SUCCESS('\n=== API Response Simulation ==='))
        self.stdout.write('Categories that would be returned by API:')
        
        for category in categories_with_counts:
            self.stdout.write(f'- {category.name}: {category.article_count} articles')