/* Product images dialog.
 *
 * The Product images inline was replaced by a Bootstrap 5 modal that lists the
 * product's images and lets the user upload new ones. Uploads go through
 * XMLHttpRequest so `xhr.upload.onprogress` can drive a progress bar while the
 * file is transferred. Kept in an external file because the site
 * Content-Security-Policy (`script-src 'self'`) blocks inline JavaScript.
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

    ready(function () {
        var root = document.getElementById('ps-product-images');
        if (!root) {
            return;
        }

        var uploadUrl = root.getAttribute('data-upload-url') || '';
        var maxMb = parseInt(root.getAttribute('data-max-size-mb') || '10', 10);
        // Localised UI strings come from data-* attributes on the wrapper so the
        // dialog follows the active admin language without inline JavaScript.
        var msgs = {
            choose: root.getAttribute('data-msg-choose') || 'Choose an image first.',
            saveFirst: root.getAttribute('data-msg-save-first') || 'Save the product first to add images.',
            uploading: root.getAttribute('data-msg-uploading') || 'Uploading...',
            uploaded: root.getAttribute('data-msg-uploaded') || 'Upload complete.',
            deleted: root.getAttribute('data-msg-deleted') || 'Image deleted.',
            mainUpdated: root.getAttribute('data-msg-main-updated') || 'Main image updated.',
            confirmDelete: root.getAttribute('data-msg-confirm-delete') || 'Delete this image?'
        };
        var labels = {
            setMain: root.getAttribute('data-label-set-main') || 'Set main',
            main: root.getAttribute('data-label-main') || 'Main',
            delete: root.getAttribute('data-label-delete') || 'Delete'
        };
        var modalEl = document.getElementById('ps-images-modal');
        var openBtn = document.getElementById('ps-open-images-dialog');
        var listEl = document.getElementById('ps-images-list');
        var emptyEl = document.getElementById('ps-images-empty');
        var fileInput = document.getElementById('ps-image-file');
        var altInput = document.getElementById('ps-image-alt-input');
        var uploadBtn = document.getElementById('ps-image-upload-btn');
        var progressWrap = document.getElementById('ps-upload-progress-wrap');
        var progressBar = document.getElementById('ps-upload-progress');
        var statusEl = document.getElementById('ps-upload-status');

        var modal = window.bootstrap && modalEl ? new window.bootstrap.Modal(modalEl) : null;

        function csrfToken() {
            var input = document.querySelector('input[name="csrfmiddlewaretoken"]');
            return input ? input.value : '';
        }

        function setStatus(text, kind) {
            if (!statusEl) {
                return;
            }
            statusEl.textContent = text || '';
            statusEl.className = 'ps-upload-status' + (kind ? ' is-' + kind : '');
        }

        function setProgress(pct) {
            if (!progressWrap || !progressBar) {
                return;
            }
            progressWrap.hidden = false;
            progressBar.style.width = pct + '%';
            progressBar.setAttribute('aria-valuenow', String(pct));
            progressBar.textContent = pct + '%';
        }

        function hideProgress() {
            if (progressWrap) {
                progressWrap.hidden = true;
            }
        }

        function buildRow(image) {
            var row = document.createElement('div');
            row.className = 'ps-image-row';
            row.setAttribute('data-image-id', image.id);
            row.setAttribute('data-delete-url', image.delete_url);
            row.setAttribute('data-main-url', image.main_url);
            row.setAttribute('data-update-url', image.update_url);

            var thumb = document.createElement('img');
            thumb.className = 'ps-image-thumb';
            thumb.src = image.url;
            thumb.alt = image.alt_text || '';
            row.appendChild(thumb);

            var alt = document.createElement('input');
            alt.type = 'text';
            alt.className = 'ps-image-alt';
            alt.value = image.alt_text || '';
            row.appendChild(alt);

            var mainBtn = document.createElement('button');
            mainBtn.type = 'button';
            mainBtn.className = 'ps-btn ps-outline ps-image-main';
            if (image.is_main) {
                mainBtn.disabled = true;
                mainBtn.textContent = labels.main;
            } else {
                mainBtn.textContent = labels.setMain;
            }
            row.appendChild(mainBtn);

            var delBtn = document.createElement('button');
            delBtn.type = 'button';
            delBtn.className = 'ps-btn ps-danger ps-image-delete';
            delBtn.textContent = labels.delete;
            row.appendChild(delBtn);

            return row;
        }

        function post(url, data) {
            return fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken(),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: data,
                credentials: 'same-origin'
            }).then(function (resp) {
                return resp
                    .json()
                    .catch(function () {
                        return {};
                    })
                    .then(function (body) {
                        if (!resp.ok) {
                            throw new Error(body.error || 'HTTP ' + resp.status);
                        }
                        return body;
                    });
            });
        }

        function upload() {
            if (!uploadUrl) {
                setStatus(msgs.saveFirst, 'error');
                return;
            }
            if (!fileInput || !fileInput.files || !fileInput.files.length) {
                setStatus(msgs.choose, 'error');
                return;
            }
            var file = fileInput.files[0];
            if (maxMb && file.size > maxMb * 1024 * 1024) {
                setStatus('File exceeds the ' + maxMb + ' MB limit.', 'error');
                return;
            }

            var formData = new FormData();
            formData.append('image', file);
            formData.append('alt_text', altInput ? altInput.value : '');

            var xhr = new XMLHttpRequest();
            xhr.open('POST', uploadUrl, true);
            xhr.setRequestHeader('X-CSRFToken', csrfToken());
            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

            xhr.upload.onprogress = function (event) {
                if (event.lengthComputable) {
                    setProgress(Math.round((event.loaded / event.total) * 100));
                }
            };
            xhr.onload = function () {
                var body = {};
                try {
                    body = JSON.parse(xhr.responseText);
                } catch (e) {
                    body = {};
                }
                if (xhr.status >= 200 && xhr.status < 300 && body.ok) {
                    setProgress(100);
                    setStatus(msgs.uploaded, 'ok');
                    if (body.image && listEl) {
                        listEl.appendChild(buildRow(body.image));
                    }
                    if (emptyEl) {
                        emptyEl.hidden = true;
                    }
                    if (fileInput) {
                        fileInput.value = '';
                    }
                    if (altInput) {
                        altInput.value = '';
                    }
                    window.setTimeout(hideProgress, 800);
                } else {
                    hideProgress();
                    setStatus(body.error || 'Upload failed (HTTP ' + xhr.status + ')', 'error');
                }
                if (uploadBtn) {
                    uploadBtn.disabled = false;
                }
            };
            xhr.onerror = function () {
                hideProgress();
                setStatus('Network error during upload.', 'error');
                if (uploadBtn) {
                    uploadBtn.disabled = false;
                }
            };

            if (uploadBtn) {
                uploadBtn.disabled = true;
            }
            setProgress(0);
            setStatus(msgs.uploading, '');
            xhr.send(formData);
        }

        if (openBtn && modal) {
            openBtn.addEventListener('click', function () {
                modal.show();
            });
        }

        if (uploadBtn) {
            uploadBtn.addEventListener('click', upload);
        }

        if (listEl) {
            listEl.addEventListener('click', function (event) {
                var target = event.target;
                var row = target.closest ? target.closest('.ps-image-row') : null;
                if (!row) {
                    return;
                }
                if (target.classList.contains('ps-image-delete')) {
                    if (!window.confirm(msgs.confirmDelete)) {
                        return;
                    }
                    post(row.getAttribute('data-delete-url'), new URLSearchParams())
                        .then(function () {
                            row.remove();
                            setStatus(msgs.deleted, 'ok');
                            if (listEl.children.length === 0 && emptyEl) {
                                emptyEl.hidden = false;
                            }
                        })
                        .catch(function (err) {
                            setStatus(err.message, 'error');
                        });
                } else if (target.classList.contains('ps-image-main')) {
                    post(row.getAttribute('data-main-url'), new URLSearchParams())
                        .then(function () {
                            Array.prototype.forEach.call(
                                listEl.querySelectorAll('.ps-image-main'),
                                function (btn) {
                                    btn.disabled = false;
                                    btn.textContent = labels.setMain;
                                }
                            );
                            target.disabled = true;
                            target.textContent = labels.main;
                            setStatus(msgs.mainUpdated, 'ok');
                        })
                        .catch(function (err) {
                            setStatus(err.message, 'error');
                        });
                }
            });

            listEl.addEventListener('change', function (event) {
                var target = event.target;
                if (!target.classList.contains('ps-image-alt')) {
                    return;
                }
                var row = target.closest('.ps-image-row');
                if (!row) {
                    return;
                }
                var data = new URLSearchParams();
                data.append('alt_text', target.value);
                post(row.getAttribute('data-update-url'), data).catch(function (err) {
                    setStatus(err.message, 'error');
                });
            });
        }
    });
})();
