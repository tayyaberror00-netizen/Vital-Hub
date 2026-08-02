/**
 * SPARTAN MOTION — Vital Hub global animation engine
 * Lightweight, dependency-free. Drives:
 *   - .spartan-reveal / -left / -right      (element entrances)
 *   - .spartan-section-reveal               (whole-section "chapter" staging)
 *   - .spartan-text-reveal                  (word-by-word cascading text)
 * all via native IntersectionObserver, defined in CSS/spartan-motion.css.
 *
 * Design notes:
 * - Each element is observed once and unobserved the instant it reveals —
 *   scrolling back up never re-triggers or re-runs layout work for it.
 * - Respects prefers-reduced-motion: everything is shown immediately with
 *   no animation and the observer never even spins up.
 * - After the CSS transition finishes, `is-settled` is added so the
 *   element's `will-change` hint is dropped — keeps the browser from
 *   holding unnecessary paint layers open for content that's done moving.
 */
(function () {
    const REVEAL_SELECTOR = '.spartan-reveal, .spartan-reveal-left, .spartan-reveal-right, .spartan-section-reveal, .spartan-text-reveal';
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // ── Text splitting for .spartan-text-reveal ───────────────────────────
    // Wraps each word in a .spartan-word span with its own staggered
    // transition-delay, while preserving any inline markup already inside
    // the element (e.g. <span class="text-blue-600">Health</span> stays
    // intact as a single atomic "word" rather than being torn apart).
    const WORD_STAGGER_MS = 45;
    const WORD_STAGGER_MAX_MS = 650;

    function splitIntoWords(container) {
        if (container.dataset.spartanSplit) return; // never split twice
        container.dataset.spartanSplit = 'true';

        const originalNodes = Array.from(container.childNodes);
        container.textContent = '';
        let wordIndex = 0;

        function nextDelay() {
            const ms = Math.min(wordIndex * WORD_STAGGER_MS, WORD_STAGGER_MAX_MS);
            wordIndex++;
            return ms + 'ms';
        }

        originalNodes.forEach(node => {
            if (node.nodeType === Node.TEXT_NODE) {
                // Split on whitespace but keep the whitespace tokens so
                // word-wrap/spacing in the sentence is unaffected.
                const parts = node.textContent.split(/(\s+)/);
                parts.forEach(part => {
                    if (part.trim() === '') {
                        if (part) container.appendChild(document.createTextNode(part));
                        return;
                    }
                    const span = document.createElement('span');
                    span.className = 'spartan-word';
                    span.textContent = part;
                    span.style.transitionDelay = nextDelay();
                    container.appendChild(span);
                });
            } else {
                // Element node (existing inline markup) — treat as one
                // atomic animated word rather than descending into it.
                node.classList.add('spartan-word');
                node.style.transitionDelay = nextDelay();
                container.appendChild(node);
            }
        });
    }

    function settleAfterTransition(el) {
        el.addEventListener('transitionend', function onEnd(e) {
            if (e.target !== el) return; // ignore bubbled transitions from children/words
            el.classList.add('is-settled');
            el.removeEventListener('transitionend', onEnd);
        });
    }

    function init() {
        // Split text-reveal elements up front so their words exist in the
        // DOM before the observer starts watching them.
        document.querySelectorAll('.spartan-text-reveal').forEach(splitIntoWords);

        const els = document.querySelectorAll(REVEAL_SELECTOR);
        if (!els.length) return;

        if (prefersReduced || !('IntersectionObserver' in window)) {
            els.forEach(el => el.classList.add('is-in', 'is-settled'));
            return;
        }

        const io = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (!entry.isIntersecting) return;
                const el = entry.target;
                el.classList.add('is-in');
                settleAfterTransition(el);
                io.unobserve(el); // once per session element — never re-triggers
            });
        }, {
            threshold: 0.12,
            rootMargin: '0px 0px -60px 0px',
        });

        els.forEach(el => {
            // Only observe elements not already revealed (relevant on refresh calls).
            if (!el.classList.contains('is-in')) io.observe(el);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Exposed so pages that inject content dynamically (AI-generated plans,
    // search results, newly-rendered cards) can bring new elements into the
    // reveal system without a full re-init.
    window.spartanMotionRefresh = init;
})();
