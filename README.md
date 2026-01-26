# Launch Sitebot

Brand assets and guidelines for Launch Family Entertainment web projects.

## Project Structure

```
launch_sitebot/
├── assets/
│   ├── fonts/          # Futura and Stilu font files
│   ├── graphics/       # EPS graphics (Events, Parties, Bar, Restaurant)
│   ├── icons/          # Kangaroo icon in various formats
│   ├── images/         # Photography assets
│   └── logos/          # Launch, Krave, and BarHops logos
├── brand-guidelines/   # Original PDF brand guidelines
├── docs/
│   ├── LAUNCH_BRAND_GUIDELINES.md   # Machine-readable brand spec
│   └── launch_brand_config.json     # Programmatic brand config
└── CLAUDE.md           # AI assistant instructions
```

## Quick Reference

### Brand Colors

| Color | HEX | Usage |
|-------|-----|-------|
| Launch Green | `#5CBA47` | Primary |
| Launch Yellow | `#F4E501` | Primary |
| White | `#FFFFFF` | Primary |
| Black | `#000000` | Primary |

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

- **Primary**: Futura Bold (headers, titles)
- **Secondary**: Futura Medium (body copy)
- **Fallback**: Futura PT Bold / Futura PT Book

### Brand Taglines

- **Catch Phrase**: "Have An Awesome Time"
- **Vision**: "To Create Awesome Memories"
- **Slogan**: "Where Memories Are Created"

## Logo Files

| File | Format | Usage |
|------|--------|-------|
| `LaunchFE_Logo_2024_Black.png` | PNG | Dark backgrounds |
| `LaunchFE_Logo_2024-White.png` | PNG | Light backgrounds |
| `LaunchFE_Logo_2024-OneColorBlack.png` | PNG | Single color, dark |
| `LaunchFE_Logo_2024-OneColorWhite.png` | PNG | Single color, light |
| `Kangaroo_Icon_2024.png` | PNG | Icon-only usage |

## Usage

### Import Brand Config in JavaScript

```javascript
import brandConfig from './docs/launch_brand_config.json';

const primaryGreen = brandConfig.colors.primary.launch_green.hex;
// #5CBA47
```

### CSS Variables

```css
:root {
  --launch-green: #5CBA47;
  --launch-yellow: #F4E501;
  --launch-white: #FFFFFF;
  --launch-black: #000000;
  --launch-orange: #FF9307;
  --launch-red: #EF4036;
  --launch-pink: #EA3D6F;
  --launch-purple: #B035C8;
  --launch-blue: #1E8FD7;
  --launch-dark-blue: #493594;
}
```

## Documentation

- [Full Brand Guidelines](docs/LAUNCH_BRAND_GUIDELINES.md) - Complete machine-readable specification
- [Brand Config JSON](docs/launch_brand_config.json) - Programmatic configuration

## External Resources

- [Branding Assets (Canto)](https://launchtrampolinepark.canto.com/b/JELNH)
- [Franchise Portal](https://sites.google.com/launchtrampolinepark.com/portal/home)
- [Marketing Submission Form](https://forms.monday.com/forms/7f957d0873068d80a947db4db9b7bade)
