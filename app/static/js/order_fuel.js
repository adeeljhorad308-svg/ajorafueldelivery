import { initConfirmOrderDialog } from "./order_confirm_dialog.js";

// Mirrors app/areas.py: used only to guess a human place name from raw
// coordinates for the "Location captured" message (no geocoding service).
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

const MIN_LITRES = 5;
const MAX_LITRES = 100;

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

function litresValue(form) {
  const raw = parseInt(form.querySelector("#field-litres").value, 10);
  if (Number.isNaN(raw)) return null;
  return Math.min(MAX_LITRES, Math.max(MIN_LITRES, raw));
}

function setAll(selector, text) {
  document.querySelectorAll(selector).forEach((el) => {
    el.textContent = text;
  });
}

function updateSummary(form) {
  const fuel = selectedFuel(form);
  const litres = parseInt(form.querySelector("#field-litres").value, 10) || 0;
  const address = form.querySelector("#field-address").value.trim();
  const area = form.querySelector("#field-area").value;
  const total = fuel.unitPrice * litres;

  setAll("[data-summary-fuel]", fuel.name);
  setAll("[data-summary-quantity]", `${litres} L`);
  setAll("[data-summary-price]", `${formatPkr(fuel.unitPrice)} / litre`);
  setAll("[data-summary-deliver]", address || area || "—");
  setAll("[data-total-display]", formatPkr(total));

  form.querySelector("[data-price-snapshot]").value = fuel.unitPrice.toFixed(2);
}

function syncChipSelection(form) {
  const litres = form.querySelector("#field-litres").value;
  form.querySelectorAll("[data-litres-chip]").forEach((chip) => {
    chip.classList.toggle("chip--selected", chip.dataset.litresChip === litres);
  });
}

function setLitres(form, value) {
  const clamped = Math.min(MAX_LITRES, Math.max(MIN_LITRES, value));
  form.querySelector("#field-litres").value = clamped;
  syncChipSelection(form);
  updateSummary(form);
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

function initStepper(form) {
  const stepper = form.querySelector("[data-stepper]");
  const step = parseInt(stepper.dataset.step, 10);
  const input = form.querySelector("#field-litres");
  stepper.querySelector("[data-stepper-decrease]").addEventListener("click", () => {
    setLitres(form, (parseInt(input.value, 10) || MIN_LITRES) - step);
  });
  stepper.querySelector("[data-stepper-increase]").addEventListener("click", () => {
    setLitres(form, (parseInt(input.value, 10) || MIN_LITRES) + step);
  });
  input.addEventListener("change", () => setLitres(form, parseInt(input.value, 10) || MIN_LITRES));
}

function initChips(form) {
  form.querySelectorAll("[data-litres-chip]").forEach((chip) => {
    chip.addEventListener("click", () => {
      setLitres(form, parseInt(chip.dataset.litresChip, 10));
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
      setLocationState(
        form,
        "captured",
        "Location captured",
        `Within ${Math.round(accuracy)} m · ${area}`,
      );
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

export function validateFuelOrder(form) {
  const errors = {};
  const litres = litresValue(form);
  if (litres === null || litres < MIN_LITRES || litres > MAX_LITRES) {
    errors.litres = true;
  }
  if (!form.querySelector("#field-address").value.trim()) {
    errors.address = true;
  }
  const hasLocation = form.querySelector("[data-latitude]").value !== "";
  if (!hasLocation && !form.querySelector("#field-area").value) {
    errors.area = true;
  }

  form.querySelectorAll("[data-error]").forEach((el) => {
    el.hidden = !errors[el.dataset.error];
  });
  form.querySelector("[data-stepper]").classList.toggle("stepper--error", Boolean(errors.litres));

  const firstError = Object.keys(errors)[0];
  if (firstError === "address") form.querySelector("#field-address").focus();
  else if (firstError === "area") form.querySelector("#field-area").focus();
  else if (firstError === "litres") form.querySelector("#field-litres").focus();

  return Object.keys(errors).length === 0;
}

export function orderSummary(form) {
  const fuel = selectedFuel(form);
  const litres = parseInt(form.querySelector("#field-litres").value, 10);
  const address = form.querySelector("#field-address").value.trim();
  const area = form.querySelector("#field-area").value;
  return {
    fuel_type: fuel.name,
    litres,
    unitPrice: fuel.unitPrice,
    total: fuel.unitPrice * litres,
    deliverTo: address || area,
    address,
    area,
    note: form.querySelector("#field-note") ? form.querySelector("#field-note").value.trim() : "",
    latitude: form.querySelector("[data-latitude]").value || null,
    longitude: form.querySelector("[data-longitude]").value || null,
    orderKey: form.querySelector("[data-order-key]").value,
    priceSnapshot: form.querySelector("[data-price-snapshot]").value,
    csrfToken: form.querySelector("[data-csrf-token]").value,
  };
}

export function initOrderFuelForm() {
  const form = document.querySelector("[data-order-fuel]");
  if (!form) return;

  initSegmentedControl(form);
  initStepper(form);
  initChips(form);
  initLocation(form);
  syncChipSelection(form);
  updateSummary(form);

  form.querySelector("#field-address").addEventListener("input", () => updateSummary(form));
  form.querySelector("#field-area").addEventListener("change", () => updateSummary(form));

  initConfirmOrderDialog(form, {
    validate: validateFuelOrder,
    summary: orderSummary,
    endpoint: "/app/order/fuel",
    formatPkr,
  });
}

initOrderFuelForm();
