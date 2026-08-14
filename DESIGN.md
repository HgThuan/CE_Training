---
name: Mercato Market Ledger Customer
description: A trustworthy Vietnamese multi-vendor storefront shaped like a clear, well-organized market ledger.
colors:
  mineral-paper: "#f7f3ea"
  clean-paper: "#fffdf8"
  bottle-green: "#173b35"
  bottle-green-deep: "#0b2a25"
  coral-action: "#e85d3f"
  coral-action-deep: "#c8452d"
  saffron-highlight: "#f2c14e"
  muted-ink: "#526762"
  market-rule: "rgb(23 59 53 / 14%)"
  soft-sage: "#e8eee9"
  image-placeholder: "#ece8de"
  coral-selection: "#fff0ea"
typography:
  display:
    fontFamily: "Young Serif, Georgia, serif"
    fontSize: "clamp(2.25rem, 3.5vw, 2.65rem)"
    fontWeight: 400
    lineHeight: 0.9
    letterSpacing: "-0.035em"
  headline:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "clamp(1.5rem, 3vw, 1.875rem)"
    fontWeight: 900
    lineHeight: 1.2
    letterSpacing: "-0.025em"
  body:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 700
    lineHeight: 1.25
rounded:
  sm: "8px"
  mobile-nav: "10.4px"
  control: "12px"
  panel: "16px"
  large-panel: "24px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "20px"
  2xl: "24px"
  3xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.coral-action}"
    textColor: "#ffffff"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "12px 20px"
    height: "44px"
  button-primary-hover:
    backgroundColor: "{colors.coral-action-deep}"
    textColor: "#ffffff"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
  search-field:
    backgroundColor: "{colors.clean-paper}"
    textColor: "{colors.bottle-green-deep}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    height: "44px"
  panel:
    backgroundColor: "{colors.clean-paper}"
    textColor: "{colors.bottle-green-deep}"
    rounded: "{rounded.panel}"
    padding: "20px"
  product-card:
    backgroundColor: "{colors.clean-paper}"
    textColor: "{colors.bottle-green-deep}"
    rounded: "{rounded.panel}"
    padding: "16px"
---

# Design System: Mercato Market Ledger Customer

## Overview

**Creative North Star: "The Organized Market Ledger"**

Mercato feels like a lively multi-category market made orderly: warm mineral paper, bottle-green structure, coral actions, saffron price markers, fine rules, and restrained receipt details. Product imagery and factual commerce data lead; the interface supplies confidence, hierarchy, and a clear path from discovery to checkout.

The system has two complementary modes. Home may persuade with one editorial, mixed-category composition and the Young Serif display voice. Catalog, product, cart, checkout, and account surfaces operate with a dense, direct sans-serif hierarchy. Neither mode becomes a generic purple-blue marketplace or a wall of identical floating cards.

This document governs the public storefront and authenticated Customer experience only. **Admin and Seller layouts, pages, workflows, and visual systems are explicitly outside its authority.** Applying these tokens through the Customer shell must not change routes, route names, API contracts, stores, composables, authorization, or business logic.

**Key Characteristics:**

- Warm paper surfaces with deep green structural anchors.
- Image-led merchandising supported by explicit price, shop, rating, stock, and offer data.
- Coral reserved for actions and commercial emphasis; saffron reserved for compact highlights.
- Ledger cues—fine rules, tickets, and restrained perforation—used as accents, not decoration everywhere.
- Full mobile commerce from 320px upward, with touch-safe controls and persistent primary navigation.

**The Customer Boundary Rule.** Never use this document as a mandate to restyle Admin or Seller UI.

**The Commerce-First Rule.** AI improves discovery and decisions but never obscures or blocks the core shopping path when its provider is unavailable.

## Colors

The palette combines trustworthy green structure with warm, tactile paper and sparing high-energy commerce accents. Frontmatter values are normative.

### Primary

- **Bottle Green:** Brand structure for the sticky header, category actions, strong text, icons, and trust cues.
- **Deep Bottle Green:** Primary body text and high-contrast dark commerce surfaces such as the checkout summary.
- **Coral Action:** Primary CTA, search submit, current commercial emphasis, and price emphasis.
- **Deep Coral Action:** Hover and active treatment for coral actions and important text links.

### Secondary

- **Saffron Highlight:** Ratings, countdown or price-label highlights, selected compact controls, and active accents on dark green. It is not a general surface color.

### Neutral

- **Mineral Paper:** Page canvas and quiet ticket backgrounds.
- **Clean Paper:** Cards, fields, menus, navigation, and raised panels.
- **Muted Ink:** Secondary copy and metadata that must remain readable.
- **Market Rule:** Dividers, rails, and structural outlines.
- **Soft Sage:** Selected/filter backgrounds and image-fallback fields.
- **Image Placeholder:** Neutral media well when product imagery is unavailable.
- **Coral Selection:** Mobile navigation selection paired with deep coral foreground.

Semantic success, warning, and error colors may remain distinct from the brand palette. Always pair them with text, an icon, or another non-color signal, and verify WCAG 2.2 AA contrast in context.

