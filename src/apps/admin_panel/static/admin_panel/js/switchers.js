/* Admin language switcher.
 *
 * The inline `onchange="this.form.submit()"` attribute is blocked by the
 * site Content-Security-Policy (`script-src 'self'`, no 'unsafe-inline'),
 * which made selecting a language appear to do nothing. This external file
 * binds the same behaviour without inline JavaScript.
 */
(function () {
    'use strict';

    function bindSwitchers() {
        var selects = document.querySelectorAll('.ps-lang-switch select[name="language"]');
        Array.prototype.forEach.call(selects, function (select) {
            if (select.dataset.switcherBound === '1') {
                return;
            }
            select.dataset.switcherBound = '1';
            select.addEventListener('change', function () {
                if (select.form) {
                    select.form.submit();
                }
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bindSwitchers);
    } else {
        bindSwitchers();
    }
})();
