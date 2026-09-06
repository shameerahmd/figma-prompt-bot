/**
 * Figma AI Prompt Optimizer - Frontend Presets & Sample Data
 */

const PRESETS = {
  devices: [
    { id: 'desktop', name: 'Desktop', res: '1440px', frame: 'Desktop 1440px' },
    { id: 'mobile', name: 'Mobile', res: '375px', frame: 'Mobile iOS 375px' },
    { id: 'tablet', name: 'Tablet', res: '834px', frame: 'Tablet iPad 834px' },
    { id: 'watch', name: 'Watch', res: '390px', frame: 'AppleWatch 390px' }
  ],
  styles: [
    { id: 'saas_modern', name: 'SaaS Modern', theme: 'Slate #0F172A, Accent #6366F1' },
    { id: 'minimal_dark', name: 'Minimal Dark', theme: 'OLED #09090B, Accent #22C55E' },
    { id: 'clean_light', name: 'Clean Light', theme: 'Light #FFFFFF, Accent #2563EB' },
    { id: 'glassmorphism', name: 'Glassmorphism', theme: 'Frosted Glass, Neon #06B6D4' },
    { id: 'neo_brutalist', name: 'Neo-Brutalist', theme: 'High-Saturation, Bold Borders' }
  ],
  samplePrompts: {
    crypto: "Modern crypto analytics dashboard with portfolio chart, 24h gainers table, and quick send/swap action bar",
    food: "Mobile food delivery restaurant page with categories scroll, food cards with photo & price, and sticky bottom cart summary",
    auth: "SaaS authentication modal with social logins, email/password inputs, remember me checkbox, and forgot password link",
    product: "E-commerce product detail page with image carousel, size/color variant chips, customer rating stars, and buy button"
  }
};
