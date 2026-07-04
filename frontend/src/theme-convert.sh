#!/bin/bash
# Convert dark theme to Apple-style white/black light theme
FILE="frontend/src/index.css"

# ── 1. Root Variables ──────────────────────────────────────────────────────
# Backgrounds: dark → white/light
sed -i '' "s/--bg-primary: #080808;/--bg-primary: #ffffff;/" "$FILE"
sed -i '' "s/--bg-secondary: #111111;/--bg-secondary: #f5f5f7;/" "$FILE"
sed -i '' "s/--bg-card: rgba(16, 16, 16, 0.80);/--bg-card: rgba(255, 255, 255, 0.85);/" "$FILE"

# Borders: white-alpha → black-alpha
sed -i '' "s/--border-color: rgba(255, 255, 255, 0.07);/--border-color: rgba(0, 0, 0, 0.08);/" "$FILE"
sed -i '' "s/--border-hover: rgba(255, 255, 255, 0.18);/--border-hover: rgba(0, 0, 0, 0.15);/" "$FILE"

# Text: light → dark
sed -i '' "s/--text-primary: #f0f0f0;/--text-primary: #1d1d1f;/" "$FILE"
sed -i '' "s/--text-secondary: #888888;/--text-secondary: #6e6e73;/" "$FILE"
sed -i '' "s/--text-muted: #555555;/--text-muted: #86868b;/" "$FILE"

# Accents: tune for light mode readability
sed -i '' "s/--accent-purple: #a3a3a3;/--accent-purple: #86868b;/" "$FILE"
sed -i '' "s/--accent-cyan: #d4d4d4;/--accent-cyan: #424245;/" "$FILE"
sed -i '' "s/--accent-emerald: #4ade80;/--accent-emerald: #34c759;/" "$FILE"
sed -i '' "s/--accent-rose: #f87171;/--accent-rose: #ff3b30;/" "$FILE"
sed -i '' "s/--accent-amber: #fbbf24;/--accent-amber: #ff9500;/" "$FILE"

# Color scheme
sed -i '' "s/color-scheme: dark;/color-scheme: light;/" "$FILE"

# ── 2. Title gradient ─────────────────────────────────────────────────────
sed -i '' "s/background: linear-gradient(135deg, #ffffff 0%, #d0d0d0 100%);/background: linear-gradient(135deg, #1d1d1f 0%, #424245 100%);/" "$FILE"

# ── 3. Glassmorphism → light glass ────────────────────────────────────────
sed -i '' "s/box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.6);/box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.06);/" "$FILE"
sed -i '' "s/box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.4);/box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.08);/" "$FILE"

# ── 4. Scrollbar ──────────────────────────────────────────────────────────
sed -i '' "s/background: #222222;/background: #d1d1d6;/g" "$FILE"
sed -i '' "s/background: #444444;/background: #aeaeb2;/" "$FILE"

# ── 5. Success banner: dark green tint → light green tint ─────────────────
sed -i '' "s/background: rgba(74, 222, 128, 0.06);/background: rgba(52, 199, 89, 0.08);/" "$FILE"
sed -i '' "s/border: 1px solid rgba(74, 222, 128, 0.2);/border: 1px solid rgba(52, 199, 89, 0.25);/" "$FILE"
sed -i '' "s/color: #86efac;/color: #248a3d;/g" "$FILE"

# ── 6. Badge colors for light mode ────────────────────────────────────────
sed -i '' "s/color: #fca5a5;/color: #d70015;/g" "$FILE"
sed -i '' "s/color: #fcd34d;/color: #b25000;/g" "$FILE"
sed -i '' "s/color: #d4d4d4;/color: #424245;/g" "$FILE"
sed -i '' "s/color: #c0c0c0;/color: #636366;/g" "$FILE"

