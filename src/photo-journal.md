# Photo journal

## June 2026

<div class="photo-collage" style="aspect-ratio: 1.237;">
  <figure class="photo-card" style="left: 1.8%; top: 0.85%; width: 20.05%; --rot: 1.92deg;"><img src="img/photo-journal/web/2026-06/HVlTD9v6WO87EzcZ5S1Y.jpg" loading="lazy" alt=""></figure>
  <figure class="photo-card" style="left: 52.55%; top: 0.0%; width: 21.18%; --rot: 2.63deg;"><img src="img/photo-journal/web/2026-06/IMG-20260601-WA0009.jpg" loading="lazy" alt=""></figure>
  <figure class="photo-card" style="left: 77.34%; top: 0.0%; width: 20.84%; --rot: -1.18deg;"><img src="img/photo-journal/web/2026-06/PXL_20260602_200748064.MP.jpg" loading="lazy" alt=""></figure>
  <figure class="photo-card" style="left: 1.65%; top: 80.01%; width: 21.46%; --rot: -1.34deg;"><img src="img/photo-journal/web/2026-06/PXL_20260604_205838188.jpg" loading="lazy" alt=""></figure>
  <figure class="photo-card" style="left: 28.15%; top: 0.0%; width: 20.14%; --rot: -2.29deg;"><img src="img/photo-journal/web/2026-06/PXL_20260611_211828118.jpg" loading="lazy" alt=""></figure>
  <figure class="photo-card" style="left: 51.45%; top: 41.28%; width: 21.29%; --rot: -2.82deg;"><img src="img/photo-journal/web/2026-06/PXL_20260612_144117516.jpg" loading="lazy" alt=""></figure>
  <figure class="photo-card" style="left: 76.96%; top: 41.68%; width: 20.23%; --rot: -2.39deg;"><img src="img/photo-journal/web/2026-06/PXL_20260613_140320081.jpg" loading="lazy" alt=""></figure>
  <figure class="photo-card" style="left: 26.22%; top: 40.08%; width: 20.91%; --rot: -1.1deg;"><img src="img/photo-journal/web/2026-06/PXL_20260613_145537671.jpg" loading="lazy" alt=""></figure>
  <figure class="photo-card" style="left: 1.72%; top: 40.94%; width: 20.33%; --rot: 1.63deg;"><img src="img/photo-journal/web/2026-06/PXL_20260613_204533674.jpg" loading="lazy" alt=""></figure>
</div>

## May 2026

<div class="photo-collage" style="aspect-ratio: 1.1337;">
  <figure class="photo-card" style="left: 76.2%; top: 0.0%; width: 21.15%; --rot: 2.1deg;"><img src="img/photo-journal/web/2026-05/IMG-20260523-WA0011 (1).jpg" loading="lazy" alt=""></figure>
  <figure class="photo-card" style="left: 26.56%; top: 0.52%; width: 20.46%; --rot: -2.58deg;"><img src="img/photo-journal/web/2026-05/PXL_20260502_151018322.jpg" loading="lazy" alt=""></figure>
  <figure class="photo-card" style="left: 52.92%; top: 46.44%; width: 20.01%; --rot: 1.99deg;"><img src="img/photo-journal/web/2026-05/PXL_20260502_152410416.jpg" loading="lazy" alt=""></figure>
  <figure class="photo-card" style="left: 77.1%; top: 47.22%; width: 20.7%; --rot: -2.9deg;"><img src="img/photo-journal/web/2026-05/PXL_20260504_192500418.jpg" loading="lazy" alt=""></figure>
  <figure class="photo-card" style="left: 1.93%; top: 45.89%; width: 20.95%; --rot: 2.1deg;"><img src="img/photo-journal/web/2026-05/PXL_20260517_090451323.jpg" loading="lazy" alt=""></figure>
  <figure class="photo-card" style="left: 2.22%; top: 81.85%; width: 21.26%; --rot: -1.24deg;"><img src="img/photo-journal/web/2026-05/PXL_20260523_191744320.jpg" loading="lazy" alt=""></figure>
  <figure class="photo-card" style="left: 27.73%; top: 45.73%; width: 21.22%; --rot: -1.09deg;"><img src="img/photo-journal/web/2026-05/PXL_20260531_120057670.MP (1).jpg" loading="lazy" alt=""></figure>
  <figure class="photo-card" style="left: 52.54%; top: 0.66%; width: 21.34%; --rot: -2.95deg;"><img src="img/photo-journal/web/2026-05/Screenshot 2026-06-14 at 12.10.43.jpg" loading="lazy" alt=""></figure>
  <figure class="photo-card" style="left: 2.0%; top: 1.01%; width: 20.39%; --rot: -1.47deg;"><img src="img/photo-journal/web/2026-05/original_7c25331b-2b0c-4014-99da-ad34f1e8d8aa_PXL_20260528_211811652.jpg" loading="lazy" alt=""></figure>
</div>

<div class="photo-lightbox" id="photo-lightbox" aria-hidden="true">
  <img src="" alt="">
</div>
<script>
(function () {
  var box = document.getElementById('photo-lightbox');
  var full = box.querySelector('img');
  function close() {
    box.classList.remove('open');
    box.setAttribute('aria-hidden', 'true');
    full.removeAttribute('src');
  }
  document.querySelectorAll('.photo-collage .photo-card img').forEach(function (img) {
    img.addEventListener('click', function () {
      full.src = img.currentSrc || img.src;
      box.classList.add('open');
      box.setAttribute('aria-hidden', 'false');
    });
  });
  box.addEventListener('click', close);
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') close();
  });
})();
</script>

