import { initConfirmOrderDialog } from "./order_confirm_dialog.js";

const AREAS = {
  "DHA": [31.4697, 74.414],
  "Gulberg": [31.5204, 74.3587],
  "Johar Town": [31.4697, 74.2728],
  "Model Town": [31.4817, 74.3246],
  "Bahria Town": [31.3684, 74.186],
  "Township": [31.444, 74.283],
  "Iqbal Town": [31.4959, 74.2989],
  "Wapda Town": [31.428, 74.266],
  "Cantt": [31.53, 74.37],
  "Shahdara": [31.623, 74.289],
};

function formatPkr(amount) {
  const rounded = Math.round(amount * 100) / 100;
  const text = Number.isInteger(rounded)
    ? rounded.toLocaleString("en-US")
    : rounded.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return `PKR ${text}`;
}

function nearestArea(lat, lng) {
  let best = null;
  let bestDistance = Infinity;
  for (const [name, [areaLat, areaLng]] of Object.entries(AREAS)) {
    const distance = Math.hypot(lat - areaLat, lng - areaLng);
    if (distance < bestDistance) {
      bestDistance = distance;
      best = name;
    }
  }
  return best;
}

function selectedService(form) {
  const name = form.querySelector("[data-service-value]").value;
  const card = form.querySelector(`[data-service-card="${name}"]`);
  return { name, unitPrice: parseFloat(card.dataset.unitPrice) };
}

function slotLabel(form, value) {
  const chip = form.querySelector(`[data-slot-chip="${value}"]`);
  return chip ? chip.textContent : value;
}

function whenLabel(form) {
  const timing = form.querySelector("[data-timing-value]").value;
  if (timing === "now") return "Now";
  const slot = form.querySelector("[data-slot-value]").value;
  return slot ? `Today, ${slotLabel(form, slot)}` : "Pick a time";
}

function updateSummary(form) {
  const service = selectedService(form);
  const address = form.querySelector("#field-address").value.trim();
  const area = form.querySelector("#field-area").value;
  const vehicle = form.querySelector("[data-vehicle-type]").value;

  form.querySelector("[data-summary-service]").textContent = service.name;
  form.querySelector("[data-summary-vehicle]").textContent = vehicle;
  form.querySelector("[data-summary-when]").textContent = whenLabel(form);
  form.querySelector("[data-summary-price]").textContent = `${formatPkr(service.unitPrice)} / service`;
  form.querySelector("[data-summary-deliver]").textContent = address || area || "—";
  form.querySelector("[data-total-display]").textContent = formatPkr(service.unitPrice);
  form.querySelector("[data-price-snapshot]").value = service.unitPrice.toFixed(2);
}

function firstAvailableSlot(form) {
  const chip = form.querySelector('[data-slot-chip][data-slot-available="true"]');
  return chip ? chip.dataset.slotChip : "";
}

function applyCarWashRule(form) {
  const isCarWash = selectedService(form).name === "Car wash";
  const nowChip = form.querySelector('[data-timing-chip="now"]');
  const helper = form.querySelector("[data-now-helper]");
  nowChip.classList.toggle("chip--disabled", isCarWash);
  nowChip.disabled = isCarWash;
  helper.hidden = isCarWash;
  form.querySelectorAll("[data-slot-chip]").forEach((chip) => {
    const timeOk = chip.dataset.slotAvailable === "true";
    chip.classList.toggle("chip--disabled", !isCarWash ? false : !timeOk);
    chip.disabled = isCarWash && !timeOk;
  });
  if (isCarWash && form.querySelector("[data-timing-value]").value === "now") {
    setTiming(form, "scheduled");
  }
}

function setTiming(form, timing) {
  form.querySelector("[data-timing-value]").value = timing;
  form.querySelectorAll("[data-timing-chip]").forEach((chip) => {
    chip.classList.toggle("chip--selected", chip.dataset.timingChip === timing);
  });
  const schedule = form.querySelector("[data-assistance-schedule]");
  schedule.hidden = timing !== "scheduled";
  if (timing === "scheduled" && !form.querySelector("[data-slot-value]").value) {
    setSlot(form, firstAvailableSlot(form));
  }
  updateSummary(form);
}

function setSlot(form, value) {
  form.querySelector("[data-slot-value]").value = value;
  form.querySelectorAll("[data-slot-chip]").forEach((chip) => {
    chip.classList.toggle("chip--selected", chip.dataset.slotChip === value);
  });
  updateSummary(form);
}

function initTimingChips(form) {
  form.querySelectorAll("[data-timing-chip]").forEach((chip) => {
    chip.addEventListener("click", () => {
      if (chip.disabled) return;
      setTiming(form, chip.dataset.timingChip);
    });
  });
}

function initSlotChips(form) {
  form.querySelectorAll("[data-slot-chip]").forEach((chip) => {
    chip.addEventListener("click", () => {
      if (chip.disabled) return;
      setSlot(form, chip.dataset.slotChip);
    });
  });
}

function initVehicleChips(form) {
  const hidden = form.querySelector("[data-vehicle-type]");
  form.querySelectorAll("[data-vehicle-chip]").forEach((chip) => {
    chip.addEventListener("click", () => {
      hidden.value = chip.dataset.vehicleChip;
      form.querySelectorAll("[data-vehicle-chip]").forEach((other) => {
        other.classList.toggle("chip--selected", other === chip);
      });
      updateSummary(form);
    });
  });
}