# ── 7. All rgba(255,255,255,X) → rgba(0,0,0,X) for borders/bgs ──────────
# These are transparent-white overlays used in dark mode → convert to transparent-black overlays
sed -i '' "s/rgba(255, 255, 255, 0.005)/rgba(0, 0, 0, 0.01)/g" "$FILE"
sed -i '' "s/rgba(255, 255, 255, 0.01)/rgba(0, 0, 0, 0.02)/g" "$FILE"
sed -i '' "s/rgba(255, 255, 255, 0.02)/rgba(0, 0, 0, 0.03)/g" "$FILE"
sed -i '' "s/rgba(255, 255, 255, 0.04)/rgba(0, 0, 0, 0.04)/g" "$FILE"
sed -i '' "s/rgba(255, 255, 255, 0.05)/rgba(0, 0, 0, 0.05)/g" "$FILE"
sed -i '' "s/rgba(255, 255, 255, 0.06)/rgba(0, 0, 0, 0.06)/g" "$FILE"
sed -i '' "s/rgba(255, 255, 255, 0.07)/rgba(0, 0, 0, 0.07)/g" "$FILE"
sed -i '' "s/rgba(255, 255, 255, 0.08)/rgba(0, 0, 0, 0.08)/g" "$FILE"
sed -i '' "s/rgba(255, 255, 255, 0.09)/rgba(0, 0, 0, 0.09)/g" "$FILE"
sed -i '' "s/rgba(255, 255, 255, 0.1)/rgba(0, 0, 0, 0.1)/g" "$FILE"
sed -i '' "s/rgba(255, 255, 255, 0.12)/rgba(0, 0, 0, 0.1)/g" "$FILE"
sed -i '' "s/rgba(255, 255, 255, 0.15)/rgba(0, 0, 0, 0.12)/g" "$FILE"
sed -i '' "s/rgba(255, 255, 255, 0.18)/rgba(0, 0, 0, 0.15)/g" "$FILE"
sed -i '' "s/rgba(255, 255, 255, 0.2)/rgba(0, 0, 0, 0.12)/g" "$FILE"
sed -i '' "s/rgba(255, 255, 255, 0.25)/rgba(0, 0, 0, 0.15)/g" "$FILE"
sed -i '' "s/rgba(255, 255, 255, 0.3)/rgba(0, 0, 0, 0.15)/g" "$FILE"
sed -i '' "s/rgba(255, 255, 255, 0.35)/rgba(0, 0, 0, 0.2)/g" "$FILE"
sed -i '' "s/rgba(255, 255, 255, 0.6)/rgba(0, 0, 0, 0.5)/g" "$FILE"

# ── 8. Remaining rgba(0,0,0,X) dark overlays → lighter ───────────────────
sed -i '' "s/background: rgba(0, 0, 0, 0.2);/background: rgba(0, 0, 0, 0.03);/g" "$FILE"
sed -i '' "s/background-color: rgba(0, 0, 0, 0.2);/background-color: rgba(0, 0, 0, 0.03);/g" "$FILE"
sed -i '' "s/background: rgba(0, 0, 0, 0.3);/background: rgba(0, 0, 0, 0.04);/g" "$FILE"
sed -i '' "s/background: rgba(0, 0, 0, 0.6);/background: rgba(0, 0, 0, 0.4);/g" "$FILE"

# ── 9. Hardcoded dark backgrounds ─────────────────────────────────────────
sed -i '' "s/background: #0d0d0d;/background: #f5f5f7;/g" "$FILE"
sed -i '' "s/background: #111111;/background: #f5f5f7;/g" "$FILE"
sed -i '' "s/background-color: rgba(8, 8, 8, 0.92);/background-color: rgba(255, 255, 255, 0.92);/g" "$FILE"

# ── 10. Hardcoded white text → dark text ──────────────────────────────────
sed -i '' "s/color: #fff;/color: #1d1d1f;/g" "$FILE"
sed -i '' "s/color: #f0f0f0;/color: #1d1d1f;/g" "$FILE"
sed -i '' "s/color: #000000;/color: #ffffff;/g" "$FILE"

# ── 11. Primary button: white-on-black → black-on-white ──────────────────
sed -i '' "s/background: #ffffff;/background: #1d1d1f;/" "$FILE"
sed -i '' "s/background: #e5e5e5;/background: #333336;/" "$FILE"
sed -i '' "s/box-shadow: 0 0 20px rgba(0, 0, 0, 0.1);/box-shadow: 0 0 20px rgba(0, 0, 0, 0.15);/" "$FILE"

