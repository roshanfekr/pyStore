/* Searchable select (Bootstrap 5 combobox).
 *
 * Progressively enhances every native <select class="ps-search-select"> into a
 * searchable dropdown with a live text filter. The native <select> is kept in
 * the DOM (just visually hidden) so form submission, validation and Django's
 * admin "add related" popups keep working unchanged.
 *
 * The menu is attached to <body> and positioned with ``position: fixed`` so it
 * is never clipped by an ancestor's ``overflow`` (Django's own ``forms.css``
 * sets ``.form-row { overflow: hidden }``), which used to cut off the lower
 * half of the list.
 *
 * Kept in an external file because the site Content-Security-Policy
 * (``script-src 'self'``) blocks inline JavaScript.
 */
(function () {
    'use strict';

    function ready(fn) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', fn);
        } else {
            fn();
        }
    }

    function fireChange(select) {
        var event;
        try {
            event = new Event('change', { bubbles: true });
        } catch (e) {
            event = document.createEvent('HTMLEvents');
            event.initEvent('change', true, false);
        }
        select.dispatchEvent(event);
    }

    function enhance(select) {
        if (select.dataset.psEnhanced === '1') {
            return;
        }
        select.dataset.psEnhanced = '1';

        var wrap = document.createElement('div');
        wrap.className = 'ps-select';

        var toggle = document.createElement('button');
        toggle.type = 'button';
        toggle.className = 'btn btn-outline-secondary dropdown-toggle ps-select-toggle';
        toggle.setAttribute('aria-haspopup', 'listbox');
        toggle.setAttribute('aria-expanded', 'false');

        var menu = document.createElement('div');
        menu.className = 'dropdown-menu ps-select-menu';

        var searchWrap = document.createElement('div');
        searchWrap.className = 'ps-select-search-wrap';
        var search = document.createElement('input');
        search.type = 'text';
        search.className = 'ps-select-search';
        search.setAttribute('autocomplete', 'off');
        search.setAttribute('placeholder', 'Search…');
        searchWrap.appendChild(search);

        var optionsBox = document.createElement('div');
        optionsBox.className = 'ps-select-options';
        optionsBox.setAttribute('role', 'listbox');

        menu.appendChild(searchWrap);
        menu.appendChild(optionsBox);
        wrap.appendChild(toggle);

        select.parentNode.insertBefore(wrap, select.nextSibling);
        select.classList.add('ps-search-select-native');
        // ``body`` is the only ancestor guaranteed to have no clipping context.
        document.body.appendChild(menu);

        var activeIndex = -1;

        function readOptions() {
            return Array.prototype.slice.call(select.options).map(function (opt) {
                return { value: opt.value, text: (opt.textContent || '').trim() };
            });
        }

        function currentLabel() {
            var opt = select.options[select.selectedIndex];
            if (opt) {
                var text = (opt.textContent || '').trim();
                if (text) {
                    return text;
                }
            }
            return '—';
        }

        function updateToggle() {
            toggle.textContent = currentLabel();
        }

        function positionMenu() {
            var rect = toggle.getBoundingClientRect();
            menu.style.position = 'fixed';
            menu.style.top = rect.bottom + 2 + 'px';
            menu.style.left = rect.left + 'px';
            menu.style.width = rect.width + 'px';
            menu.style.minWidth = rect.width + 'px';
            menu.style.zIndex = '2000';
        }

        function renderOptions(filter) {
            var query = (filter || '').trim().toLowerCase();
            var items = readOptions().filter(function (opt) {
                if (opt.value === '' && query) {
                    return false;
                }
                return !query || opt.text.toLowerCase().indexOf(query) !== -1;
            });
            optionsBox.textContent = '';
            activeIndex = -1;
            if (!items.length) {
                var empty = document.createElement('div');
                empty.className = 'ps-select-empty';
                empty.textContent = 'No matches';
                optionsBox.appendChild(empty);
                return;
            }
            items.forEach(function (opt) {
                var item = document.createElement('button');
                item.type = 'button';
                item.className = 'ps-select-option';
                item.setAttribute('data-value', opt.value);
                item.setAttribute('role', 'option');
                item.textContent = opt.text;
                if (opt.value === select.value) {
                    item.classList.add('is-selected');
                }
                optionsBox.appendChild(item);
            });
        }

        function openMenu() {
            renderOptions('');
            search.value = '';
            positionMenu();
            menu.classList.add('show');
            toggle.setAttribute('aria-expanded', 'true');
            window.setTimeout(function () {
                search.focus();
            }, 0);
        }

        function closeMenu() {
            menu.classList.remove('show');
            toggle.setAttribute('aria-expanded', 'false');
        }

        function isOpen() {
            return menu.classList.contains('show');
        }

        function choose(value) {
            select.value = value;
            updateToggle();
            closeMenu();
            fireChange(select);
        }

        toggle.addEventListener('click', function (event) {
            event.preventDefault();
            event.stopPropagation();
            if (isOpen()) {
                closeMenu();
            } else {
                openMenu();
            }
        });

        // Close when clicking anywhere outside the toggle or the (detached) menu.
        document.addEventListener('click', function (event) {
            if (!isOpen()) {
                return;
            }
            if (wrap.contains(event.target) || menu.contains(event.target)) {
                return;
            }
            closeMenu();
        });

        optionsBox.addEventListener('click', function (event) {
            var item = event.target.closest ? event.target.closest('.ps-select-option') : null;
            if (!item) {
                return;
            }
            event.preventDefault();
            event.stopPropagation();
            choose(item.getAttribute('data-value'));
        });

        search.addEventListener('input', function () {
            renderOptions(search.value);
        });

        function moveActive(delta) {
            var items = Array.prototype.slice.call(
                optionsBox.querySelectorAll('.ps-select-option')
            );
            if (!items.length) {
                return;
            }
            if (activeIndex >= 0 && items[activeIndex]) {
                items[activeIndex].classList.remove('is-active');
            }
            activeIndex = (activeIndex + delta + items.length) % items.length;
            var current = items[activeIndex];
            current.classList.add('is-active');
            if (current.scrollIntoView) {
                current.scrollIntoView({ block: 'nearest' });
            }
        }

        search.addEventListener('keydown', function (event) {
            // Stop Bootstrap's dropdown keyboard nav from stealing arrow keys.
            event.stopPropagation();
            if (event.key === 'ArrowDown') {
                event.preventDefault();
                moveActive(1);
            } else if (event.key === 'ArrowUp') {
                event.preventDefault();
                moveActive(-1);
            } else if (event.key === 'Enter') {
                event.preventDefault();
                var items = Array.prototype.slice.call(
                    optionsBox.querySelectorAll('.ps-select-option')
                );
                var target = items[activeIndex >= 0 ? activeIndex : 0];
                if (target) {
                    choose(target.getAttribute('data-value'));
                }
            } else if (event.key === 'Escape') {
                closeMenu();
            }
        });

        // Keep the fixed menu aligned while the page scrolls or resizes.
        function reposition() {
            if (isOpen()) {
                positionMenu();
            }
        }
        window.addEventListener('scroll', reposition, true);
        window.addEventListener('resize', reposition);

        // Stay in sync when Django admin popups (or the select itself) change
        // the selected value.
        select.addEventListener('change', updateToggle);

        updateToggle();
    }

    ready(function () {
        var selects = document.querySelectorAll('select.ps-search-select');
        Array.prototype.forEach.call(selects, enhance);
    });
})();
