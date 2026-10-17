/* ============================================================
   AjaxCart plugin — fetch-based cart client.

   Progressive enhancement: the server-rendered add-to-cart form still
   works without JavaScript. When this script loads it intercepts the
   product buy form and keeps the drawer / cart page in sync through the
   existing DRF cart API (same session as the SSR pages).
   ============================================================ */
(function () {
    'use strict';

    if (typeof window.fetch !== 'function') {
        return;
    }

    var config = null;

    function readConfig() {
        var root = document.querySelector('[data-ajax-cart]');
        if (!root) {
            return null;
        }
        var data = root.dataset;
        return {
            root: root,
            endpoint: data.ajaxCartEndpoint || '/api/v1/cart',
            openOnAdd: data.ajaxCartOpenOnAdd !== 'false',
            symbol: data.ajaxCartSymbol || '',
            decimals: parseInt(data.ajaxCartDecimals, 10) || 0,
            emptyMessage: data.ajaxCartEmptyMessage || '',
            checkoutLabel: data.ajaxCartCheckoutLabel || '',
            freeShipping: data.ajaxCartFreeShipping || '',
            labels: {
                remove: data.ajaxCartRemoveLabel || 'Remove',
                decrease: data.ajaxCartDecreaseLabel || '-',
                increase: data.ajaxCartIncreaseLabel || '+',
                quantity: data.ajaxCartQuantityLabel || 'Quantity',
                items: data.ajaxCartItemsLabel || 'items',
                error: data.ajaxCartErrorLabel || 'Request failed',
                added: data.ajaxCartAddedLabel || 'Added to cart.',
                qualified: data.ajaxCartFreeShippingQualified || '',
                remaining: data.ajaxCartFreeShippingRemaining || ''
            }
        };
    }

    function getCookie(name) {
        var match = document.cookie.match(new RegExp('(^|;\\s*)' + name + '=([^;]*)'));
        return match ? decodeURIComponent(match[2]) : '';
    }

    function escapeHtml(value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function formatMoney(raw) {
        var value = parseFloat(raw);
        if (isNaN(value)) {
            return raw == null ? '' : String(raw);
        }
        var parts = value.toFixed(config.decimals).split('.');
        parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',');
        var text = parts.join('.');
        return config.symbol ? text + ' ' + config.symbol : text;
    }

    function errorMessage(data) {
        if (!data) {
            return '';
        }
        if (typeof data === 'string') {
            return data;
        }
        if (data.error && data.error.message) {
            return data.error.message;
        }
        if (data.detail) {
            return data.detail;
        }
        var found = '';
        Object.keys(data).some(function (key) {
            var value = data[key];
            if (Array.isArray(value) && value.length) {
                found = String(value[0]);
                return true;
            }
            if (typeof value === 'string') {
                found = value;
                return true;
            }
            return false;
        });
        return found;
    }

    function request(method, path, body) {
        var options = {
            method: method,
            credentials: 'same-origin',
            headers: { Accept: 'application/json' }
        };
        if (method !== 'GET') {
            options.headers['X-CSRFToken'] = getCookie('csrftoken');
        }
        if (body !== undefined) {
            options.headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(body);
        }
        return fetch(config.endpoint + path, options).then(function (response) {
            if (response.status === 204) {
                return null;
            }
            return response.text().then(function (text) {
                var data = null;
                if (text) {
                    try {
                        data = JSON.parse(text);
                    } catch (error) {
                        data = null;
                    }
                }
                if (!response.ok) {
                    throw new Error(errorMessage(data) || config.labels.error);
                }
                return data;
            });
        });
    }

    function each(selector, callback) {
        Array.prototype.slice.call(document.querySelectorAll(selector)).forEach(callback);
    }

    function showMessage(text, isSuccess) {
        each('[data-ajax-cart-message]', function (element) {
            element.textContent = text;
            element.classList.toggle('is-success', !!isSuccess);
            element.hidden = !text;
        });
    }

    function lineMarkup(line) {
        var initial = (line.product_name || '').trim().charAt(0).toUpperCase();
        return '' +
            '<div class="ajax-cart-line" data-ajax-cart-line data-item-id="' + escapeHtml(line.item_id) + '">' +
                '<span class="ajax-cart-line-media" aria-hidden="true">' + escapeHtml(initial) + '</span>' +
                '<div class="ajax-cart-line-body">' +
                    '<span class="ajax-cart-line-name">' + escapeHtml(line.product_name) + '</span>' +
                    '<p class="ajax-cart-line-unit">' + formatMoney(line.unit_price) + '</p>' +
                    '<div class="ajax-cart-qty">' +
                        '<button type="button" data-ajax-cart-dec data-item-id="' + escapeHtml(line.item_id) + '" ' +
                            'aria-label="' + escapeHtml(config.labels.decrease) + '">&#8722;</button>' +
                        '<input type="number" min="1" value="' + escapeHtml(line.quantity) + '" ' +
                            'data-ajax-cart-qty data-item-id="' + escapeHtml(line.item_id) + '" ' +
                            'aria-label="' + escapeHtml(config.labels.quantity) + '">' +
                        '<button type="button" data-ajax-cart-inc data-item-id="' + escapeHtml(line.item_id) + '" ' +
                            'aria-label="' + escapeHtml(config.labels.increase) + '">+</button>' +
                    '</div>' +
                    '<button type="button" class="ajax-cart-remove" data-ajax-cart-remove ' +
                        'data-item-id="' + escapeHtml(line.item_id) + '">' + escapeHtml(config.labels.remove) + '</button>' +
                '</div>' +
                '<div class="ajax-cart-line-total">' + formatMoney(line.line_total) + '</div>' +
            '</div>';
    }

    function renderProgress(subtotal) {
        if (!config.freeShipping) {
            return;
        }
        var threshold = parseFloat(config.freeShipping);
        var value = parseFloat(subtotal);
        if (isNaN(threshold) || threshold <= 0 || isNaN(value)) {
            return;
        }
        var qualified = value >= threshold;
        var text = qualified
            ? config.labels.qualified
            : config.labels.remaining.replace('{amount}', formatMoney(String(Math.max(threshold - value, 0))));
        var percent = Math.min(100, Math.round((value / threshold) * 100));
        each('[data-ajax-cart-progress]', function (element) {
            element.hidden = false;
            element.innerHTML = escapeHtml(text) +
                '<span class="ajax-cart-progress-bar"><span style="width: ' + percent + '%"></span></span>';
        });
    }

    function render(cart) {
        var lines = (cart && cart.lines) || [];
        var count = lines.reduce(function (total, line) {
            return total + (parseInt(line.quantity, 10) || 0);
        }, 0);
        var hasItems = lines.length > 0;

        each('[data-ajax-cart-lines]', function (element) {
            element.innerHTML = lines.map(lineMarkup).join('');
        });

        each('[data-ajax-cart-content]', function (element) {
            element.hidden = !hasItems;
        });
        each('[data-ajax-cart-empty]', function (element) {
            element.hidden = hasItems;
        });

        each('[data-ajax-cart-subtotal]', function (element) {
            element.textContent = formatMoney(cart ? cart.subtotal : '0');
        });
        each('[data-ajax-cart-total]', function (element) {
            element.textContent = formatMoney(cart ? cart.total : '0');
        });

        var discount = cart ? parseFloat(cart.discount_amount) : 0;
        var hasDiscount = !isNaN(discount) && discount > 0;
        each('[data-ajax-cart-discount]', function (element) {
            element.textContent = formatMoney(cart ? cart.discount_amount : '0');
        });
        each('[data-ajax-cart-discount-row]', function (element) {
            element.hidden = !hasDiscount;
        });

        var coupon = cart ? cart.coupon_code : '';
        each('[data-ajax-cart-coupon-applied]', function (element) {
            element.hidden = !coupon;
        });
        each('[data-ajax-cart-coupon-code]', function (element) {
            element.textContent = coupon || '';
        });

        each('[data-ajax-cart-count]', function (element) {
            element.textContent = String(count);
            element.hidden = count === 0;
        });
        each('[data-ajax-cart-page-count]', function (element) {
            element.textContent = count + ' ' + config.labels.items;
            element.hidden = count === 0;
        });

        if (config.freeShipping && hasItems) {
            renderProgress(cart ? cart.subtotal : '0');
        } else {
            each('[data-ajax-cart-progress]', function (element) {
                element.hidden = true;
            });
        }
    }

    function openDrawer() {
        var root = config.root;
        if (root && window.bootstrap && window.bootstrap.Offcanvas) {
            window.bootstrap.Offcanvas.getOrCreateInstance(root).show();
        } else if (root) {
            root.classList.add('show');
            root.style.visibility = 'visible';
        }
    }

    function refresh() {
        return request('GET', '').then(render).catch(function (error) {
            showMessage(error.message || config.labels.error, false);
        });
    }

    function setQuantity(itemId, quantity) {
        if (quantity <= 0) {
            return request('DELETE', '/items/' + encodeURIComponent(itemId)).then(refresh);
        }
        return request('PATCH', '/items/' + encodeURIComponent(itemId), { quantity: quantity }).then(render);
    }

    function addToCart(form) {
        var slug = form.getAttribute('data-product-slug');
        if (!slug) {
            return false;
        }
        var select = form.querySelector('select[name="variant"]');
        var sku = '';
        if (select && select.options.length) {
            var option = select.options[select.selectedIndex];
            sku = option ? (option.getAttribute('data-sku') || '') : '';
        }
        var quantityInput = form.querySelector('input[name="quantity"]');
        var quantity = parseInt(quantityInput ? quantityInput.value : '1', 10);
        if (isNaN(quantity) || quantity < 1) {
            quantity = 1;
        }
        var payload = { product: slug, quantity: quantity };
        if (sku) {
            payload.variant = sku;
        }
        var button = form.querySelector('button[type="submit"]');
        if (button) {
            button.disabled = true;
        }
        request('POST', '/items', payload)
            .then(function (cart) {
                showMessage(config.labels.added, true);
                render(cart);
                if (config.openOnAdd) {
                    openDrawer();
                }
            })
            .catch(function (error) {
                showMessage(error.message || config.labels.error, false);
                if (config.openOnAdd) {
                    openDrawer();
                }
            })
            .then(function () {
                if (button) {
                    button.disabled = false;
                }
            });
        return true;
    }

    function applyCoupon(form) {
        var input = form.querySelector('input[name="code"]');
        var code = input ? input.value.trim() : '';
        if (!code) {
            return;
        }
        request('POST', '/coupon', { code: code })
            .then(function (cart) {
                if (input) {
                    input.value = '';
                }
                showMessage('', false);
                render(cart);
            })
            .catch(function (error) {
                showMessage(error.message || config.labels.error, false);
            });
    }

    function wire() {
        document.addEventListener('submit', function (event) {
            var form = event.target;
            if (!form || !form.classList) {
                return;
            }
            if (form.classList.contains('product-buy') && form.getAttribute('data-product-slug')) {
                if (addToCart(form)) {
                    event.preventDefault();
                }
                return;
            }
            if (form.hasAttribute('data-ajax-cart-coupon-form')) {
                event.preventDefault();
                applyCoupon(form);
            }
        });

        document.addEventListener('click', function (event) {
            var target = event.target;
            if (!target || !target.closest) {
                return;
            }
            var remove = target.closest('[data-ajax-cart-remove]');
            if (remove) {
                event.preventDefault();
                setQuantity(remove.getAttribute('data-item-id'), 0).catch(function (error) {
                    showMessage(error.message || config.labels.error, false);
                });
                return;
            }
            var dec = target.closest('[data-ajax-cart-dec]');
            if (dec) {
                event.preventDefault();
                var decLine = dec.closest('[data-ajax-cart-line]');
                var decInput = decLine ? decLine.querySelector('[data-ajax-cart-qty]') : null;
                var decValue = Math.max(1, (parseInt(decInput ? decInput.value : '1', 10) || 1) - 1);
                setQuantity(dec.getAttribute('data-item-id'), decValue).catch(function (error) {
                    showMessage(error.message || config.labels.error, false);
                });
                return;
            }
            var inc = target.closest('[data-ajax-cart-inc]');
            if (inc) {
                event.preventDefault();
                var incLine = inc.closest('[data-ajax-cart-line]');
                var incInput = incLine ? incLine.querySelector('[data-ajax-cart-qty]') : null;
                var incValue = (parseInt(incInput ? incInput.value : '1', 10) || 1) + 1;
                setQuantity(inc.getAttribute('data-item-id'), incValue).catch(function (error) {
                    showMessage(error.message || config.labels.error, false);
                });
                return;
            }
            var couponRemove = target.closest('[data-ajax-cart-coupon-remove]');
            if (couponRemove) {
                event.preventDefault();
                request('DELETE', '/coupon')
                    .then(function () {
                        showMessage('', false);
                        return refresh();
                    })
                    .catch(function (error) {
                        showMessage(error.message || config.labels.error, false);
                    });
            }
        });

        document.addEventListener('change', function (event) {
            var input = event.target;
            if (!input || !input.hasAttribute || !input.hasAttribute('data-ajax-cart-qty')) {
                return;
            }
            var quantity = parseInt(input.value, 10);
            if (isNaN(quantity) || quantity < 1) {
                quantity = 1;
            }
            setQuantity(input.getAttribute('data-item-id'), quantity).catch(function (error) {
                showMessage(error.message || config.labels.error, false);
            });
        });
    }

    function init() {
        config = readConfig();
        if (!config) {
            return;
        }
        wire();
        refresh();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
