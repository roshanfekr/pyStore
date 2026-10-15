/* Product image gallery.
 *
 * Shows every product image as a thumbnail under the main image; clicking a
 * thumbnail swaps the main image. External (CSP-safe) so no inline script is
 * needed. */
(function () {
    'use strict';

    function bindGallery(gallery) {
        var main = gallery.querySelector('[data-gallery-main]');
        var thumbs = gallery.querySelectorAll('[data-gallery-thumb]');
        if (!main || !thumbs.length) {
            return;
        }

        Array.prototype.forEach.call(thumbs, function (thumb) {
            thumb.addEventListener('click', function () {
                var src = thumb.getAttribute('data-src');
                if (src) {
                    main.src = src;
                }
                var alt = thumb.getAttribute('data-alt');
                if (alt) {
                    main.alt = alt;
                }
                Array.prototype.forEach.call(thumbs, function (other) {
                    other.classList.remove('is-active');
                });
                thumb.classList.add('is-active');
            });
        });
    }

    function init() {
        Array.prototype.forEach.call(
            document.querySelectorAll('[data-gallery]'),
            bindGallery
        );
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
