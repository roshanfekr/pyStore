(function () {
    'use strict';

    var STORAGE_KEY = 'pystore.admin.collapsedGroups';

    function getCollapsedIds() {
        try {
            return JSON.parse(sessionStorage.getItem(STORAGE_KEY)) || [];
        } catch (e) {
            return [];
        }
    }

    function saveCollapsedIds(ids) {
        try {
            sessionStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
        } catch (e) {}
    }

    function applyState(table, collapsed) {
        table.classList.toggle('is-collapsed', collapsed);
        var caption = table.querySelector('caption');
        if (caption) {
            caption.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
        }
    }

    function restoreAll(tables) {
        var collapsedIds = getCollapsedIds();
        tables.forEach(function (table) {
            applyState(table, collapsedIds.indexOf(table.id) !== -1);
        });
    }

    function init() {
        var tables = Array.prototype.slice.call(
            document.querySelectorAll('#nav-sidebar .psnav-collapsible')
        );
        if (!tables.length) {
            return;
        }

        restoreAll(tables);

        tables.forEach(function (table) {
            var caption = table.querySelector('caption');
            if (!caption) {
                return;
            }
            caption.setAttribute('role', 'button');
            caption.setAttribute('tabindex', '0');
            caption.addEventListener('click', function () {
                var collapsed = !table.classList.contains('is-collapsed');
                applyState(table, collapsed);

                var ids = getCollapsedIds();
                if (collapsed) {
                    if (ids.indexOf(table.id) === -1) {
                        ids.push(table.id);
                    }
                } else {
                    ids = ids.filter(function (id) {
                        return id !== table.id;
                    });
                }
                saveCollapsedIds(ids);
            });
            caption.addEventListener('keydown', function (e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    caption.click();
                }
            });
        });

        var filter = document.getElementById('nav-filter');
        if (filter) {
            filter.addEventListener('input', function () {
                if (filter.value) {
                    tables.forEach(function (table) {
                        applyState(table, false);
                    });
                } else {
                    restoreAll(tables);
                }
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
