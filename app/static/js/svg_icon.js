// Builds an inline <svg><use></svg> pointing at the icon sprite, for the few
// places JS has to create an icon itself (toasts, live status updates)
// instead of Jinja's icon() macro.
const SVG_NS = "http://www.w3.org/2000/svg";
const XLINK_NS = "http://www.w3.org/1999/xlink";
const SPRITE_PATH = "/static/icons/sprite.svg";

export function buildIcon(name) {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("class", "icon");
  svg.setAttribute("aria-hidden", "true");
  const use = document.createElementNS(SVG_NS, "use");
  use.setAttributeNS(XLINK_NS, "href", `${SPRITE_PATH}#icon-${name}`);
  use.setAttribute("href", `${SPRITE_PATH}#icon-${name}`);
  svg.appendChild(use);
  return svg;
}