**The Rare Accent Rule.** Coral and saffron communicate action, price, selection, or urgency; do not wash whole pages in them.

**The Paper Rule.** Customer surfaces are warm paper, not cold gray-white. Use soft sage or tonal layering before introducing an unrelated neutral.

## Typography

**Display Font:** Young Serif, with Georgia and serif fallbacks.

**Body Font:** Inter when available, followed by the implemented native sans-serif stack.

**Character:** Young Serif gives Mercato a recognizable editorial market voice. The workhorse sans remains compact, direct, and highly scannable for all transactional information.

### Hierarchy

- **Display:** Regular, tightly tracked, compact leading. Use only for the Mercato wordmark and the primary Home editorial headline.
- **Headline:** Heavy sans-serif at a responsive 24–30px scale. Use for section and page headings where scan speed matters.
- **Title:** Bold or extra-bold sans-serif, typically 16–20px. Use for product names, panels, checkout steps, and grouped tasks.
- **Body:** Regular sans-serif at 16px with 1.5 line height. Use for explanations, instructions, and longer content; keep reading lines near 65–75 characters where layouts permit.
- **Label:** Bold sans-serif at 12–14px. Use for controls, metadata, shop names, navigation, and compact commerce facts. Uppercase with wide tracking is reserved for short eyebrows or status labels.
- **Price:** Extra-bold sans-serif with tabular-friendly alignment. Current price leads; supporting prices and ranges remain subordinate.

**The Two-Voice Rule.** Serif creates recognition on the wordmark and Home hero only; forms, tables, prices, product names, and operational pages stay sans-serif.

**The Data Legibility Rule.** Never trade price, quantity, delivery, voucher, stock, or order readability for display styling.

## Layout

Customer pages sit in a centered container capped at 80rem for the header and typically 72–80rem for page content, with 16px mobile gutters and 24px gutters from small screens upward. Use the implemented 4/8px rhythm and the frontmatter spacing scale; sections generally breathe at 24–32px while related control groups stay at 8–16px.

Desktop uses a two-tier sticky header: wordmark, wide search/AI field, and utilities above; shopping navigation and a factual promise below. Home opens with a wide curated-market hero, then a receipt-like Flash Sale band, horizontal category routes, and an image-led grid. Operational pages use clear page headings, bounded panels, and predictable form grouping. Checkout uses a fluid task column plus a 360px sticky receipt summary at large widths.

Product grids adapt to available space: two columns from small screens, three at large widths, and four on wide Home layouts. Catalog may reserve a 260px desktop filter column; the filter becomes an off-canvas sheet on smaller screens. Horizontal category or trust rails may scroll rather than shrink content below legibility.

At 900px and below, the header search moves to a full second row, the desktop rail disappears, and the menu becomes explicit. At 640px and below, nonessential header utilities collapse, a five-item bottom navigation appears, safe-area insets are honored, and the shell reserves 4.75rem of bottom space. The Home hero becomes 32rem tall with a readable paper gradient over imagery; category overlays and secondary hero bullets may hide. The interface must remain complete at 320px—never solve mobile by deleting checkout, account, search, cart, or order capability.

**The Full Mobile Rule.** Mobile is a complete shopping experience, not a compressed or functionally reduced desktop page.

**The One Primary Grid Rule.** A section uses one clear merchandising grid; avoid nested card grids and competing horizontal scrollers in the same viewport.

## Elevation & Depth

Depth is a hybrid of paper tonality, fine green rules, and soft green-tinted shadows. Cards sit lightly above the mineral canvas (`0 10px 30px rgb(23 59 53 / 8%)`); trust and category surfaces use quieter ambient depth (`0 8px 24px rgb(23 59 53 / 7%)`); the hero and dark checkout summary use stronger emphasis (`0 16px 40px rgb(23 59 53 / 14–16%)`). Hover may add a small lift of 1–4px where the whole surface is interactive.

Receipt surfaces use dashed block edges at restrained opacity, not ornamental paper effects on every panel. Focus depth is functional: Customer form fields use a coral border plus a 3px translucent coral ring.

**The Flat-by-Default Rule.** Elevation establishes hierarchy or interaction; it is never a decorative glow around every object.

**The Green Shadow Rule.** Shadows derive from bottle green rather than neutral black so raised paper remains inside the Market Ledger world.

## Shapes

Controls and compact cards use gently curved 12px corners; major panels and product cards use 16px; 24px is reserved for larger legacy-compatible task containers and empty/loading states. Small badges use 8px corners. Circular or pill geometry is limited to icon-only controls, avatars, counts, and genuinely continuous chips—never as the default language for every button and container.

One-pixel translucent green rules organize dense information. Media is clipped inside its card silhouette. Receipt/perforation cues appear only on sale, totals, or other ledger-like summaries and remain subtle.

**The No Pill Sprawl Rule.** Rounded-full is for compact semantic objects, not navigation bars, fields, cards, or ordinary CTAs.

## Components

### Customer Shell and Navigation

