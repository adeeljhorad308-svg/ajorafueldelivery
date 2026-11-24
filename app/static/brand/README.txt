AJORA logo kit
==============
Chosen logo: Idea A, "drop in a pin" (17 Nov 2026).
Source of truth: Figma file "AJORA – Design", page "00 · Logo & icons".

svg/  (text already outlined, so no font is needed)
  ajora-logo-horizontal-positive.svg    Default, on White / Canvas / Mint
  ajora-logo-horizontal-reversed.svg    On Obsidian or dark photos
  ajora-logo-horizontal-on-emerald.svg  All white, on Emerald
  ajora-logo-horizontal-one-colour.svg  Single ink (stamps, receipts)
  ajora-mark.svg / -white / -obsidian   Mark alone (min 16 px)
  ajora-app-icon.svg                    Emerald square + white mark
  favicon.svg                           Browser tab icon

png/
  ajora-logo-horizontal-*@2x.png        325 x 80 px
  ajora-mark*-256.png
  app-icon-512.png, app-icon-192.png    Android / web app manifest
  apple-touch-icon.png                  180 x 180, iPhone home screen
  favicon-16/32/48.png

favicon.ico                             16 + 32 + 48 in one file

Colours: Emerald #0F9F6E, Obsidian #0B0D0C, White #FFFFFF.
Clear space: half the mark height on every side.
Minimum size: horizontal logo 96 px wide, mark 16 px.
Do not stretch, recolour, add gradients or shadows, or crowd the logo.

Where these go in the code (session C1):
  app/static/brand/   all files from svg/ and png/
  app/static/favicon.ico
