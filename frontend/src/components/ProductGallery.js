import { escapeHtml as esc, sanitizeMediaUrl, createSafeImageElement } from '../utils/dom.js';
import { mediaForVariant } from '../utils/productMedia.js';

export function mountProductGallery(host, product, variantId) {
  const media = mediaForVariant(product, variantId);
  const specific = media.findIndex(m => m.variant_id === variantId);
  let index = specific >= 0 ? specific : Math.max(0, media.findIndex(m => m.role === 'primary'));
  let alive = true;
  host.innerHTML = `<div class="product-gallery-stage"></div><div class="product-gallery-thumbs" role="group" aria-label="Product media">
    ${media.map((m,i) => `<button type="button" class="option-pill" data-gallery-index="${i}" aria-label="${esc((m.kind === 'video' ? 'Play video: ' : 'View image: ') + (m.alt_text || product.title))}" aria-pressed="${i === index}">${m.kind === 'video' ? 'Video' : 'Image'} ${i+1}</button>`).join('')}</div>
    <p class="product-media-feedback" role="status" aria-live="polite"></p>`;
  const stage = host.querySelector('.product-gallery-stage');
  const feedback = host.querySelector('[role="status"]');
  function pause() { stage.querySelectorAll('video').forEach(v => v.pause?.()); }
  function show(next) {
    pause(); index = next;
    const item = media[index];
    stage.innerHTML = ''; feedback.textContent = '';
    host.querySelectorAll('[data-gallery-index]').forEach(button => button.setAttribute('aria-pressed', String(Number(button.dataset.galleryIndex) === index)));
    if (item.kind === 'video') {
      const video = document.createElement('video');
      video.className = 'modal-img product-gallery-video'; video.controls = true; video.playsInline = true; video.preload = 'none';
      const poster = sanitizeMediaUrl(item.poster_url, '');
      if (poster) video.poster = poster;
      video.setAttribute('aria-label', item.alt_text || product.title);
      const supported = ['video/mp4','video/webm'].includes(item.content_type) && poster;
      if (supported) video.src = sanitizeMediaUrl(item.url, '');
      else feedback.textContent = 'This video is unavailable. Select another image or video.';
      video.addEventListener('error', () => { if (alive) feedback.textContent = 'This browser could not play the video. Select another image or video.'; });
      stage.appendChild(video);
    } else {
      const image = createSafeImageElement({src:item.url, alt:item.alt_text || product.title, className:'modal-img', loading:index === 0 ? 'eager' : 'lazy', width:item.width, height:item.height});
      image.addEventListener('error', () => { if (alive) feedback.textContent = 'This image could not load. Select another image.'; });
      stage.appendChild(image);
    }
  }
  host.querySelectorAll('[data-gallery-index]').forEach(button => button.addEventListener('click', () => show(Number(button.dataset.galleryIndex))));
  show(index);
  return { destroy() { alive = false; pause(); } };
}
