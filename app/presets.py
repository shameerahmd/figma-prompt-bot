"""
UI/UX Presets, Design Tokens, and Archetypes for Figma AI Prompt Optimizer.
"""

DEVICE_PRESETS = {
    "desktop": {
        "id": "desktop",
        "name": "Desktop (1440px)",
        "resolution": "1440x900",
        "frame_token": "Desktop 1440px",
        "default_for": ["dashboard", "saas", "admin", "landing_page"]
    },
    "mobile": {
        "id": "mobile",
        "name": "Mobile (375px)",
        "resolution": "375x812",
        "frame_token": "Mobile iOS 375px",
        "default_for": ["consumer", "social", "e_commerce_mobile", "food_delivery", "fintech_mobile"]
    },
    "tablet": {
        "id": "tablet",
        "name": "Tablet (834px)",
        "resolution": "834x1194",
        "frame_token": "Tablet iPad 834px",
        "default_for": ["pos", "dashboard_tablet", "reader"]
    },
    "watch": {
        "id": "watch",
        "name": "Watch (390px)",
        "resolution": "390x450",
        "frame_token": "AppleWatch 45mm 390px",
        "default_for": ["fitness", "quick_glance", "iot"]
    }
}

STYLE_PRESETS = {
    "saas_modern": {
        "id": "saas_modern",
        "name": "SaaS Modern (Slate)",
        "theme_token": "Clean Slate #0F172A, Accent #6366F1, White Surface #FFFFFF",
        "radius": "8px",
        "typography": "Inter / Geist Sans",
        "contrast": "High"
    },
    "minimal_dark": {
        "id": "minimal_dark",
        "name": "Minimalist Dark",
        "theme_token": "Dark OLED #09090B, Surface #18181B, Accent #22C55E",
        "radius": "12px",
        "typography": "SF Pro / Inter",
        "contrast": "High"
    },
    "clean_light": {
        "id": "clean_light",
        "name": "Clean Light",
        "theme_token": "Pure Light #FAFAFA, Card #FFFFFF, Border #E4E4E7, Primary #2563EB",
        "radius": "10px",
        "typography": "Inter Regular/SemiBold",
        "contrast": "Crisp"
    },
    "glassmorphism": {
        "id": "glassmorphism",
        "name": "Glassmorphic Frosted",
        "theme_token": "Frosted Blur rgba(255,255,255,0.08), Gradient Backdrop, Neon Accent #06B6D4",
        "radius": "16px",
        "typography": "Plus Jakarta Sans",
        "contrast": "Luminous"
    },
    "neo_brutalist": {
        "id": "neo_brutalist",
        "name": "Neo-Brutalism",
        "theme_token": "High-Saturation Canary #FFE500, Pure Black 2px Borders, Shadow 4px hard",
        "radius": "0px",
        "typography": "Cabinet Grotesk / Archivo Bold",
        "contrast": "Maximum"
    }
}

ARCHETYPE_TEMPLATES = {
    "analytics_dashboard": {
        "name": "Analytics Dashboard",
        "category": "Data & SaaS",
        "default_components": ["SidebarNav", "HeaderSearchBar", "MetricCardsGrid(4)", "AreaLineChart", "DataTableWithPagination"]
    },
    "ecommerce_product": {
        "name": "E-Commerce Product Detail",
        "category": "Retail",
        "default_components": ["ProductGalleryCarousel", "BadgeTag", "PriceHeader", "ColorVariantSelector", "SizeChips", "StickyBottomCTA"]
    },
    "auth_modal": {
        "name": "Authentication & Onboarding",
        "category": "Auth",
        "default_components": ["BrandLogo", "OAuthButtonGroup(Google, GitHub)", "DividerText('or email')", "LabeledInput(Email)", "LabeledInput(Password)", "PrimaryButton('Sign In')", "FooterHelperLinks"]
    },
    "social_feed": {
        "name": "Social / Content Feed",
        "category": "Community",
        "default_components": ["TopStoriesCarousel", "PostCard(Avatar, Username, Timestamp, MediaBlock, ActionRow: Like/Comment/Share)", "FloatingActionButton"]
    },
    "pricing_table": {
        "name": "SaaS Pricing Tier Comparison",
        "category": "Marketing",
        "default_components": ["BillingToggle(Monthly/Annual -20%)", "3TierPricingCards(Free, Pro[Highlighted], Enterprise)", "FeatureChecklistMatrix", "FAQAccordion"]
    }
}

DESIGN_TOKENS_DEFAULTS = {
    "grid_system": "8px Auto-Layout base",
    "border_radius": "8px (Cards), 6px (Inputs/Buttons), 999px (Pills)",
    "elevation": "Subtle DropShadow 0 4px 6px -1px rgba(0,0,0,0.1)",
    "component_naming": "Atomic UI / Figma Component Nomenclature"
}