- **Header:** Sticky deep-green two-tier shell on desktop; compact header plus mobile menu at medium widths; bottom navigation at small widths.
- **Wordmark:** Young Serif on clean paper white, always linking to Home with an accessible name.
- **Icons:** Heroicons 24px outline family; use a consistent 20px rendered size for routine utilities.
- **States:** Hover and active states use saffron or a restrained translucent-paper field. Route-active styling must remain visible without relying on color alone when context is ambiguous.
- **Touch:** Primary links and icon controls are at least 44×44px; mobile bottom-nav destinations are at least 56px tall.

### Search and AI Discovery

- **Field:** Clean-paper 44px field with a 12px radius, leading search icon, explicit clear control, and coral submit action.
- **Suggestions:** A bounded raised listbox with visible loading, error, empty, hover, keyboard-active, and selected states. Preserve combobox/listbox semantics and arrow, Enter, and Escape behavior.
- **AI:** AI search is a compact enhancement beside ordinary search. Its state is explicit; failure must leave keyword search and catalog navigation usable.

### Buttons and Actions

- **Primary:** Coral, white text, heavy sans label, 12px corners, and at least 44px height. Hover deepens to deep coral and may lift 1px.
- **Dark/Category:** Bottle green with white text for category routes and selected structural actions.
- **Secondary/Ghost:** Clean paper or transparent with a visible green/rule boundary and strong ink text.
- **Icon-only:** 44×44px minimum with an accessible name; selected, busy, disabled, and pressed states are programmatic as well as visual.
- **Focus/Disabled:** Use a clear coral focus indicator. Disabled controls reduce emphasis but retain legible labels and expose the reason nearby or through explanatory text when necessary.

### Product Cards

- **Structure:** Image first in a 4:3 media well, followed by shop, two-line product name, rating count, current price, and only relevant supporting price information.
- **Surface:** Clean paper, 16px corners, soft green-tinted ambient shadow, and 16px content padding.
- **Media:** Real API image with meaningful product alt text. On failure, show the structured Mercato fallback and an honest “Ảnh đang cập nhật” label.
- **Actions:** Wishlist and compare are separate 44px overlay controls with pressed, disabled, busy, and accessible-label states. Product navigation remains a proper link.
- **Motion:** Hover image zoom is restrained to roughly 1.03 and about 500ms; disable nonessential motion under reduced-motion preferences.

### Prices, Promotions, and Receipt Patterns

- **Current price:** Extra-bold coral and visually dominant.
- **Original price:** Muted and struck through only when its numeric value is greater than the sale price.
- **Ranges:** Say “Giá từ … đến …” only when the maximum exceeds the minimum.
- **Flash Sale:** Paper ticket with dashed block rules, truthful countdown, quota/sold data, and coral add-to-cart action. Never infer a discount label or urgency claim.
- **Checkout receipt:** Deep-green sticky summary with saffron for a real discount, explicit subtotal/shipping/discount/total rows, loading feedback, and a full-width coral submit action.

### Panels, Forms, and States

- **Panels:** Clean paper with 16px corners and soft depth; use 24px corners only for large, established operational groups.
- **Fields:** 12px corners, visible boundary, descriptive labels, and coral focus ring. Autofill retains deep-green text on clean paper.
- **State inventory:** Loading, empty, error, success, disabled, missing image, long content, and AI-unavailable are first-class states. Skeletons preserve the eventual layout; empty states explain the next useful action.
- **Dialogs and sheets:** Trap and restore focus, close with Escape where appropriate, expose names/roles, and keep destructive choices explicit.

## Do's and Don'ts

### Do:

- **Do** apply this system consistently across public storefront, catalog, product, cart, checkout, wishlist, notifications, chat, after-sales, and Customer account surfaces.
- **Do** format money in VND and dates according to Vietnamese conventions; keep UI and core content in clear Vietnamese.
- **Do** render values from API/store truth for price, stock, rating, sold count, promotion, delivery, voucher scope, and totals.
- **Do** keep genuine product and banner imagery image-led, with honest, structured fallbacks when assets fail or are missing.
- **Do** target WCAG 2.2 AA, preserve semantic HTML and accessible names, support keyboard and touch, maintain 44×44px important targets, and honor `prefers-reduced-motion`.
- **Do** explain unavailable purchase actions and pair state color with text, iconography, pattern, or programmatic state.
- **Do** preserve every existing route, route name, API, store, composable, permission boundary, and business rule while extending Customer UI.

### Don't:

- **Don't** apply Market Ledger tokens or component rules to Admin or Seller UI unless a separate, explicit design decision expands scope.
- **Don't** invent prices, discounts, ratings, sales counts, stock, merchant claims, delivery promises, policies, reviews, social proof, or AI conclusions.
- **Don't** strike an original price unless it is numerically greater than the selling price, or show a range unless the maximum is greater than the minimum.
- **Don't** let AI errors block ordinary search, catalog browsing, cart, checkout, account, or after-sales tasks.
- **Don't** return to a generic purple-blue marketplace identity, cold gray canvas, indiscriminate pills, or uniform card walls that erase category and information hierarchy.
- **Don't** rely on route guards as authorization; backend enforcement remains the source of permission truth.
