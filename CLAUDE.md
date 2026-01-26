# CLAUDE.md

This file provides guidance to Claude Code when working with the Launch Sitebot project.

## Project Overview

**Launch Sitebot** - Brand assets and web development resources for Launch Family Entertainment.

This repository contains:
- Official brand guidelines and specifications
- Logo and icon assets (PNG, EPS, PDF)
- Font files (Futura, Stilu)
- Machine-readable brand configuration
- Photography assets

## Brand Identity Quick Reference

### Company

| Property | Value |
|----------|-------|
| **Name** | Launch Family Entertainment |
| **Abbreviation** | LFE |
| **Catch Phrase** | "Have An Awesome Time" |
| **Vision** | "To Create Awesome Memories" |
| **Slogan** | "Where Memories Are Created" |
| **Mascot** | Joey the Kangaroo |

### Primary Colors

| Color | HEX | RGB |
|-------|-----|-----|
| Launch Green | `#5CBA47` | rgb(92, 186, 71) |
| Launch Yellow | `#F4E501` | rgb(244, 229, 1) |
| White | `#FFFFFF` | rgb(255, 255, 255) |
| Black | `#000000` | rgb(0, 0, 0) |

### Secondary Colors

| Color | HEX |
|-------|-----|
| Orange | `#FF9307` |
| Red | `#EF4036` |
| Pink | `#EA3D6F` |
| Purple | `#B035C8` |
| Blue | `#1E8FD7` |
| Dark Blue | `#493594` |

### Typography

- **Primary Font**: Futura Bold (headers, titles, buttons)
- **Secondary Font**: Futura Medium (body copy, paragraphs)
- **Fallback**: Futura PT Bold / Futura PT Book (Google Drive, Canva)

## Project Structure

```
launch_sitebot/
├── assets/
│   ├── fonts/          # Futura (.ttf, .ttc, .otf) and Stilu fonts
│   ├── graphics/       # EPS graphics (Events, Parties, Bar, Restaurant, Slogan)
│   ├── icons/          # Kangaroo icon (PNG, EPS, PDF)
│   ├── images/         # Photography (JPG)
│   └── logos/          # Launch, Krave, BarHops logos (PNG, EPS, PDF)
├── brand-guidelines/   # Original PDF brand guidelines (Full, Short, Compressed)
├── docs/
│   ├── LAUNCH_BRAND_GUIDELINES.md   # Complete machine-readable brand spec
│   └── launch_brand_config.json     # JSON config for programmatic use
├── CLAUDE.md           # This file
└── README.md           # Project documentation
```

## Logo Usage Rules

### Approved Background/Logo Combinations

| Background | Allowed Logo Colors |
|------------|---------------------|
| White | Black, Green, Yellow |
| Black | White, Green, Yellow |
| Green | Black, White, Yellow |
| Yellow | Black, Green, White |

### Single Color Approved

Logo can be single color in: White, Black, Launch Green, or Launch Yellow

### DO NOT

- Change logo colors to secondary colors or gradients
- Skew, stretch, or distort the logo
- Change the layout/arrangement
- Add strokes, shadows (unless subtle for readability), or effects
- Add seasonal themes or graphics behind logo
- Use old logo or old Joey silhouette
- Place over photos that make it difficult to read

## Available Assets

### Logos (assets/logos/)

| File | Description |
|------|-------------|
| `LaunchFE_Logo_2024_Black.png/eps` | Full color on white/light backgrounds |
| `LaunchFE_Logo_2024-White.png/eps` | Full color on black/dark backgrounds |
| `LaunchFE_Logo_2024-OneColorBlack.png/eps` | Single color black |
| `LaunchFE_Logo_2024-OneColorWhite.png/eps` | Single color white |
| `BarHops_logo_2024_Copy.png/eps` | Bar Hops sub-brand logo |
| `KraveLogo_FlatColor-01.eps` | Krave restaurant logo |

### Icons (assets/icons/)

| File | Description |
|------|-------------|
| `Kangaroo_Icon_2024.png/eps` | Joey kangaroo icon |
| `Icon_Socials.png` | Social media icon version |

