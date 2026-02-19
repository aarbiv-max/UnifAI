/**
 * Color utility functions for generating harmonious color palettes
 * based on a primary color.
 */

export interface HSL {
  h: number;
  s: number;
  l: number;
}

/**
 * Convert hex color to HSL
 */
export function hexToHsl(hex: string): HSL {
  const sanitized = hex.replace("#", "");
  const r = parseInt(sanitized.substring(0, 2), 16) / 255;
  const g = parseInt(sanitized.substring(2, 4), 16) / 255;
  const b = parseInt(sanitized.substring(4, 6), 16) / 255;

  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  let h = 0;
  let s = 0;
  const l = (max + min) / 2;

  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max - min);
    switch (max) {
      case r:
        h = (g - b) / d + (g < b ? 6 : 0);
        break;
      case g:
        h = (b - r) / d + 2;
        break;
      case b:
        h = (r - g) / d + 4;
        break;
    }
    h /= 6;
  }

  return {
    h: Math.round(h * 360),
    s: Math.round(s * 100),
    l: Math.round(l * 100)
  };
}

/**
 * Convert HSL to hex color
 */
export function hslToHex(h: number, s: number, l: number): string {
  l /= 100;
  const a = (s * Math.min(l, 1 - l)) / 100;
  const f = (n: number) => {
    const k = (n + h / 30) % 12;
    const color = l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
    return Math.round(255 * color)
      .toString(16)
      .padStart(2, '0');
  };
  return `#${f(0)}${f(8)}${f(4)}`;
}

/**
 * Generate a harmonious color palette based on a primary color
 * @param primaryHex - The primary color in hex format
 * @param count - Number of colors to generate (including the primary)
 * @returns Array of hex colors
 */
export function generateColorPalette(primaryHex: string, count: number): string[] {
  const primaryHsl = hexToHsl(primaryHex);
  const colors: string[] = [primaryHex]; // First color is always the primary
  
  // Generate variations by adjusting hue, saturation, and lightness
  // Use different strategies for each color to ensure variety
  const variations = [
    { h: 30, s: -10, l: 10 },   // Warmer, lighter
    { h: -30, s: 5, l: -5 },     // Cooler, darker
    { h: 60, s: -15, l: 15 },    // Shifted hue, lighter, less saturated
    { h: -60, s: 10, l: -10 },   // Shifted hue, darker, more saturated
    { h: 90, s: -20, l: 20 },    // Further shifted, much lighter
    { h: -90, s: 15, l: -15 },   // Further shifted, much darker
    { h: 120, s: -25, l: 25 },   // Complementary direction, very light
  ];

  for (let i = 0; i < count - 1 && i < variations.length; i++) {
    const variation = variations[i];
    let newH = (primaryHsl.h + variation.h + 360) % 360;
    let newS = Math.max(20, Math.min(100, primaryHsl.s + variation.s));
    let newL = Math.max(30, Math.min(85, primaryHsl.l + variation.l));
    
    colors.push(hslToHex(newH, newS, newL));
  }

  return colors;
}

/**
 * Get a color from the palette by index, cycling if needed
 * @param primaryHex - The primary color
 * @param index - Index of the color to get (0 = primary)
 * @param totalColors - Total number of colors needed
 * @returns Hex color string
 */
export function getPaletteColor(primaryHex: string, index: number, totalColors: number = 6): string {
  const palette = generateColorPalette(primaryHex, totalColors);
  return palette[index % palette.length];
}

// ---------------------------------------------------------------------------
// Derived theme colors – single source of truth for all theme-aware components
// ---------------------------------------------------------------------------

export interface DerivedThemeColors {
  primary: string;
  primaryLight: string;
  primaryDark: string;
  conditionAccent: string;
  conditionEdge: string;
  conditionCardBg: string;
  conditionCardBorder: string;
  hoverBorder: string;
  conditionDragOverBg: string;
}

/**
 * Derive a full set of theme-cohesive colors from a single primary hex.
 * Every component that needs theme-aware colors should use this function
 * instead of doing inline hsl transforms.
 */
/** Validate that a string is a well-formed 3- or 6-char hex colour. */
function isValidHex(value: string): boolean {
  return /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(value);
}

/** Expand short-hand 3-char hex (#abc) to full 6-char (#aabbcc). */
function expandHex(hex: string): string {
  if (hex.length === 4) {
    // #abc → #aabbcc
    return `#${hex[1]}${hex[1]}${hex[2]}${hex[2]}${hex[3]}${hex[3]}`;
  }
  return hex;
}

export function deriveThemeColors(primaryHex: string | undefined): DerivedThemeColors {
  const DEFAULT_HEX = "#8A2BE2";

  // Sanitize: ensure it starts with '#' and is valid hex
  let hex = primaryHex?.startsWith("#") ? primaryHex : `#${primaryHex || "8A2BE2"}`;
  if (!isValidHex(hex)) {
    hex = DEFAULT_HEX;
  }
  hex = expandHex(hex);

  let hsl = hexToHsl(hex);

  // Guard against NaN from malformed input slipping through
  if (Number.isNaN(hsl.h) || Number.isNaN(hsl.s) || Number.isNaN(hsl.l)) {
    hsl = hexToHsl(DEFAULT_HEX);
  }

  const condHue = (hsl.h + 30) % 360;

  const conditionAccent = hslToHex(condHue, Math.min(100, hsl.s), Math.max(30, hsl.l - 5));

  return {
    primary: hex,
    primaryLight: hslToHex(hsl.h, Math.min(100, hsl.s + 5), Math.min(70, hsl.l + 12)),
    primaryDark: hslToHex(hsl.h, Math.min(100, hsl.s + 5), Math.max(20, hsl.l - 10)),
    conditionAccent,
    conditionEdge: hslToHex(condHue, Math.min(100, hsl.s), Math.min(60, hsl.l + 8)),
    conditionCardBg: hslToHex(condHue, Math.min(40, hsl.s), 15),
    conditionCardBorder: hslToHex(condHue, Math.min(50, hsl.s), 25),
    hoverBorder: hslToHex(hsl.h, Math.min(70, hsl.s), Math.min(60, hsl.l + 15)),
    conditionDragOverBg: `${conditionAccent}20`,
  };
}