# ── 12. Success/danger btn hover states ───────────────────────────────────
sed -i '' "s/color: #052e16;/color: #ffffff;/g" "$FILE"
sed -i '' "s/color: #450a0a;/color: #ffffff;/" "$FILE"
sed -i '' "s/color: #451a03;/color: #ffffff;/" "$FILE"
sed -i '' "s/background: #4ade80;/background: #34c759;/g" "$FILE"
sed -i '' "s/background: #f87171;/background: #ff3b30;/" "$FILE"
sed -i '' "s/background: #fbbf24;/background: #ff9500;/" "$FILE"

# ── 13. Feedback textarea / edit inputs ───────────────────────────────────
# Already handled #0d0d0d → #f5f5f7 above, now fix color
# The "color: #fff" in .feedback-textarea and .edit-input are already converted

# ── 14. Spinner ───────────────────────────────────────────────────────────
# Already handled by rgba(255,255,255,0.06) and rgba(255,255,255,0.6) rules

# ── 15. Domain select ────────────────────────────────────────────────────
# Already handled #111111 → #f5f5f7 and #fff → #1d1d1f above

# ── 16. Box shadows with rgba(0,0,0,...) ──────────────────────────────────
sed -i '' "s/box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.4);/box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.08);/g" "$FILE"
sed -i '' "s/box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);/box-shadow: 0 10px 40px rgba(0, 0, 0, 0.12);/g" "$FILE"
sed -i '' "s/box-shadow: -1px 0 12px rgba(0, 0, 0, 0.3);/box-shadow: -1px 0 12px rgba(0, 0, 0, 0.06);/g" "$FILE"

# ── 17. Emerald color adjustments for light mode readability ──────────────
sed -i '' "s/background: rgba(74, 222, 128, 0.08);/background: rgba(52, 199, 89, 0.08);/g" "$FILE"
sed -i '' "s/border: 1px solid rgba(74, 222, 128, 0.25);/border: 1px solid rgba(52, 199, 89, 0.3);/g" "$FILE"
sed -i '' "s/border: 1px solid rgba(74, 222, 128, 0.2);/border: 1px solid rgba(52, 199, 89, 0.25);/g" "$FILE"
sed -i '' "s/background: rgba(74, 222, 128, 0.1);/background: rgba(52, 199, 89, 0.1);/g" "$FILE"
sed -i '' "s/background: rgba(74, 222, 128, 0.05);/background: rgba(52, 199, 89, 0.06);/g" "$FILE"
sed -i '' "s/border-color: rgba(74, 222, 128, 0.25);/border-color: rgba(52, 199, 89, 0.3);/g" "$FILE"

# ── 18. Rose/red for light mode ──────────────────────────────────────────
sed -i '' "s/background: rgba(248, 113, 113, 0.1);/background: rgba(255, 59, 48, 0.08);/g" "$FILE"
sed -i '' "s/border-color: rgba(248, 113, 113, 0.3);/border-color: rgba(255, 59, 48, 0.25);/g" "$FILE"
sed -i '' "s/background: rgba(248, 113, 113, 0.08);/background: rgba(255, 59, 48, 0.06);/g" "$FILE"
sed -i '' "s/border: 1px solid rgba(248, 113, 113, 0.25);/border: 1px solid rgba(255, 59, 48, 0.2);/g" "$FILE"
sed -i '' "s/border: 1px solid rgba(248, 113, 113, 0.3);/border: 1px solid rgba(255, 59, 48, 0.25);/g" "$FILE"

# ── 19. Amber/warning for light mode ─────────────────────────────────────
sed -i '' "s/background: rgba(251, 191, 36, 0.08);/background: rgba(255, 149, 0, 0.08);/g" "$FILE"
sed -i '' "s/border: 1px solid rgba(251, 191, 36, 0.25);/border: 1px solid rgba(255, 149, 0, 0.2);/g" "$FILE"
sed -i '' "s/border-color: rgba(251, 191, 36, 0.25);/border-color: rgba(255, 149, 0, 0.2);/g" "$FILE"
sed -i '' "s/background: rgba(251, 191, 36, 0.04);/background: rgba(255, 149, 0, 0.06);/g" "$FILE"
sed -i '' "s/border: 1px solid rgba(251, 191, 36, 0.15);/border: 1px solid rgba(255, 149, 0, 0.15);/g" "$FILE"
sed -i '' "s/border-color: rgba(251, 191, 36, 0.45);/border-color: rgba(255, 149, 0, 0.4);/g" "$FILE"

echo "✅ Theme conversion complete!"