### Fonts (assets/fonts/)

| File | Description |
|------|-------------|
| `Futura Bold.ttf` | Primary header font |
| `Futura.ttc` | Futura collection |
| `Futura Condensed Bold.otf` | Condensed variant |
| `Stilu-*.otf` | Secondary font family |

### Graphics (assets/graphics/)

| File | Description |
|------|-------------|
| `WhereMemoriesAreCreated copy-01.eps` | Slogan graphic |
| `Events.eps` | Events graphic |
| `Parties.eps` | Parties graphic |
| `Bar.eps` | Bar graphic |
| `Restaurant.eps` | Restaurant graphic |

## Development Guidelines

### Using Brand Config

```javascript
// Import JSON configuration
const brand = require('./docs/launch_brand_config.json');

// Access colors
const green = brand.colors.primary.launch_green.hex; // #5CBA47

// Access CSS variables
const cssVars = brand.css_variables;

// Use asset selection logic
const logo = brand.asset_selection.logo_selection.by_background.light.full_color;
// Returns: "assets/logos/LaunchFE_Logo_2024_Black.png"

// Get approved headlines for content generation
const headlines = brand.content_patterns.approved_headlines;

// Check brand voice guidelines
const tone = brand.content_patterns.brand_voice.tone;
// Returns: ["enthusiastic", "positive", "family-friendly", "welcoming", "energetic"]
```

### CSS Setup

```css
:root {
  /* Primary */
  --launch-green: #5CBA47;
  --launch-yellow: #F4E501;
  --launch-white: #FFFFFF;
  --launch-black: #000000;

  /* Secondary */
  --launch-orange: #FF9307;
  --launch-red: #EF4036;
  --launch-pink: #EA3D6F;
  --launch-purple: #B035C8;
  --launch-blue: #1E8FD7;
  --launch-dark-blue: #493594;

  /* Typography */
  --font-primary: 'Futura Bold', 'Futura PT Bold', sans-serif;
  --font-secondary: 'Futura Medium', 'Futura PT Book', sans-serif;
}
```

### Gradient Usage

Approved dual gradients (use sparingly):
- Green -> Yellow
- Purple -> Pink
- Yellow -> Orange
- Green -> Blue
- Orange -> Red
- Purple -> Blue

Full rainbow gradient order: Green -> Yellow -> Orange -> Red -> Pink -> Purple -> Blue

## Asset Selection Quick Reference

### Selecting Logos by Context

| Context | Use This File |
|---------|---------------|
| Light background (web) | `assets/logos/LaunchFE_Logo_2024_Black.png` |
| Light background (print) | `assets/logos/LaunchFE_Logo_2024_Black.eps` |
| Dark background (web) | `assets/logos/LaunchFE_Logo_2024-White.png` |
| Dark background (print) | `assets/logos/LaunchFE_Logo_2024-White.eps` |
| Single color on light | `assets/logos/LaunchFE_Logo_2024-OneColorBlack.png` |
| Single color on dark | `assets/logos/LaunchFE_Logo_2024-OneColorWhite.png` |

### Selecting Icons by Context

| Context | Use This File |
|---------|---------------|
| General use (web) | `assets/icons/Kangaroo_Icon_2024.png` |
| General use (print) | `assets/icons/Kangaroo_Icon_2024.eps` |
| Social media profiles | `assets/icons/Icon_Socials.png` |

### Content Generation

When generating brand content, use these approved patterns:

**Taglines:**
- "Have An Awesome Time" (catch phrase)
- "Where Memories Are Created" (slogan)
- "To Create Awesome Memories" (vision)

**Headlines:**
- Have An Awesome Time
- Where Memories Are Created
- Create Awesome Memories
- Family Fun For Everyone
- Jump Into Fun
- Entertainment For All Ages

**Call-to-Actions:**
- Book Your Party Today
- Plan Your Visit
- Join The Fun
- Reserve Your Spot
- Get Started

**Brand Voice:**
- Tone: Enthusiastic, positive, family-friendly, welcoming, energetic
- Avoid: Negative language, exclusionary terms, adult-only themes, unsafe imagery
