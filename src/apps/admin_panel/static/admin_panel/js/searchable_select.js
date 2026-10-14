/* Searchable select (Bootstrap 5 combobox).
 *
 * Progressively enhances every native <select class="ps-search-select"> into a
 * Bootstrap 5 dropdown with a live text filter. The native <select> is kept in
 * the DOM (just visually hidden) so form submission, validation and Django's
 * admin "add related" popups keep working unchanged. Kept in an external file
 * because the site Content-Security-Policy (`script-src 'self'`) blocks inline
 * JavaScript.
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
        wrap.className = 'dropdown ps-select';

        var toggle = document.createElement('button');
        toggle.type = 'button';
        toggle.className = 'btn btn-outline-secondary dropdown-toggle ps-select-toggle';
        toggle.setAttribute('data-bs-toggle', 'dropdown');
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
        wrap.appendChild(menu);

        select.parentNode.insertBefore(wrap, select.nextSibling);
        select.classList.add('ps-search-select-native');

        var dropdown = window.bootstrap
            ? window.bootstrap.Dropdown.getOrCreateInstance(toggle)
            : null;

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
            if (dropdown) {
                dropdown.show();
            }
            window.setTimeout(function () {
                search.focus();
            }, 0);
        }

        function choose(value) {
            select.value = value;
            updateToggle();
            if (dropdown) {
                dropdown.hide();
            }
            fireChange(select);
        }

        toggle.addEventListener('click', function () {
            // Bootstrap toggles the menu; populate and focus it once it is shown.
            window.setTimeout(function () {
                if (menu.classList.contains('show')) {
                    openMenu();
                }
            }, 0);
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
            } else if (event.key === 'Escape' && dropdown) {
                dropdown.hide();
            }
        });

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
