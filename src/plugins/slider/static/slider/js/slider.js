(function () {
    'use strict';

    function initSlider(root) {
        var slides = Array.prototype.slice.call(root.querySelectorAll('.pslider-slide'));
        var dots = Array.prototype.slice.call(root.querySelectorAll('.pslider-dot'));
        var index = 0;
        var timer = null;
        var autoplay = parseInt(root.getAttribute('data-autoplay'), 10) || 0;

        function show(next) {
            index = (next + slides.length) % slides.length;
            slides.forEach(function (slide, i) {
                slide.classList.toggle('is-active', i === index);
            });
            dots.forEach(function (dot, i) {
                dot.classList.toggle('is-active', i === index);
            });
        }

        function play() {
            if (autoplay <= 0 || slides.length < 2) return;
            stop();
            timer = window.setInterval(function () {
                show(index + 1);
            }, autoplay);
        }

        function stop() {
            if (timer !== null) {
                window.clearInterval(timer);
                timer = null;
            }
        }

        var prev = root.querySelector('.pslider-arrow.is-prev');
        var next = root.querySelector('.pslider-arrow.is-next');

        if (prev) {
            prev.addEventListener('click', function () {
                show(index - 1);
                play();
            });
        }
        if (next) {
            next.addEventListener('click', function () {
                show(index + 1);
                play();
            });
        }

        dots.forEach(function (dot) {
            dot.addEventListener('click', function () {
                show(parseInt(dot.getAttribute('data-index'), 10) || 0);
                play();
            });
        });

        root.addEventListener('mouseenter', stop);
        root.addEventListener('mouseleave', play);

        play();
    }

    document.addEventListener('DOMContentLoaded', function () {
        Array.prototype.slice
            .call(document.querySelectorAll('.pslider'))
            .forEach(initSlider);
    });
})();
