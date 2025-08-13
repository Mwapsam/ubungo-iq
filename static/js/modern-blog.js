// Modern Blog JavaScript
// Handles mobile menu, search, lazy loading, and HTMX interactions

(function() {
    'use strict';

    // Initialize when DOM is loaded
    document.addEventListener('DOMContentLoaded', function() {
        initMobileMenu();
        initSearch();
        initScrollEffects();
        initLazyLoading();
        initSmoothScroll();
        initBackToTop();
        initViewTracking();
    });

    // Mobile Menu Functionality
    function initMobileMenu() {
        const menuToggle = document.querySelector('.mobile-menu-toggle');
        const mainNav = document.querySelector('.main-nav');
        
        if (!menuToggle || !mainNav) return;

        menuToggle.addEventListener('click', function() {
            const isExpanded = menuToggle.getAttribute('aria-expanded') === 'true';
            
            menuToggle.setAttribute('aria-expanded', !isExpanded);
            mainNav.classList.toggle('mobile-open');
            
            // Prevent body scroll when menu is open
            document.body.style.overflow = isExpanded ? '' : 'hidden';
        });

        // Close menu when clicking outside
        document.addEventListener('click', function(event) {
            if (!menuToggle.contains(event.target) && !mainNav.contains(event.target)) {
                menuToggle.setAttribute('aria-expanded', 'false');
                mainNav.classList.remove('mobile-open');
                document.body.style.overflow = '';
            }
        });

        // Close menu on escape key
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape') {
                menuToggle.setAttribute('aria-expanded', 'false');
                mainNav.classList.remove('mobile-open');
                document.body.style.overflow = '';
            }
        });
    }

    // Enhanced Search Functionality
    function initSearch() {
        const searchInput = document.querySelector('.search-input');
        const searchResults = document.querySelector('.search-results');
        let searchTimeout;

        if (!searchInput || !searchResults) return;

        // Handle search input
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value.trim();

            if (query.length < 2) {
                hideSearchResults();
                return;
            }

            // Debounce search requests
            searchTimeout = setTimeout(() => {
                performSearch(query);
            }, 300);
        });

        // Hide results when clicking outside
        document.addEventListener('click', function(event) {
            if (!event.target.closest('.search-container')) {
                hideSearchResults();
            }
        });

        function performSearch(query) {
            showLoadingState();
            
            fetch(`/api/search/?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    displaySearchResults(data);
                })
                .catch(error => {
                    console.error('Search error:', error);
                    hideSearchResults();
                });
        }

        function showLoadingState() {
            searchResults.innerHTML = '<div class="search-loading">Searching...</div>';
            searchResults.style.display = 'block';
        }

        function displaySearchResults(data) {
            if (!data.articles || data.articles.length === 0) {
                searchResults.innerHTML = '<div class="no-results">No articles found</div>';
                return;
            }

            const resultsHTML = data.articles.map(article => `
                <a href="${article.url}" class="search-result">
                    <h4>${article.title}</h4>
                    <p>${article.intro}</p>
                    <span class="search-meta">${article.category} • ${article.formatted_date}</span>
                </a>
            `).join('');

            searchResults.innerHTML = resultsHTML;
            searchResults.style.display = 'block';
        }

        function hideSearchResults() {
            searchResults.style.display = 'none';
        }
    }

    // Scroll Effects
    function initScrollEffects() {
        const header = document.querySelector('.site-header');
        if (!header) return;

        let lastScrollTop = 0;
        
        window.addEventListener('scroll', function() {
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            
            // Add background to header on scroll
            if (scrollTop > 100) {
                header.classList.add('scrolled');
            } else {
                header.classList.remove('scrolled');
            }

            // Hide/show header on scroll
            if (scrollTop > lastScrollTop && scrollTop > 200) {
                header.style.transform = 'translateY(-100%)';
            } else {
                header.style.transform = 'translateY(0)';
            }
            
            lastScrollTop = scrollTop;
        });
    }

    // Intersection Observer for Lazy Loading and Animations
    function initLazyLoading() {
        // Lazy load images
        const lazyImages = document.querySelectorAll('img[loading="lazy"]');
        
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src || img.src;
                        img.classList.remove('lazy');
                        imageObserver.unobserve(img);
                    }
                });
            });

            lazyImages.forEach(img => {
                imageObserver.observe(img);
            });

            // Animate elements on scroll
            const animatedElements = document.querySelectorAll('.fade-in-up');
            const animationObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.style.opacity = '1';
                        entry.target.style.transform = 'translateY(0)';
                        animationObserver.unobserve(entry.target);
                    }
                });
            }, { threshold: 0.1 });

            animatedElements.forEach(el => {
                el.style.opacity = '0';
                el.style.transform = 'translateY(30px)';
                el.style.transition = 'opacity 0.6s ease-out, transform 0.6s ease-out';
                animationObserver.observe(el);
            });
        }
    }

    // Smooth Scroll for Anchor Links
    function initSmoothScroll() {
        document.addEventListener('click', function(event) {
            const link = event.target.closest('a[href^="#"]');
            if (!link) return;

            event.preventDefault();
            const targetId = link.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);
            
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    }

    // Back to Top Button
    function initBackToTop() {
        const backToTop = createBackToTopButton();
        document.body.appendChild(backToTop);

        window.addEventListener('scroll', function() {
            if (window.pageYOffset > 500) {
                backToTop.classList.add('visible');
            } else {
                backToTop.classList.remove('visible');
            }
        });

        backToTop.addEventListener('click', function() {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }

    function createBackToTopButton() {
        const button = document.createElement('button');
        button.className = 'back-to-top';
        button.setAttribute('aria-label', 'Back to top');
        button.innerHTML = `
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 10l7-7m0 0l7 7m-7-7v18"></path>
            </svg>
        `;

        // Add CSS styles
        const styles = `
            .back-to-top {
                position: fixed;
                bottom: 2rem;
                right: 2rem;
                width: 3rem;
                height: 3rem;
                background: var(--color-primary);
                color: white;
                border: none;
                border-radius: 50%;
                cursor: pointer;
                opacity: 0;
                visibility: hidden;
                transform: translateY(20px);
                transition: all 0.3s ease;
                z-index: 100;
                box-shadow: var(--shadow-lg);
            }
            
            .back-to-top.visible {
                opacity: 1;
                visibility: visible;
                transform: translateY(0);
            }
            
            .back-to-top:hover {
                background: var(--color-primary-dark);
                transform: translateY(-2px);
            }
            
            .back-to-top svg {
                width: 1.5rem;
                height: 1.5rem;
            }
        `;

        if (!document.getElementById('back-to-top-styles')) {
            const styleSheet = document.createElement('style');
            styleSheet.id = 'back-to-top-styles';
            styleSheet.textContent = styles;
            document.head.appendChild(styleSheet);
        }

        return button;
    }

    // View Tracking
    function initViewTracking() {
        const pageId = document.body.getAttribute('data-page-id');
        if (!pageId) return;

        // Track view after user has been on page for 3 seconds
        setTimeout(() => {
            if (document.visibilityState === 'visible') {
                trackPageView(pageId);
            }
        }, 3000);

        // Track view when page becomes visible (if user switched tabs)
        document.addEventListener('visibilitychange', function() {
            if (document.visibilityState === 'visible') {
                setTimeout(() => {
                    trackPageView(pageId);
                }, 3000);
            }
        });
    }

    function trackPageView(pageId) {
        fetch('/api/track-view/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                page_id: pageId,
                url: window.location.href,
                referrer: document.referrer
            })
        }).catch(error => {
            console.error('View tracking error:', error);
        });
    }

    // HTMX Event Handlers
    document.body.addEventListener('htmx:beforeRequest', function(event) {
        // Show loading state
        const target = event.target;
        if (target.hasAttribute('data-loading-class')) {
            target.classList.add(target.getAttribute('data-loading-class'));
        }
    });

    document.body.addEventListener('htmx:afterRequest', function(event) {
        // Hide loading state
        const target = event.target;
        if (target.hasAttribute('data-loading-class')) {
            target.classList.remove(target.getAttribute('data-loading-class'));
        }

        // Reinitialize components for new content
        initLazyLoading();
    });

    document.body.addEventListener('htmx:responseError', function(event) {
        console.error('HTMX request failed:', event.detail);
        // Show user-friendly error message
        showErrorMessage('Something went wrong. Please try again.');
    });

    // Utility Functions
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function showErrorMessage(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        errorDiv.style.cssText = `
            position: fixed;
            top: 2rem;
            right: 2rem;
            background: #ef4444;
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 0.5rem;
            z-index: 1000;
            box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
            transform: translateX(100%);
            transition: transform 0.3s ease;
        `;
        
        document.body.appendChild(errorDiv);
        
        // Slide in
        setTimeout(() => {
            errorDiv.style.transform = 'translateX(0)';
        }, 100);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            errorDiv.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (errorDiv.parentNode) {
                    errorDiv.parentNode.removeChild(errorDiv);
                }
            }, 300);
        }, 5000);
    }

    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Reading Progress Bar (for article pages)
    if (document.body.classList.contains('article-page')) {
        initReadingProgress();
    }

    function initReadingProgress() {
        const progressBar = document.createElement('div');
        progressBar.className = 'reading-progress';
        progressBar.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 0%;
            height: 3px;
            background: var(--color-primary);
            z-index: 1000;
            transition: width 0.3s ease;
        `;
        
        document.body.appendChild(progressBar);

        window.addEventListener('scroll', debounce(function() {
            const scrollTop = window.pageYOffset;
            const docHeight = document.documentElement.scrollHeight - window.innerHeight;
            const scrollPercent = (scrollTop / docHeight) * 100;
            
            progressBar.style.width = Math.min(scrollPercent, 100) + '%';
        }, 10));
    }

    // Performance Monitoring
    if ('PerformanceObserver' in window) {
        const perfObserver = new PerformanceObserver((list) => {
            list.getEntries().forEach((entry) => {
                // Log slow operations
                if (entry.duration > 100) {
                    console.warn('Slow operation detected:', entry);
                }
            });
        });
        
        perfObserver.observe({ entryTypes: ['measure', 'navigation'] });
    }

    // Service Worker Registration (for PWA features)
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', function() {
            navigator.serviceWorker.register('/sw.js')
                .then(registration => {
                    console.log('ServiceWorker registered:', registration.scope);
                })
                .catch(error => {
                    console.log('ServiceWorker registration failed:', error);
                });
        });
    }

    // Export functions for external use
    window.ModernBlog = {
        showErrorMessage,
        getCookie,
        debounce
    };
})();