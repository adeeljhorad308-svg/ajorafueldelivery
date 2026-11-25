// Fills the shared driver-card markup (components/driver_card.html) from an
// /api/orders/<id>/status JSON payload. Used by Order confirmed and Track order.
export function fillDriverCard(card, driver) {
  card.hidden = false;
  card.querySelector("[data-driver-initials]").textContent = driver.initials;
  card.querySelector("[data-driver-name]").textContent = driver.name;
  card.querySelector("[data-driver-meta] span").textContent =
    `${driver.rating_label} · ${driver.vehicle_no}`;
  card.querySelector("[data-driver-call]").href = `tel:${driver.phone}`;
  card.querySelector("[data-driver-distance]").textContent = driver.distance_label;
  card.querySelector("[data-driver-eta]").textContent = `about ${driver.eta_minutes} min`;
}
