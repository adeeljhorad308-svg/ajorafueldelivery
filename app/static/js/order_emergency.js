import { initConfirmOrderDialog } from "./order_confirm_dialog.js";

// Mirrors app/areas.py: used only to guess a human place name from raw
// coordinates (no geocoding service).
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

function selectedFuel(form) {
  const input = form.querySelector('input[name="fuel_type"]:checked');
  return { name: input.value, unitPrice: parseFloat(input.dataset.unitPrice) };
}

function setAll(form, selector, text) {
  form.querySelectorAll(selector).forEach((el) => {
    el.textContent = text;
  });
}

function updateSummary(form) {
  const fuel = selectedFuel(form);
  const litres = parseInt(form.querySelector("[data-litres-value]").value, 10);
  const total = fuel.unitPrice * litres;
  setAll(form, "[data-total-display]", formatPkr(total));
  form.querySelector("[data-price-snapshot]").value = fuel.unitPrice.toFixed(2);
}

function setLitres(form, value) {
  form.querySelector("[data-litres-value]").value = value;
  form.querySelectorAll("[data-litres-chip]").forEach((chip) => {
    chip.classList.toggle("chip--selected", Number(chip.dataset.litresChip) === value);
  });
  updateSummary(form);
}

function initChips(form) {
  form.querySelectorAll("[data-litres-chip]").forEach((chip) => {
    chip.addEventListener("click", () => setLitres(form, Number(chip.dataset.litresChip)));
  });
}

function initSegmentedControl(form) {
  form.querySelectorAll(".segmented__input").forEach((input) => {
    input.addEventListener("change", () => {
      form.querySelectorAll(".segmented__option").forEach((option) => {
        option.classList.toggle(
          "segmented__option--selected",
          option.querySelector(".segmented__input") === input,
        );
      });
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
  form.querySelector("[data-area-fallback]").hidden = state === "captured";
  const icon = card.querySelector("[data-location-icon] use");
  if (icon) {
    const base = icon.getAttribute("href").split("#")[0];
    icon.setAttribute("href", `${base}#icon-${state === "captured" ? "check" : "location-crosshairs"}`);
  }
}

function requestLocation(form) {
  if (!navigator.geolocation) {
    setLocationState(form, "off", "Location is off", "Pick your area and type your vehicle note.");
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
    },
    () => {
      form.querySelector("[data-latitude]").value = "";
      form.querySelector("[data-longitude]").value = "";
      setLocationState(form, "off", "Location is off", "Pick your area and type your vehicle note.");
    },
    { enableHighAccuracy: true, timeout: 8000 },
  );
}

function initLocation(form) {
  requestLocation(form);
  form.querySelector("[data-location-action]").addEventListener("click", () => requestLocation(form));
}

export function validateEmergencyOrder(form) {
  const errors = {};
  const note = form.querySelector("#field-note").value.trim();
  if (!note) errors.note = true;
  const hasLocation = form.querySelector("[data-latitude]").value !== "";
  if (!hasLocation && !form.querySelector("#field-area").value) errors.area = true;

  form.querySelectorAll("[data-error]").forEach((el) => {
    el.hidden = !errors[el.dataset.error];
  });

  const firstError = Object.keys(errors)[0];
  if (firstError === "note") form.querySelector("#field-note").focus();
  else if (firstError === "area") form.querySelector("#field-area").focus();

  return Object.keys(errors).length === 0;
}

export function emergencySummary(form) {
  const fuel = selectedFuel(form);
  const litres = parseInt(form.querySelector("[data-litres-value]").value, 10);
  const area = form.querySelector("#field-area").value;
  return {
    fuel_type: fuel.name,
    litres,
    unitPrice: fuel.unitPrice,
    total: fuel.unitPrice * litres,
    deliverTo: area || "Your current location",
    address: null,
    area,
    note: form.querySelector("#field-note").value.trim(),
    latitude: form.querySelector("[data-latitude]").value || null,
    longitude: form.querySelector("[data-longitude]").value || null,
    orderKey: form.querySelector("[data-order-key]").value,
    priceSnapshot: form.querySelector("[data-price-snapshot]").value,
    csrfToken: form.querySelector("[data-csrf-token]").value,
  };
}

function buildRequestBody(summary) {
  return {
    fuel_type: summary.fuel_type,
    litres: summary.litres,
    area: summary.area,
    note: summary.note,
    latitude: summary.latitude,
    longitude: summary.longitude,
    order_key: summary.orderKey,
    price_snapshot: summary.priceSnapshot,
  };
}

function handleCustomError(dialog, data) {
  if (data.status !== "already_open") return false;
  const errorEl = dialog.querySelector("[data-confirm-form-error]");
  errorEl.hidden = false;
  errorEl.textContent = "";
  errorEl.append(document.createTextNode(`${data.message} `));
  const link = document.createElement("a");
  link.href = data.track_url;
  link.textContent = "Track it";
  errorEl.append(link);
  return true;
}

export function initOrderEmergencyForm() {
  const form = document.querySelector("[data-order-emergency]");
  if (!form) return;
  if (form.dataset.disabled !== undefined) return;

  initSegmentedControl(form);
  initChips(form);
  initLocation(form);
  updateSummary(form);

  initConfirmOrderDialog(form, {
    validate: validateEmergencyOrder,
    summary: emergencySummary,
    endpoint: "/app/order/emergency",
    formatPkr,
    buildRequestBody,
    handleCustomError,
  });
}

initOrderEmergencyForm();
