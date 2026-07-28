/**
 * VITAL HUB - MODERN ANIMATION SYSTEM
 * Drives every .reveal / .reveal-up / .reveal-left / .reveal-right /
 * .reveal-scale / .reveal-stagger element defined in CSS/style.css.
 * Purely additive — pages that don't use these classes are unaffected.
 */
(function () {
    const REVEAL_SELECTOR = '.reveal, .reveal-up, .reveal-left, .reveal-right, .reveal-scale, .reveal-stagger';

    function initReveal() {
        const els = document.querySelectorAll(REVEAL_SELECTOR);
        if (!els.length) return;

        if (!('IntersectionObserver' in window)) {
            els.forEach(el => el.classList.add('in-view'));
            return;
        }

        const io = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('in-view');
                    io.unobserve(entry.target);
                }
            });
        }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

        els.forEach(el => io.observe(el));
    }

    function init() {
        initReveal();
        if (window.lucide) lucide.createIcons();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Re-scan when new content is injected dynamically (e.g. AI-generated
    // nutrition plans, grocery lists, search results) so those also animate in.
    window.vhRefreshReveal = initReveal;
})();
