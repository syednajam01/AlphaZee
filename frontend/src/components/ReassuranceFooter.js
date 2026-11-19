import { storeConfig } from '../data/store-config.js';
import { createBrandLogo } from './BrandLogo.js';
import { fetchPublicStoreSettings } from '../utils/api.js';

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function bindAccordion(root) {
  root.querySelectorAll('.faq-item').forEach(item => {
    const btn = item.querySelector('.faq-question');
    const chevron = item.querySelector('.faq-chevron');
    if (!btn || !chevron) return;

    btn.onclick = () => {
      const isOpen = item.classList.contains('is-open');

      // Close others
      root.querySelectorAll('.faq-item').forEach(other => {
        other.classList.remove('is-open');
        const ob = other.querySelector('.faq-question');
        const oc = other.querySelector('.faq-chevron');
        if (ob) ob.setAttribute('aria-expanded', 'false');
        if (oc) oc.style.transform = 'rotate(0deg)';
      });

      if (!isOpen) {
        item.classList.add('is-open');
        btn.setAttribute('aria-expanded', 'true');
        chevron.style.transform = 'rotate(180deg)';
      }
    };
  });
}

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
    <section class="section" id="faq" aria-label="Before you order">
      <div class="container">
        <div class="section-header">
          <h2 class="section-title">Before you order</h2>
          <p class="section-subtitle">A few useful answers, all in one place.</p>
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
              A considered selection of clothing and accessories. Find your next piece, and make it your own.
            </p>
            <img
              src="/logo/huda-brand-quote.png"
              alt="A vision by Syed Najam. A name carried with pride: Huda."
              class="footer-quote-img"
              width="2172"
              height="724"
              loading="lazy"
            />
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

          <div id="footer-assistance-slot">
            <h4 class="footer-heading">Need Assistance?</h4>
            <p class="footer-link" style="margin-bottom: 12px; line-height: 1.4;">
              Our support contact is not available yet. Please check the FAQ for sizing and delivery information.
            </p>
            <button type="button" disabled class="btn btn-secondary" style="font-size: 0.875rem; padding: 10px 18px; min-height: 44px;">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l-.999 3.648 3.742-.981z"/>
              </svg>
              Support unavailable
            </button>
          </div>
        </div>

        <div class="footer-bottom">
          <div>© ${new Date().getFullYear()} AlphaZee. All rights reserved.</div>
          <div style="display: flex; gap: 24px;">
            ${storeConfig.footerLinks.legal.map(l => `
              ${l.href ? `<a href="${l.href}" class="footer-link">${l.label}</a>` : `<span class="footer-link" aria-disabled="true">${l.label} (not yet available)</span>`}
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
      href: '/',
      ariaLabel: 'AlphaZee home',
    });
    footerLogoSlot.appendChild(footerLogo);
  }

  // Bind initial static accordions
  bindAccordion(wrapper);

  // Dynamically load live store settings if available
  fetchPublicStoreSettings().then(settings => {
    if (!settings) return;

    // 0. Dynamic Reassurance Badges from Admin Settings
    if (Array.isArray(settings.reassurance_items) && settings.reassurance_items.length > 0) {
      const reassuranceGrid = wrapper.querySelector('.reassurance-grid');
      if (reassuranceGrid) {
        reassuranceGrid.innerHTML = settings.reassurance_items.map(item => `
          <div class="reassurance-item">
            <div class="reassurance-icon">
              ${getIconSvg(item.icon)}
            </div>
            <div>
              <h3 class="reassurance-title">${escapeHtml(item.title)}</h3>
              <p class="reassurance-desc">${escapeHtml(item.description || item.desc || '')}</p>
            </div>
          </div>
        `).join('');
      }
    }

    // 0b. Dynamic FAQ Section Header & Subtitle
    const faqTitleEl = wrapper.querySelector('#faq .section-title');
    if (faqTitleEl && settings.faq_section_title) {
      faqTitleEl.textContent = settings.faq_section_title;
    }
    const faqSubtitleEl = wrapper.querySelector('#faq .section-subtitle');
    if (faqSubtitleEl && settings.faq_section_subtitle) {
      faqSubtitleEl.textContent = settings.faq_section_subtitle;
    }

    // 0c. Dynamic Storefront Footer Brand Quote
    if (settings.footer_quote) {
      const quoteEl = wrapper.querySelector('.footer-brand-desc');
      if (quoteEl) {
        quoteEl.textContent = settings.footer_quote;
      }
    }

    // 1. Dynamic FAQ Items from Admin Settings
    if (Array.isArray(settings.faq_items) && settings.faq_items.length > 0) {
      const activeFaqs = settings.faq_items.filter(f => f.is_enabled !== false);
      if (activeFaqs.length > 0) {
        const faqList = wrapper.querySelector('.faq-list');
        if (faqList) {
          faqList.innerHTML = activeFaqs.map((faq, index) => `
            <div class="faq-item ${index === 0 ? 'is-open' : ''}">
              <button class="faq-question" aria-expanded="${index === 0}">
                <span>${escapeHtml(faq.question)}</span>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="faq-chevron" style="transition: transform 200ms ease; transform: ${index === 0 ? 'rotate(180deg)' : 'rotate(0)'};">
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              </button>
              <div class="faq-answer">
                ${escapeHtml(faq.answer)}
              </div>
            </div>
          `).join('');
          bindAccordion(faqList);
        }
      }
    }

    // 2. Dynamic Customer Support (WhatsApp DM with Pre-filled Message & Gmail/Email 1-Click Inquiry)
    const assistanceSlot = wrapper.querySelector('#footer-assistance-slot');
    if (assistanceSlot && (settings.support_phone || settings.support_email)) {
      let buttonsHtml = '';

      if (settings.support_phone) {
        const phone = settings.support_phone.trim();
        const phoneClean = phone.replace(/[^0-9]/g, '');
        const prefillMsg = encodeURIComponent(settings.whatsapp_prefill_message || 'Hi AlphaZee, I have a question regarding my order:');
        buttonsHtml += `
          <a href="https://wa.me/${phoneClean}?text=${prefillMsg}" target="_blank" rel="noopener noreferrer" class="btn btn-whatsapp-action" style="font-size: 0.8125rem; font-weight: 600; padding: 10px 16px; min-height: 44px; display: inline-flex; align-items: center; justify-content: center; gap: 8px; background: #25D366; color: #052e16; border-radius: 6px; text-decoration: none; box-shadow: 0 2px 8px rgba(37, 211, 102, 0.25); transition: transform 0.15s ease, background 0.15s ease;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l-.999 3.648 3.742-.981z"/>
            </svg>
            Chat on WhatsApp
          </a>
        `;
      }

      if (settings.support_email) {
        const email = settings.support_email.trim();
        const subject = encodeURIComponent(settings.email_subject_template || 'AlphaZee Customer Inquiry');
        const body = encodeURIComponent(settings.email_body_template || '');
        buttonsHtml += `
          <a href="mailto:${email}?subject=${subject}&body=${body}" class="btn btn-email-action" style="font-size: 0.8125rem; font-weight: 500; padding: 10px 16px; min-height: 44px; display: inline-flex; align-items: center; justify-content: center; gap: 8px; background: rgba(255, 255, 255, 0.08); color: #F3F4F6; border: 1px solid rgba(255, 255, 255, 0.18); border-radius: 6px; text-decoration: none; transition: background 0.15s ease, border-color 0.15s ease;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
            Email Customer Care
          </a>
        `;
      }

      let hoursHtml = '';
      if (settings.support_hours) {
        hoursHtml = `<div style="display: inline-flex; align-items: center; gap: 6px; font-size: 0.75rem; color: #10B981; background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.2); padding: 4px 10px; border-radius: 4px; margin-bottom: 8px; width: fit-content;"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>${escapeHtml(settings.support_hours)}</div>`;
      }

      assistanceSlot.innerHTML = `
        <h4 class="footer-heading">Need Assistance?</h4>
        ${hoursHtml}
        <p class="footer-link" style="margin-bottom: 12px; line-height: 1.4;">
          Have questions before ordering? Connect directly with our team.
        </p>
        <div style="display: flex; flex-direction: column; gap: 8px;">
          ${buttonsHtml}
        </div>
      `;
    }
  }).catch(() => {});

  return wrapper;
}

function getIconSvg(iconName) {
  switch (iconName) {
    case 'truck':
      return `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="1" y="3" width="15" height="13"></rect>
        <polygon points="16 8 20 8 23 11 23 16 16 16 8"></polygon>
        <circle cx="5.5" cy="18.5" r="2.5"></circle>
        <circle cx="18.5" cy="18.5" r="2.5"></circle>
      </svg>`;
    case 'shield-check':
      return `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
        <polyline points="9 12 11 14 15 10"></polyline>
      </svg>`;
    case 'message-circle':
      return `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>
      </svg>`;
    case 'refresh-cw':
      return `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="23 4 23 10 17 10"></polyline>
        <polyline points="1 20 1 14 7 14"></polyline>
        <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
      </svg>`;
    case 'package':
      return `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <line x1="16.5" y1="9.4" x2="7.5" y2="4.21"></line>
        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
        <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
        <line x1="12" y1="22.08" x2="12" y2="12"></line>
      </svg>`;
    case 'award':
      return `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="8" r="7"></circle>
        <polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"></polyline>
      </svg>`;
    case 'lock':
      return `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
        <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
      </svg>`;
    case 'credit-card':
      return `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="1" y="4" width="22" height="16" rx="2" ry="2"></rect>
        <line x1="1" y1="10" x2="23" y2="10"></line>
      </svg>`;
    case 'leaf':
      return `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"></path>
        <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"></path>
      </svg>`;
    case 'zap':
      return `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
      </svg>`;
    case 'heart':
      return `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
      </svg>`;
    case 'globe':
      return `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="2" y1="12" x2="22" y2="12"></line>
        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
      </svg>`;
    case 'clock':
      return `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"></circle>
        <polyline points="12 6 12 12 16 14"></polyline>
      </svg>`;
    case 'headphones':
      return `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M3 18v-6a9 9 0 0 1 18 0v6"></path>
        <path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"></path>
      </svg>`;
    case 'check-circle':
      return `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
        <polyline points="22 4 12 14.01 9 11.01"></polyline>
      </svg>`;
    case 'sparkles':
      return `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"></path>
        <path d="M5 3v4"></path>
        <path d="M19 17v4"></path>
        <path d="M3 5h4"></path>
        <path d="M17 19h4"></path>
      </svg>`;
    default:
      return `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="12" y1="8" x2="12" y2="12"></line>
        <line x1="12" y1="16" x2="12.01" y2="16"></line>
      </svg>`;
  }
}
