/* Tagify initialisation for the product tag input.
 *
 * Progressively enhances every `input.ps-tagify` (rendered by
 * `admin_panel.widgets.TagPickerWidget`) into a Tagify chip editor. The value
 * that is finally submitted stays a comma-separated string thanks to
 * `originalInputValueFormat`, so the server-side `clean_tags_input()` and
 * `save_related()` logic keeps working unchanged.
 *
 * Kept in an external file because the site Content-Security-Policy
 * (`script-src 'self'`) blocks inline JavaScript.
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

    function readWhitelist(id) {
        var holder = document.getElementById(id + '_data');
        if (!holder) {
            return [];
        }
        try {
            var parsed = JSON.parse(holder.textContent || '[]');
            return Array.isArray(parsed) ? parsed : [];
        } catch (e) {
            return [];
        }
    }

    function enhance(input) {
        if (input.dataset.psTagifyReady === '1' || !window.Tagify) {
            return;
        }
        input.dataset.psTagifyReady = '1';

        var whitelist = readWhitelist(input.id);
        var config = {
            delimiters: ',',
            maxTags: 50,
            dropdown: { enabled: 1, maxItems: 20, closeOnSelect: false },
            originalInputValueFormat: function (items) {
                return items
                    .map(function (item) {
                        return item.value;
                    })
                    .join(', ');
            }
        };
        if (whitelist.length) {
            config.whitelist = whitelist;
        }

        // eslint-disable-next-line no-new
        new window.Tagify(input, config);
    }

    ready(function () {
        var inputs = document.querySelectorAll('input.ps-tagify');
        Array.prototype.forEach.call(inputs, enhance);
    });
})();
