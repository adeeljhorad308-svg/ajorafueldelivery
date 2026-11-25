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

const MIN_LITRES = 20;
const MAX_LITRES = 500;
const CALL_THRESHOLD = 200;

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

function selectSingleChip(form, groupSelector, hiddenInput, value) {
  hiddenInput.value = value;
  form.querySelectorAll(groupSelector).forEach((chip) => {
    chip.classList.toggle("chip--selected", chip.dataset.chipValue === String(value));
  });
}

function litresValue(form) {
  const raw = parseInt(form.querySelector("#field-litres").value, 10);
  if (Number.isNaN(raw)) return null;
  return Math.min(MAX_LITRES, Math.max(MIN_LITRES, raw));
}

function dayLabel(form, value) {
  const chip = form.querySelector(`[data-day-chip="${value}"]`);
  return chip ? chip.textContent : value;
}

function slotLabel(form, value) {
  const chip = form.querySelector(`[data-slot-chip="${value}"]`);
  return chip ? chip.textContent : value;
}

function deliveryLabel(form) {
  const timing = form.querySelector("[data-timing-value]").value;
  if (timing === "asap") return "As soon as possible";
  const day = form.querySelector("[data-day-value]").value;
  const slot = form.querySelector("[data-slot-value]").value;
  return `${dayLabel(form, day)}, ${slotLabel(form, slot)}`;
}

function updateSummary(form) {
  const fuel = selectedFuel(form);
  const litres = parseInt(form.querySelector("#field-litres").value, 10) || 0;
  const total = fuel.unitPrice * litres;

  form.querySelector("[data-summary-type]").textContent =
    form.querySelector("[data-generator-type]").value;
  form.querySelector("[data-summary-fuel]").textContent = fuel.name;
  form.querySelector("[data-summary-quantity]").textContent = `${litres} L`;
  form.querySelector("[data-summary-price]").textContent = `${formatPkr(fuel.unitPrice)} / litre`;
  form.querySelector("[data-summary-delivery]").textContent = deliveryLabel(form);
  form.querySelector("[data-total-display]").textContent = formatPkr(total);
  form.querySelector("[data-price-snapshot]").value = fuel.unitPrice.toFixed(2);

  form.querySelector("[data-call-banner]").hidden = litres <= CALL_THRESHOLD;
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
  const stepperEl = form.querySelector("[data-stepper]");
  const step = parseInt(stepperEl.dataset.step, 10);
  const input = form.querySelector("#field-litres");
  stepperEl.querySelector("[data-stepper-decrease]").addEventListener("click", () => {
    setLitres(form, (parseInt(input.value, 10) || MIN_LITRES) - step);
  });
  stepperEl.querySelector("[data-stepper-increase]").addEventListener("click", () => {
    setLitres(form, (parseInt(input.value, 10) || MIN_LITRES) + step);
  });
  input.addEventListener("change", () => setLitres(form, parseInt(input.value, 10) || MIN_LITRES));
}

function initChips(form) {
  form.querySelectorAll("[data-litres-chip]").forEach((chip) => {
    chip.addEventListener("click", () => setLitres(form, parseInt(chip.dataset.litresChip, 10)));
  });
}

function initTypeChips(form) {
  form.querySelectorAll("[data-type-chip]").forEach((chip) => {
    chip.dataset.chipValue = chip.dataset.typeChip;
    chip.addEventListener("click", () => {
      selectSingleChip(form, "[data-type-chip]", form.querySelector("[data-generator-type]"), chip.dataset.typeChip);
      updateSummary(form);
    });
  });
}

function initDayAndSlotChips(form) {
  form.querySelectorAll("[data-day-chip]").forEach((chip) => {
    chip.dataset.chipValue = chip.dataset.dayChip;
    chip.addEventListener("click", () => {
      selectSingleChip(form, "[data-day-chip]", form.querySelector("[data-day-value]"), chip.dataset.dayChip);
      updateSummary(form);
    });
  });
  form.querySelectorAll("[data-slot-chip]").forEach((chip) => {
    chip.dataset.chipValue = chip.dataset.slotChip;
    chip.addEventListener("click", () => {
      selectSingleChip(form, "[data-slot-chip]", form.querySelector("[data-slot-value]"), chip.dataset.slotChip);
      updateSummary(form);
    });
  });
}

function initTimingChips(form) {
  const schedule = form.querySelector("[data-generator-schedule]");
  form.querySelectorAll("[data-timing-chip]").forEach((chip) => {
    chip.dataset.chipValue = chip.dataset.timingChip;
    chip.addEventListener("click", () => {
      selectSingleChip(form, "[data-timing-chip]", form.querySelector("[data-timing-value]"), chip.dataset.timingChip);
      schedule.hidden = chip.dataset.timingChip !== "scheduled";
      updateSummary(form);
    });
  });
}

function requestLocation(form) {
  if (!navigator.geolocation) return;
  const button = form.querySelector("[data-location-action]");
  navigator.geolocation.getCurrentPosition(
    (position) => {
      const { latitude, longitude } = position.coords;
      form.querySelector("[data-latitude]").value = latitude;
      form.querySelector("[data-longitude]").value = longitude;
      const area = nearestArea(latitude, longitude);
      form.querySelector("#field-area").value = area;
      form.querySelector("[data-location-action-label]").textContent = "Location added";
      button.disabled = true;
    },
    () => {},
    { enableHighAccuracy: true, timeout: 8000 },
  );
}

export function validateGeneratorOrder(form) {
  const errors = {};
  const litres = litresValue(form);
  if (litres === null || litres < MIN_LITRES || litres > MAX_LITRES) errors.litres = true;
  if (!form.querySelector("#field-address").value.trim()) errors.address = true;
  const hasLocation = form.querySelector("[data-latitude]").value !== "";
  if (!hasLocation && !form.querySelector("#field-area").value) errors.area = true;

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

export function generatorSummary(form) {
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
    generatorType: form.querySelector("[data-generator-type]").value,
    timing: form.querySelector("[data-timing-value]").value,
    day: form.querySelector("[data-day-value]").value,
    slot: form.querySelector("[data-slot-value]").value,
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
    address: summary.address,
    area: summary.area,
    generator_type: summary.generatorType,
    timing: summary.timing,
    day: summary.day,
    slot: summary.slot,
    latitude: summary.latitude,
    longitude: summary.longitude,
    order_key: summary.orderKey,
    price_snapshot: summary.priceSnapshot,
  };
}

export function initOrderGeneratorForm() {
  const form = document.querySelector("[data-order-generator]");
  if (!form) return;

  initSegmentedControl(form);
  initStepper(form);
  initChips(form);
  initTypeChips(form);
  initDayAndSlotChips(form);
  initTimingChips(form);
  syncChipSelection(form);
  updateSummary(form);

  form.querySelector("#field-address").addEventListener("input", () => updateSummary(form));
  form.querySelector("#field-area").addEventListener("change", () => updateSummary(form));
  form.querySelector("[data-location-action]").addEventListener("click", () => requestLocation(form));

  initConfirmOrderDialog(form, {
    validate: validateGeneratorOrder,
    summary: generatorSummary,
    endpoint: "/app/order/generator",
    formatPkr,
    buildRequestBody,
  });
}

initOrderGeneratorForm();
