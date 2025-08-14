from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock
from django import forms


class FeaturedArticleBlock(blocks.StructBlock):
    """Block for featuring a specific article."""
    title = blocks.CharBlock(max_length=100, default="Featured Article")
    show_title = blocks.BooleanBlock(default=True, required=False)
    
    class Meta:
        template = "home/blocks/featured_article_block.html"
        icon = "star"
        label = "Featured Article"


class LatestArticlesBlock(blocks.StructBlock):
    """Block for displaying latest articles."""
    title = blocks.CharBlock(max_length=100, default="Latest Articles")
    show_title = blocks.BooleanBlock(default=True, required=False)
    number_of_articles = blocks.IntegerBlock(
        min_value=1, 
        max_value=12, 
        default=6,
        help_text="Number of articles to display"
    )
    
    class Meta:
        template = "home/blocks/latest_articles_block.html"
        icon = "doc-full"
        label = "Latest Articles"


class PopularArticlesBlock(blocks.StructBlock):
    """Block for displaying popular articles."""
    title = blocks.CharBlock(max_length=100, default="Popular Articles")
    show_title = blocks.BooleanBlock(default=True, required=False)
    number_of_articles = blocks.IntegerBlock(
        min_value=1, 
        max_value=12, 
        default=6,
        help_text="Number of articles to display"
    )
    time_period = blocks.ChoiceBlock(
        choices=[
            ('week', 'This Week'),
            ('month', 'This Month'),
            ('all', 'All Time'),
        ],
        default='month',
        help_text="Time period for popularity calculation"
    )
    
    class Meta:
        template = "home/blocks/popular_articles_block.html"
        icon = "view"
        label = "Popular Articles"


class AdSpaceBlock(blocks.StructBlock):
    """Block for ad spaces."""
    title = blocks.CharBlock(max_length=100, default="Advertisement", required=False)
    ad_type = blocks.ChoiceBlock(
        choices=[
            ('banner', 'Banner Ad'),
            ('square', 'Square Ad'),
            ('sidebar', 'Sidebar Ad'),
            ('custom', 'Custom HTML'),
        ],
        default='banner'
    )
    ad_image = ImageChooserBlock(required=False, help_text="Upload ad image")
    ad_url = blocks.URLBlock(required=False, help_text="URL when ad is clicked")
    ad_html = blocks.RawHTMLBlock(
        required=False, 
        help_text="Custom HTML for ad (use only if ad_type is 'custom')"
    )
    alt_text = blocks.CharBlock(
        max_length=200, 
        required=False,
        help_text="Alt text for ad image"
    )
    
    class Meta:
        template = "home/blocks/ad_space_block.html"
        icon = "image"
        label = "Advertisement"


class CategoryHighlightBlock(blocks.StructBlock):
    """Block for highlighting specific categories."""
    title = blocks.CharBlock(max_length=100, default="Explore Categories")
    show_title = blocks.BooleanBlock(default=True, required=False)
    number_of_categories = blocks.IntegerBlock(
        min_value=3,
        max_value=8,
        default=6,
        help_text="Number of categories to display"
    )
    
    class Meta:
        template = "home/blocks/category_highlight_block.html"
        icon = "folder"
        label = "Category Highlight"


class NewsletterSignupBlock(blocks.StructBlock):
    """Block for newsletter signup."""
    title = blocks.CharBlock(max_length=100, default="Stay Updated")
    subtitle = blocks.CharBlock(
        max_length=200, 
        default="Get the latest articles delivered to your inbox",
        required=False
    )
    background_color = blocks.ChoiceBlock(
        choices=[
            ('primary', 'Primary Blue'),
            ('secondary', 'Secondary Green'),
            ('gray', 'Gray'),
            ('dark', 'Dark'),
        ],
        default='primary'
    )
    
    class Meta:
        template = "home/blocks/newsletter_signup_block.html"
        icon = "mail"
        label = "Newsletter Signup"