function initServiceCards(form) {
  const hidden = form.querySelector("[data-service-value]");
  form.querySelectorAll("[data-service-card]").forEach((card) => {
    card.addEventListener("click", () => {
      hidden.value = card.dataset.serviceCard;
      form.querySelectorAll("[data-service-card]").forEach((other) => {
        other.classList.toggle("service-pick-card--selected", other === card);
      });
      applyCarWashRule(form);
      updateSummary(form);
    });
  });
}

function setLocationState(form, state, title, message) {
  const card = form.querySelector("[data-location-card]");
  card.dataset.state = state;
  card.classList.toggle("location-card--captured", state === "captured");
  card.classList.toggle("location-card--off", state !== "captured");
  form.querySelector("[data-location-title]").textContent = title;
  form.querySelector("[data-location-message]").textContent = message;
  form.querySelector("[data-location-action-label]").textContent =
    state === "captured" ? "Update" : "Try again";
  const icon = card.querySelector("[data-location-icon] use");
  if (icon) {
    const base = icon.getAttribute("href").split("#")[0];
    icon.setAttribute("href", `${base}#icon-${state === "captured" ? "check" : "location-crosshairs"}`);
  }
}

function requestLocation(form) {
  if (!navigator.geolocation) {
    setLocationState(form, "off", "Location is off", "Pick your area and type your address.");
    return;
  }
  navigator.geolocation.getCurrentPosition(
    (position) => {
      const { latitude, longitude, accuracy } = position.coords;
      form.querySelector("[data-latitude]").value = latitude;
      form.querySelector("[data-longitude]").value = longitude;
      const area = nearestArea(latitude, longitude);
      form.querySelector("#field-area").value = area;
      setLocationState(form, "captured", "Location captured", `Within ${Math.round(accuracy)} m · ${area}`);
      updateSummary(form);
    },
    () => {
      form.querySelector("[data-latitude]").value = "";
      form.querySelector("[data-longitude]").value = "";
      setLocationState(form, "off", "Location is off", "Pick your area and type your address.");
    },
    { enableHighAccuracy: true, timeout: 8000 },
  );
}

function initLocation(form) {
  requestLocation(form);
  form.querySelector("[data-location-action]").addEventListener("click", () => requestLocation(form));
}

export function validateAssistanceOrder(form) {
  const errors = {};
  if (!form.querySelector("#field-address").value.trim()) errors.address = true;
  const hasLocation = form.querySelector("[data-latitude]").value !== "";
  if (!hasLocation && !form.querySelector("#field-area").value) errors.area = true;
  const timing = form.querySelector("[data-timing-value]").value;
  if (timing === "scheduled" && !form.querySelector("[data-slot-value]").value) {
    errors.timing = true;
  }

  form.querySelectorAll("[data-error]").forEach((el) => {
    el.hidden = !errors[el.dataset.error];
  });

  const firstError = Object.keys(errors)[0];
  if (firstError === "address") form.querySelector("#field-address").focus();
  else if (firstError === "area") form.querySelector("#field-area").focus();

  return Object.keys(errors).length === 0;
}

function quantityTextForUnit(unitPrice, formatter) {
  return `1 × ${formatter(unitPrice)}`;
}

export function assistanceSummary(form) {
  const service = selectedService(form);
  const address = form.querySelector("#field-address").value.trim();
  const area = form.querySelector("#field-area").value;
  return {
    fuel_type: service.name,
    unitPrice: service.unitPrice,
    total: service.unitPrice,
    deliverTo: address || area,
    address,
    area,
    note: form.querySelector("#field-note").value.trim(),
    vehicleType: form.querySelector("[data-vehicle-type]").value,
    timing: form.querySelector("[data-timing-value]").value,
    slot: form.querySelector("[data-slot-value]").value,
    service: form.querySelector("[data-service-value]").value,
    latitude: form.querySelector("[data-latitude]").value || null,
    longitude: form.querySelector("[data-longitude]").value || null,
    orderKey: form.querySelector("[data-order-key]").value,
    priceSnapshot: form.querySelector("[data-price-snapshot]").value,
    csrfToken: form.querySelector("[data-csrf-token]").value,
    quantityTextForUnit,
  };
}

function buildRequestBody(summary) {
  return {
    service: summary.service,
    vehicle_type: summary.vehicleType,
    timing: summary.timing,
    slot: summary.slot,
    address: summary.address,
    area: summary.area,
    note: summary.note,
    latitude: summary.latitude,
    longitude: summary.longitude,
    order_key: summary.orderKey,
    price_snapshot: summary.priceSnapshot,
  };
}

export function initOrderAssistanceForm() {
  const form = document.querySelector("[data-order-assistance]");
  if (!form) return;

  initServiceCards(form);
  initVehicleChips(form);
  initTimingChips(form);
  initSlotChips(form);
  initLocation(form);
  applyCarWashRule(form);
  updateSummary(form);

  form.querySelector("#field-address").addEventListener("input", () => updateSummary(form));
  form.querySelector("#field-area").addEventListener("change", () => updateSummary(form));

  initConfirmOrderDialog(form, {
    validate: validateAssistanceOrder,
    summary: assistanceSummary,
    endpoint: "/app/order/assistance",
    formatPkr,
    buildRequestBody,
  });
}

initOrderAssistanceForm();
