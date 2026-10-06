import { storeConfig } from '../data/store-config.js';
import { createBrandLogo } from './BrandLogo.js';

export function createReassuranceAndFooter() {
  const wrapper = document.createElement('div');
  wrapper.id = 'reassurance';

  wrapper.innerHTML = `
    <!-- Reassurance Strip -->
    <section class="reassurance-strip" aria-label="Customer Reassurance & Guarantees">
      <div class="container">
        <div class="reassurance-grid">
          ${storeConfig.reassurance.map(item => `
            <div class="reassurance-item">
              <div class="reassurance-icon">
                ${getIconSvg(item.icon)}
              </div>
              <div>
                <h3 class="reassurance-title">${item.title}</h3>
                <p class="reassurance-desc">${item.desc}</p>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    </section>

    <!-- FAQ Section -->
    <section class="section" id="faq" aria-label="Frequently Asked Questions">
      <div class="container">
        <div class="section-header" style="text-align: center; max-width: 600px; margin-left: auto; margin-right: auto;">
          <h2 class="section-title">Frequently Asked Questions</h2>
          <p class="section-subtitle">Everything you need to know before ordering.</p>
        </div>

        <div class="faq-list">
          ${storeConfig.faqs.map((faq, index) => `
            <div class="faq-item ${index === 0 ? 'is-open' : ''}">
              <button class="faq-question" aria-expanded="${index === 0}">
                <span>${faq.q}</span>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="faq-chevron" style="transition: transform 200ms ease; transform: ${index === 0 ? 'rotate(180deg)' : 'rotate(0)'};">
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              </button>
              <div class="faq-answer">
                ${faq.a}
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    </section>

    <!-- Site Footer -->
    <footer class="site-footer">
      <div class="container">
        <div class="footer-top-grid">
          <div>
            <div id="footer-logo-slot" style="margin-bottom: 16px;"></div>
            <p class="footer-brand-desc">
              ${storeConfig.tagline}. Purpose-built apparel combining timeless cuts with dependable construction.
            </p>
          </div>

          <div>
            <h4 class="footer-heading">Shop</h4>
            <ul class="footer-link-list">
              ${storeConfig.footerLinks.shop.map(link => `
                <li><a href="${link.href}" class="footer-link">${link.label}</a></li>
              `).join('')}
            </ul>
          </div>

          <div>
            <h4 class="footer-heading">Customer Care</h4>
            <ul class="footer-link-list">
              ${storeConfig.footerLinks.customerCare.map(link => `
                <li><a href="${link.href}" class="footer-link">${link.label}</a></li>
              `).join('')}
            </ul>
          </div>

          <div>
            <h4 class="footer-heading">Need Assistance?</h4>
            <p class="footer-link" style="margin-bottom: 12px; line-height: 1.4;">
              Questions about sizing or dispatch times? Reach our team directly.
            </p>
            <a href="https://wa.me/yourwhatsapp" target="_blank" rel="noopener noreferrer" class="btn btn-primary" style="background-color: #25D366; border-color: #25D366; color: #FFFFFF; font-size: 0.875rem; padding: 10px 18px; min-height: 44px;">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l-.999 3.648 3.742-.981z"/>
              </svg>
              Chat on WhatsApp
            </a>
          </div>
        </div>

        <div class="footer-bottom">
          <div>© ${new Date().getFullYear()} AlphaZee. All verified rights reserved.</div>
          <div style="display: flex; gap: 24px;">
            ${storeConfig.footerLinks.legal.map(l => `
              <a href="${l.href}" class="footer-link">${l.label}</a>
            `).join('')}
          </div>
        </div>
      </div>
    </footer>
  `;

  // Mount Footer Brand Logo (Combined logo ~185px on dark surface)
  const footerLogoSlot = wrapper.querySelector('#footer-logo-slot');
  if (footerLogoSlot) {
    const footerLogo = createBrandLogo({
      variant: 'combined',
      surface: 'dark',
      width: 185, // 170–200px wide
      ariaLabel: 'AlphaZee home',
    });
    footerLogoSlot.appendChild(footerLogo);
  }

  // Accordion Logic
  wrapper.querySelectorAll('.faq-item').forEach(item => {
    const btn = item.querySelector('.faq-question');
    const chevron = item.querySelector('.faq-chevron');

    btn.addEventListener('click', () => {
      const isOpen = item.classList.contains('is-open');
      
      // Close others
      wrapper.querySelectorAll('.faq-item').forEach(other => {
        other.classList.remove('is-open');
        other.querySelector('.faq-question').setAttribute('aria-expanded', 'false');
        other.querySelector('.faq-chevron').style.transform = 'rotate(0deg)';
      });

      if (!isOpen) {
        item.classList.add('is-open');
        btn.setAttribute('aria-expanded', 'true');
        chevron.style.transform = 'rotate(180deg)';
      }
    });
  });

  return wrapper;
}

function getIconSvg(iconName) {
  if (iconName === 'truck') {
    return `
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="1" y="3" width="15" height="13"></rect>
        <polygon points="16 8 20 8 23 11 23 16 16 16 16 8"></polygon>
        <circle cx="5.5" cy="18.5" r="2.5"></circle>
        <circle cx="18.5" cy="18.5" r="2.5"></circle>
      </svg>
    `;
  }
  if (iconName === 'shield-check') {
    return `
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
        <polyline points="9 12 11 14 15 10"></polyline>
      </svg>
    `;
  }
  return `
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>
    </svg>
  `;
}
