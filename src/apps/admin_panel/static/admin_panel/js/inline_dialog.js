/* Dialog-based inline admin forms.
 *
 * Turns an inline formset into a "grid + modal dialog" UI without changing how
 * the browser submits the form: the real, always-submitted Django formset forms
 * live in a hidden container, and the visible grid is a thin client-side view.
 *
 *   - "Add"  opens the modal with a blank form (a clone of the empty form).
 *   - "Edit" opens the modal pre-filled from the hidden row's form.
 *   - "Delete" hides the row and ticks the formset's DELETE checkbox, so the
 *     record is removed on save (Django skips the form on save).
 *
 * The row's fields are *moved* (not cloned) into the dialog so there is always
 * exactly one copy of every input and the formset stays valid. Kept in an
 * external file because the site CSP (`script-src 'self'`) blocks inline JS.
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

    function forEach(nodes, fn) {
        Array.prototype.forEach.call(nodes, fn);
    }

    function fieldNames(root) {
        return (root.getAttribute('data-ps-fields') || '')
            .split(',')
            .map(function (name) {
                return name.trim();
            })
            .filter(function (name) {
                return name.length > 0;
            });
    }

    function fullName(root, index, field) {
        return (root.getAttribute('data-ps-prefix') || '') + '-' + index + '-' + field;
    }

    function query(form, name) {
        return form ? form.querySelector('[name="' + name + '"]') : null;
    }

    function readValue(el) {
        if (!el) {
            return '';
        }
        if (el.type === 'checkbox' || el.type === 'radio') {
            return el.checked;
        }
        return el.value;
    }

    function writeValue(el, value) {
        if (!el) {
            return;
        }
        if (el.type === 'checkbox' || el.type === 'radio') {
            el.checked = !!value;
        } else {
            el.value = value == null ? '' : value;
        }
    }

    function setupFormset(root) {
        var prefix = root.getAttribute('data-ps-prefix') || '';
        var modalEl = document.getElementById('ps-inline-modal-' + prefix);
        var modal = window.bootstrap && modalEl ? new window.bootstrap.Modal(modalEl) : null;
        var body = root.querySelector('[data-ps-inline-dialog-body]');
        var container = root.querySelector('.ps-inline-forms');
        var totalInput = root.querySelector('input[name$="-TOTAL_FORMS"]');
        var maxInput = root.querySelector('input[name$="-MAX_NUM_FORMS"]');
        var applyBtn = root.querySelector('[data-ps-inline-apply]');
        var labels = {
            edit: root.getAttribute('data-label-edit') || 'Edit',
            delete: root.getAttribute('data-label-delete') || 'Delete'
        };
        var confirmDelete = root.getAttribute('data-msg-confirm-delete') || 'Delete this item?';

        // The row whose fields are currently living inside the dialog.
        var activeFields = null;
        var activeForm = null;
        var snapshot = null;
        var committed = false;

        function maxNum() {
            if (!maxInput || maxInput.value === '') {
                return null;
            }
            var n = parseInt(maxInput.value, 10);
            return isNaN(n) ? null : n;
        }

        function formByIndex(index) {
            return root.querySelector(
                '.ps-inline-form[data-index="' + index + '"]:not([data-ps-inline-empty])'
            );
        }

        function rowByIndex(index) {
            return root.querySelector('.ps-inline-row[data-index="' + index + '"]');
        }

        function createForm(index) {
            var template = root.querySelector('[data-ps-inline-empty="1"]');
            if (!container || !template) {
                return null;
            }
            var html = template.outerHTML.split('__prefix__').join(String(index));
            var holder = document.createElement('div');
            holder.innerHTML = html;
            var node = holder.firstElementChild;
            if (!node) {
                return null;
            }
            node.removeAttribute('data-ps-inline-empty');
            node.setAttribute('data-index', String(index));
            node.setAttribute('data-ps-new', '1');
            container.appendChild(node);
            return node;
        }

        function makeButton(text, className) {
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = className;
            btn.textContent = text;
            return btn;
        }

        function createRow(index) {
            var tbody = root.querySelector('[data-ps-inline-grid] tbody');
            if (!tbody) {
                return null;
            }
            var form = formByIndex(index);
            var tr = document.createElement('tr');
            tr.className = 'ps-inline-row';
            tr.setAttribute('data-ps-inline-row', '');
            tr.setAttribute('data-index', String(index));
            fieldNames(root).forEach(function (field) {
                var name = fullName(root, index, field);
                var td = document.createElement('td');
                td.setAttribute('data-ps-field', name);
                var input = query(form, name);
                if (input && input.type === 'hidden') {
                    td.className = 'hidden';
                }
                td.textContent = '\u2014';
                tr.appendChild(td);
            });
            var actions = document.createElement('td');
            actions.className = 'ps-inline-actions';
            actions.appendChild(makeButton(labels.edit, 'ps-btn ps-outline ps-inline-edit'));
            actions.appendChild(makeButton(labels.delete, 'ps-btn ps-danger ps-inline-delete-btn'));
            tr.appendChild(actions);
            tbody.appendChild(tr);
            return tr;
        }

        function updateEmptyState() {
            var empty = root.querySelector('[data-ps-inline-empty-msg]');
            if (!empty) {
                return;
            }
            var visible = root.querySelectorAll('.ps-inline-row:not([hidden])');
            empty.hidden = visible.length > 0;
        }

        function syncRow(index) {
            var form = formByIndex(index);
            var row = rowByIndex(index);
            if (!form || !row) {
                return;
            }
            forEach(row.querySelectorAll('td[data-ps-field]'), function (cell) {
                var el = query(form, cell.getAttribute('data-ps-field'));
                if (el && (el.type === 'checkbox' || el.type === 'radio')) {
                    cell.textContent = el.checked ? '\u2713' : '\u2014';
                    return;
                }
                var value = readValue(el);
                cell.textContent = value === '' || value == null ? '\u2014' : value;
            });
        }

        function takeSnapshot(form) {
            var data = {};
            forEach(form.querySelectorAll('input, select, textarea'), function (el) {
                if (el.name) {
                    data[el.name] = readValue(el);
                }
            });
            return data;
        }

        function restoreSnapshot(form, data) {
            if (!data) {
                return;
            }
            Object.keys(data).forEach(function (name) {
                writeValue(query(form, name), data[name]);
            });
        }

        function openDialog(index) {
            if (!body) {
                return;
            }
            var form = formByIndex(index);
            var fields = form ? form.querySelector('.ps-inline-fields') : null;
            if (!form || !fields) {
                return;
            }
            body.appendChild(fields);
            activeFields = fields;
            activeForm = form;
            snapshot = takeSnapshot(form);
            committed = false;
            if (modal) {
                modal.show();
            }
        }

        function closeDialog() {
            if (activeFields && activeForm) {
                if (!committed) {
                    restoreSnapshot(activeForm, snapshot);
                }
                activeForm.appendChild(activeFields);
                syncRow(activeForm.getAttribute('data-index'));
            }
            activeFields = null;
            activeForm = null;
            snapshot = null;
            committed = false;
        }

        function addRow() {
            if (!totalInput) {
                return;
            }
            var index = parseInt(totalInput.value, 10) || 0;
            var max = maxNum();
            if (max !== null && max !== 0 && index >= max) {
                return;
            }
            totalInput.value = String(index + 1);
            var form = createForm(index);
            if (!form) {
                totalInput.value = String(index);
                return;
            }
            createRow(index);
            updateEmptyState();
            openDialog(index);
        }

        function deleteRow(index) {
            var form = formByIndex(index);
            var row = rowByIndex(index);
            if (form) {
                var del = form.querySelector('input[type="checkbox"][name$="-DELETE"]');
                if (del) {
                    del.checked = true;
                }
            }
            if (row) {
                row.hidden = true;
            }
            updateEmptyState();
        }

        root.addEventListener('click', function (event) {
            var target = event.target;
            if (!target.closest) {
                return;
            }
            var row = target.closest('.ps-inline-row');
            if (row) {
                var index = row.getAttribute('data-index');
                if (target.classList.contains('ps-inline-edit')) {
                    openDialog(index);
                } else if (target.classList.contains('ps-inline-delete-btn')) {
                    if (window.confirm(confirmDelete)) {
                        deleteRow(index);
                    }
                }
                return;
            }
            if (target.classList.contains('ps-inline-add')) {
                addRow();
            }
        });

        if (applyBtn) {
            applyBtn.addEventListener('click', function () {
                committed = true;
                if (modal) {
                    modal.hide();
                } else {
                    closeDialog();
                }
            });
        }

        if (modalEl) {
            modalEl.addEventListener('hidden.bs.modal', closeDialog);
        }

        // Populate the grid from the authoritative formset values on load.
        forEach(root.querySelectorAll('.ps-inline-row'), function (row) {
            syncRow(row.getAttribute('data-index'));
        });
        updateEmptyState();
    }

    ready(function () {
        forEach(document.querySelectorAll('[data-ps-inline]'), setupFormset);
    });
})();
