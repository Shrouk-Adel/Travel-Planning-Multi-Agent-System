let currentThreadId = localStorage.getItem("travel_thread_id") || null;
let latestAnswerMarkdown = "";
let waitingForApproval = false;

const AGENT_LABELS = {
  flight_agent: "✈️ Flight Agent",
  hotel_agent: "🏨 Hotel Agent",
  weather_agent: "🌦️ Weather Agent",
  budget_agent: "💰 Budget Agent",
  itinerary_agent: "🗓️ Itinerary Agent"
};

function flagEmoji(countryCode) {
  if (!countryCode) return "🏳️";
  return countryCode
    .toUpperCase()
    .replace(/./g, (char) => String.fromCodePoint(127397 + char.charCodeAt(0)));
}

// Major travel-relevant cities, one per country (mix of capitals and the
// most commonly booked travel hub for that country). `code` is the
// country's ISO code, used to render the flag next to each city.
const CITIES = [
  ["Kabul", "Afghanistan", "AF"], ["Tirana", "Albania", "AL"], ["Algiers", "Algeria", "DZ"],
  ["Andorra la Vella", "Andorra", "AD"], ["Luanda", "Angola", "AO"], ["Buenos Aires", "Argentina", "AR"],
  ["Yerevan", "Armenia", "AM"], ["Sydney", "Australia", "AU"], ["Vienna", "Austria", "AT"],
  ["Baku", "Azerbaijan", "AZ"], ["Nassau", "Bahamas", "BS"], ["Manama", "Bahrain", "BH"],
  ["Dhaka", "Bangladesh", "BD"], ["Bridgetown", "Barbados", "BB"], ["Minsk", "Belarus", "BY"],
  ["Brussels", "Belgium", "BE"], ["Belize City", "Belize", "BZ"], ["Cotonou", "Benin", "BJ"],
  ["Thimphu", "Bhutan", "BT"], ["La Paz", "Bolivia", "BO"], ["Sarajevo", "Bosnia and Herzegovina", "BA"],
  ["Gaborone", "Botswana", "BW"], ["Rio de Janeiro", "Brazil", "BR"], ["Bandar Seri Begawan", "Brunei", "BN"],
  ["Sofia", "Bulgaria", "BG"], ["Ouagadougou", "Burkina Faso", "BF"], ["Bujumbura", "Burundi", "BI"],
  ["Phnom Penh", "Cambodia", "KH"], ["Yaoundé", "Cameroon", "CM"], ["Toronto", "Canada", "CA"],
  ["N'Djamena", "Chad", "TD"], ["Santiago", "Chile", "CL"], ["Shanghai", "China", "CN"],
  ["Bogotá", "Colombia", "CO"], ["San José", "Costa Rica", "CR"], ["Zagreb", "Croatia", "HR"],
  ["Havana", "Cuba", "CU"], ["Nicosia", "Cyprus", "CY"], ["Prague", "Czech Republic", "CZ"],
  ["Copenhagen", "Denmark", "DK"], ["Djibouti City", "Djibouti", "DJ"], ["Santo Domingo", "Dominican Republic", "DO"],
  ["Quito", "Ecuador", "EC"], ["Cairo", "Egypt", "EG"], ["San Salvador", "El Salvador", "SV"],
  ["Tallinn", "Estonia", "EE"], ["Addis Ababa", "Ethiopia", "ET"], ["Suva", "Fiji", "FJ"],
  ["Helsinki", "Finland", "FI"], ["Paris", "France", "FR"], ["Libreville", "Gabon", "GA"],
  ["Banjul", "Gambia", "GM"], ["Tbilisi", "Georgia", "GE"], ["Berlin", "Germany", "DE"],
  ["Accra", "Ghana", "GH"], ["Athens", "Greece", "GR"], ["Guatemala City", "Guatemala", "GT"],
  ["Conakry", "Guinea", "GN"], ["Georgetown", "Guyana", "GY"], ["Port-au-Prince", "Haiti", "HT"],
  ["Tegucigalpa", "Honduras", "HN"], ["Hong Kong", "Hong Kong", "HK"], ["Budapest", "Hungary", "HU"],
  ["Reykjavik", "Iceland", "IS"], ["Mumbai", "India", "IN"], ["Jakarta", "Indonesia", "ID"],
  ["Tehran", "Iran", "IR"], ["Baghdad", "Iraq", "IQ"], ["Dublin", "Ireland", "IE"],
  ["Tel Aviv", "Israel", "IL"], ["Rome", "Italy", "IT"], ["Kingston", "Jamaica", "JM"],
  ["Tokyo", "Japan", "JP"], ["Amman", "Jordan", "JO"], ["Almaty", "Kazakhstan", "KZ"],
  ["Nairobi", "Kenya", "KE"], ["Kuwait City", "Kuwait", "KW"], ["Bishkek", "Kyrgyzstan", "KG"],
  ["Vientiane", "Laos", "LA"], ["Riga", "Latvia", "LV"], ["Beirut", "Lebanon", "LB"],
  ["Maseru", "Lesotho", "LS"], ["Monrovia", "Liberia", "LR"], ["Tripoli", "Libya", "LY"],
  ["Vaduz", "Liechtenstein", "LI"], ["Vilnius", "Lithuania", "LT"], ["Luxembourg City", "Luxembourg", "LU"],
  ["Antananarivo", "Madagascar", "MG"], ["Lilongwe", "Malawi", "MW"], ["Kuala Lumpur", "Malaysia", "MY"],
  ["Malé", "Maldives", "MV"], ["Bamako", "Mali", "ML"], ["Valletta", "Malta", "MT"],
  ["Nouakchott", "Mauritania", "MR"], ["Port Louis", "Mauritius", "MU"], ["Mexico City", "Mexico", "MX"],
  ["Chisinau", "Moldova", "MD"], ["Monaco", "Monaco", "MC"], ["Ulaanbaatar", "Mongolia", "MN"],
  ["Podgorica", "Montenegro", "ME"], ["Marrakech", "Morocco", "MA"], ["Maputo", "Mozambique", "MZ"],
  ["Yangon", "Myanmar", "MM"], ["Windhoek", "Namibia", "NA"], ["Kathmandu", "Nepal", "NP"],
  ["Amsterdam", "Netherlands", "NL"], ["Auckland", "New Zealand", "NZ"], ["Managua", "Nicaragua", "NI"],
  ["Niamey", "Niger", "NE"], ["Lagos", "Nigeria", "NG"], ["Pyongyang", "North Korea", "KP"],
  ["Skopje", "North Macedonia", "MK"], ["Oslo", "Norway", "NO"], ["Muscat", "Oman", "OM"],
  ["Karachi", "Pakistan", "PK"], ["Panama City", "Panama", "PA"], ["Port Moresby", "Papua New Guinea", "PG"],
  ["Asunción", "Paraguay", "PY"], ["Lima", "Peru", "PE"], ["Manila", "Philippines", "PH"],
  ["Warsaw", "Poland", "PL"], ["Lisbon", "Portugal", "PT"], ["Doha", "Qatar", "QA"],
  ["Bucharest", "Romania", "RO"], ["Moscow", "Russia", "RU"], ["Kigali", "Rwanda", "RW"],
  ["Riyadh", "Saudi Arabia", "SA"], ["Dakar", "Senegal", "SN"], ["Belgrade", "Serbia", "RS"],
  ["Victoria", "Seychelles", "SC"], ["Freetown", "Sierra Leone", "SL"], ["Singapore", "Singapore", "SG"],
  ["Bratislava", "Slovakia", "SK"], ["Ljubljana", "Slovenia", "SI"], ["Mogadishu", "Somalia", "SO"],
  ["Cape Town", "South Africa", "ZA"], ["Seoul", "South Korea", "KR"], ["Juba", "South Sudan", "SS"],
  ["Barcelona", "Spain", "ES"], ["Colombo", "Sri Lanka", "LK"], ["Khartoum", "Sudan", "SD"],
  ["Paramaribo", "Suriname", "SR"], ["Stockholm", "Sweden", "SE"], ["Zurich", "Switzerland", "CH"],
  ["Damascus", "Syria", "SY"], ["Taipei", "Taiwan", "TW"], ["Dushanbe", "Tajikistan", "TJ"],
  ["Dar es Salaam", "Tanzania", "TZ"], ["Bangkok", "Thailand", "TH"], ["Lomé", "Togo", "TG"],
  ["Port of Spain", "Trinidad and Tobago", "TT"], ["Tunis", "Tunisia", "TN"], ["Istanbul", "Turkey", "TR"],
  ["Ashgabat", "Turkmenistan", "TM"], ["Kampala", "Uganda", "UG"], ["Kyiv", "Ukraine", "UA"],
  ["Dubai", "United Arab Emirates", "AE"], ["London", "United Kingdom", "GB"], ["New York", "United States", "US"],
  ["Montevideo", "Uruguay", "UY"], ["Tashkent", "Uzbekistan", "UZ"], ["Port Vila", "Vanuatu", "VU"],
  ["Caracas", "Venezuela", "VE"], ["Ho Chi Minh City", "Vietnam", "VN"], ["Sana'a", "Yemen", "YE"],
  ["Lusaka", "Zambia", "ZM"], ["Harare", "Zimbabwe", "ZW"]
].map(([city, country, code]) => ({ city, country, code }));

const CURRENCIES = [
  ["USD", "US Dollar"], ["EUR", "Euro"], ["GBP", "British Pound"], ["BDT", "Bangladeshi Taka"],
  ["INR", "Indian Rupee"], ["PKR", "Pakistani Rupee"], ["JPY", "Japanese Yen"], ["CNY", "Chinese Yuan"],
  ["AED", "UAE Dirham"], ["SAR", "Saudi Riyal"], ["SGD", "Singapore Dollar"], ["MYR", "Malaysian Ringgit"],
  ["THB", "Thai Baht"], ["IDR", "Indonesian Rupiah"], ["AUD", "Australian Dollar"], ["CAD", "Canadian Dollar"],
  ["CHF", "Swiss Franc"], ["HKD", "Hong Kong Dollar"], ["KRW", "South Korean Won"], ["TRY", "Turkish Lira"],
  ["RUB", "Russian Ruble"], ["BRL", "Brazilian Real"], ["ZAR", "South African Rand"], ["EGP", "Egyptian Pound"],
  ["NGN", "Nigerian Naira"], ["KES", "Kenyan Shilling"], ["PHP", "Philippine Peso"], ["VND", "Vietnamese Dong"],
  ["NZD", "New Zealand Dollar"], ["SEK", "Swedish Krona"], ["NOK", "Norwegian Krone"], ["DKK", "Danish Krone"],
  ["PLN", "Polish Zloty"], ["CZK", "Czech Koruna"], ["HUF", "Hungarian Forint"], ["ILS", "Israeli Shekel"],
  ["QAR", "Qatari Riyal"], ["KWD", "Kuwaiti Dinar"], ["OMR", "Omani Rial"], ["BHD", "Bahraini Dinar"],
  ["JOD", "Jordanian Dinar"], ["LKR", "Sri Lankan Rupee"], ["NPR", "Nepalese Rupee"], ["MMK", "Myanmar Kyat"],
  ["MXN", "Mexican Peso"], ["ARS", "Argentine Peso"], ["CLP", "Chilean Peso"], ["COP", "Colombian Peso"]
].map(([code, name]) => ({ code, name }));

/**
 * Wires a text input to a filterable dropdown of options.
 * options: [{ value, label, sub, flag }]
 * onSelect(option) fires when the user picks one.
 */
function initCombobox({ inputId, dropdownId, options, onSelect, formatSelected, strict = true }) {
  const input = document.getElementById(inputId);
  const dropdown = document.getElementById(dropdownId);
  if (!input || !dropdown) return;

  let highlighted = -1;
  let visible = [];
  let lastValue = input.value || "";

  function renderList(list) {
    dropdown.innerHTML = "";
    if (!list.length) {
      const empty = document.createElement("div");
      empty.className = "combobox-empty";
      empty.textContent = "No matches found";
      dropdown.appendChild(empty);
      return;
    }
    list.forEach((opt, idx) => {
      const row = document.createElement("div");
      row.className = "combobox-option" + (idx === highlighted ? " highlighted" : "");
      row.innerHTML = `${opt.flag ? `<span class="opt-flag">${opt.flag}</span>` : ""}<span>${opt.label}</span>${opt.sub ? `<span class="opt-code">${opt.sub}</span>` : ""}`;
      row.addEventListener("mousedown", (e) => {
        e.preventDefault();
        selectOption(opt);
      });
      dropdown.appendChild(row);
    });
  }

  function selectOption(opt) {
    lastValue = formatSelected ? formatSelected(opt) : opt.label;
    input.value = lastValue;
    closeDropdown();
    if (onSelect) onSelect(opt);
  }

  function filter(query) {
    const q = query.trim().toLowerCase();
    if (!q) return options;
    const haystack = (o) => `${o.label} ${o.sub || ""}`.toLowerCase();
    const startsWith = options.filter((o) => haystack(o).startsWith(q));
    const contains = options.filter(
      (o) => !haystack(o).startsWith(q) && haystack(o).includes(q)
    );
    return [...startsWith, ...contains];
  }

  function openDropdown() {
    visible = filter(input.value === lastValue ? "" : input.value);
    highlighted = -1;
    renderList(visible);
    dropdown.classList.remove("hidden");
  }

  function closeDropdown() {
    dropdown.classList.add("hidden");
  }

  input.addEventListener("focus", () => {
    input.select();
    openDropdown();
  });
  input.addEventListener("click", openDropdown);
  input.addEventListener("input", openDropdown);

  input.addEventListener("keydown", (e) => {
    if (dropdown.classList.contains("hidden")) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      highlighted = Math.min(highlighted + 1, visible.length - 1);
      renderList(visible);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      highlighted = Math.max(highlighted - 1, 0);
      renderList(visible);
    } else if (e.key === "Enter") {
      if (highlighted >= 0 && visible[highlighted]) {
        e.preventDefault();
        selectOption(visible[highlighted]);
      }
    } else if (e.key === "Escape") {
      closeDropdown();
    }
  });

  input.addEventListener("blur", () => {
    // Give a click on an option time to register before we validate.
    setTimeout(() => {
      if (!strict) return;
      const typed = input.value.trim().toLowerCase();
      if (!typed) {
        lastValue = "";
        return;
      }
      const exact = options.find(
        (o) => o.label.toLowerCase() === typed || (formatSelected && formatSelected(o).toLowerCase() === typed)
      );
      if (exact) {
        selectOption(exact);
      } else {
        input.value = lastValue;
      }
    }, 150);
  });

  document.addEventListener("click", (e) => {
    if (!input.contains(e.target) && !dropdown.contains(e.target)) {
      closeDropdown();
    }
  });
}

function initCityComboboxes() {
  const cityOptions = CITIES.map((c) => ({
    value: c.city,
    label: c.city,
    sub: c.country,
    country: c.country,
    flag: flagEmoji(c.code)
  }));

  initCombobox({
    inputId: "originInput",
    dropdownId: "originDropdown",
    options: cityOptions,
    formatSelected: (opt) => `${opt.label}, ${opt.country}`
  });

  initCombobox({
    inputId: "destinationInput",
    dropdownId: "destinationDropdown",
    options: cityOptions,
    formatSelected: (opt) => `${opt.label}, ${opt.country}`
  });
}

function initCurrencyCombobox() {
  const currencyCodeField = document.getElementById("currencyCode");
  const currencyOptions = CURRENCIES.map((c) => ({
    value: c.code,
    label: c.name,
    sub: c.code
  }));

  initCombobox({
    inputId: "currencyInput",
    dropdownId: "currencyDropdown",
    options: currencyOptions,
    formatSelected: (opt) => `${opt.sub} — ${opt.label}`,
    onSelect: (opt) => {
      if (currencyCodeField) currencyCodeField.value = opt.value;
    }
  });
}

const selectedInterests = new Set(["Flights", "Hotels", "Sightseeing"]);

const PRESETS = {
  japan: {
    origin: "Dhaka, Bangladesh",
    destination: "Tokyo, Japan",
    duration: 7,
    travelers: 2,
    budget: 200000,
    currency: "BDT",
    interests: ["Flights", "Hotels", "Sightseeing"]
  },
  dubai: {
    origin: "Dhaka, Bangladesh",
    destination: "Dubai, United Arab Emirates",
    duration: 5,
    travelers: 2,
    budget: 150000,
    currency: "BDT",
    interests: ["Flights", "Hotels", "Sightseeing", "Shopping"]
  },
  thailand: {
    origin: "Dhaka, Bangladesh",
    destination: "Bangkok, Thailand",
    duration: 7,
    travelers: 2,
    budget: 120000,
    currency: "BDT",
    interests: ["Flights", "Hotels", "Sightseeing"]
  }
};

function initInterestChips() {
  const chips = document.querySelectorAll(".interest-chip");
  chips.forEach((chip) => {
    if (selectedInterests.has(chip.dataset.value)) {
      chip.classList.add("active");
    }
    chip.addEventListener("click", () => {
      const value = chip.dataset.value;
      if (selectedInterests.has(value)) {
        selectedInterests.delete(value);
        chip.classList.remove("active");
      } else {
        selectedInterests.add(value);
        chip.classList.add("active");
      }
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initInterestChips();
  initCityComboboxes();
  initCurrencyCombobox();
  const form = document.getElementById("tripForm");
  if (form) form.addEventListener("submit", sendMessage);
});

function applyPreset(name) {
  const preset = PRESETS[name];
  if (!preset) return;

  document.getElementById("originInput").value = preset.origin;
  document.getElementById("destinationInput").value = preset.destination;
  document.getElementById("durationInput").value = preset.duration;
  document.getElementById("travelersInput").value = preset.travelers;
  document.getElementById("budgetInput").value = preset.budget;

  const currency = CURRENCIES.find((c) => c.code === preset.currency);
  if (currency) {
    document.getElementById("currencyInput").value = `${currency.code} — ${currency.name}`;
    document.getElementById("currencyCode").value = currency.code;
  }

  selectedInterests.clear();
  document.querySelectorAll(".interest-chip").forEach((chip) => {
    const active = preset.interests.includes(chip.dataset.value);
    chip.classList.toggle("active", active);
    if (active) selectedInterests.add(chip.dataset.value);
  });
}

// Builds the JSON body sent to POST /api/travel. Field names/types must
// match the backend's TravelRequest pydantic model exactly:
//   origin: str, destination: str, date: str, duration: int, budget: float,
//   currency: str, num_travelers: int, interests: list[str] = [],
//   thread_id: str | None, message: str | None
function buildTripPayload() {
  const origin = document.getElementById("originInput").value.trim();
  const destination = document.getElementById("destinationInput").value.trim();
  const startDate = document.getElementById("startDateInput").value; // yyyy-mm-dd from <input type="date">
  const duration = document.getElementById("durationInput").value;
  const travelers = document.getElementById("travelersInput").value;
  const budget = document.getElementById("budgetInput").value;
  const currency = document.getElementById("currencyCode").value || "USD";
  const notes = document.getElementById("notesInput").value.trim();
  const interests = Array.from(selectedInterests);

  if (!origin || !destination) {
    return { error: "Please enter both an origin and a destination city." };
  }
  if (!startDate) {
    return { error: "Please choose a start date." };
  }
  if (!duration || Number(duration) < 1) {
    return { error: "Please enter a trip duration of at least 1 day." };
  }
  if (!travelers || Number(travelers) < 1) {
    return { error: "Please enter at least 1 traveler." };
  }
  if (!budget || Number(budget) <= 0) {
    return { error: "Please enter a budget." };
  }

  return {
    payload: {
      origin,
      destination,
      date: startDate,
      duration: Number(duration),
      budget: Number(budget),
      currency,
      num_travelers: Number(travelers),
      interests,
      thread_id: currentThreadId,
      message: notes || null
    }
  };
}

function setLoading(isLoading, mode = "draft") {
  const sendBtn = document.getElementById("sendBtn");
  const btnText = document.getElementById("btnText");
  const btnLoader = document.getElementById("btnLoader");
  const approveBtn = document.getElementById("approveBtn");
  const reviseBtn = document.getElementById("reviseBtn");

  sendBtn.disabled = isLoading;
  approveBtn.disabled = isLoading;
  reviseBtn.disabled = isLoading;

  if (isLoading && mode === "draft") {
    btnText.classList.add("hidden");
    btnLoader.classList.remove("hidden");
  } else {
    btnText.classList.remove("hidden");
    btnLoader.classList.add("hidden");
  }
}

function showError(message) {
  const errorBox = document.getElementById("errorBox");
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
  errorBox.scrollIntoView({ behavior: "smooth", block: "center" });
}

function hideError() {
  const errorBox = document.getElementById("errorBox");
  errorBox.classList.add("hidden");
  errorBox.textContent = "";
}

function renderMarkdown(element, markdown) {
  if (typeof marked !== "undefined") {
    element.innerHTML = marked.parse(markdown || "");
  } else {
    element.innerText = markdown || "";
  }
}

function showWorkflow(data) {
  const section = document.getElementById("workflowSection");
  const reasoning = document.getElementById("supervisorReasoning");
  const chips = document.getElementById("agentChips");
  const guardrailBadge = document.getElementById("guardrailBadge");

  // The backend no longer runs a supervisor/guardrail LLM step — agent
  // selection is derived deterministically from the form's interests, so
  // there's no reasoning text or guardrail verdict to show. Hide those
  // pieces rather than leaving stale/misleading placeholder copy.
  if (reasoning) reasoning.textContent = "Agents selected from your trip details.";
  if (guardrailBadge) guardrailBadge.classList.add("hidden");

  chips.innerHTML = "";
  (data.selected_agents || []).forEach((agent) => {
    const chip = document.createElement("span");
    chip.className = "agent-chip";
    chip.textContent = AGENT_LABELS[agent] || agent;
    chips.appendChild(chip);
  });

  section.classList.remove("hidden");
}

function showResult(answer, threadId, isDraft = false) {
  latestAnswerMarkdown = answer || "";

  const resultSection = document.getElementById("resultSection");
  const resultBox = document.getElementById("resultBox");
  const threadInfo = document.getElementById("threadInfo");
  const resultTitle = document.getElementById("resultTitle");

  renderMarkdown(resultBox, latestAnswerMarkdown);
  threadInfo.textContent = `Thread ID: ${threadId}`;
  resultTitle.textContent = isDraft ? "Draft Travel Plan" : "Your Final AI Travel Plan";
  resultSection.classList.remove("hidden");

  resultSection.scrollIntoView({
    behavior: "smooth",
    block: "start"
  });
}

function showApproval(data) {
  waitingForApproval = true;
  const section = document.getElementById("approvalSection");
  const approvalRequest = document.getElementById("approvalRequest");
  approvalRequest.textContent = data.approval_request ||
    "Approve the draft or provide feedback before the final plan is generated.";
  section.classList.remove("hidden");
}

function hideApproval() {
  waitingForApproval = false;
  document.getElementById("approvalSection").classList.add("hidden");
  document.getElementById("approvalFeedback").value = "";
}

async function sendMessage(event) {
  if (event) event.preventDefault();
  hideError();

  if (waitingForApproval) {
    showError("Please approve or revise the current draft before starting another plan.");
    return;
  }

  const built = buildTripPayload();

  if (built.error) {
    showError(built.error);
    return;
  }

  setLoading(true, "draft");

  try {
    const response = await fetch("/api/travel", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(built.payload)
    });

    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(data.error || "Something went wrong.");
    }

    currentThreadId = data.thread_id;
    localStorage.setItem("travel_thread_id", currentThreadId);

    showWorkflow(data);

    if (data.requires_approval) {
      showResult(data.itinerary || data.answer, data.thread_id, true);
      showApproval(data);
    } else {
      hideApproval();
      showResult(data.answer, data.thread_id, false);
    }
  } catch (error) {
    showError(error.message);
  } finally {
    setLoading(false, "draft");
  }
}

async function submitApproval(approved) {
  hideError();

  if (!currentThreadId || !waitingForApproval) {
    showError("There is no draft waiting for approval.");
    return;
  }

  const feedbackInput = document.getElementById("approvalFeedback");
  const feedback = feedbackInput.value.trim();

  if (!approved && !feedback) {
    showError("Please enter revision feedback before requesting changes.");
    feedbackInput.focus();
    return;
  }

  setLoading(true, "approval");

  try {
    const response = await fetch("/api/travel/approve", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        thread_id: currentThreadId,
        approved: approved,
        feedback: feedback
      })
    });

    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(data.error || "Could not resume the travel workflow.");
    }

    showWorkflow(data);
    hideApproval();
    showResult(data.answer, data.thread_id, false);
  } catch (error) {
    showError(error.message);
  } finally {
    setLoading(false, "approval");
  }
}

function copyResult() {
  const resultBox = document.getElementById("resultBox");
  const text = resultBox.innerText;

  if (!text) {
    return;
  }

  navigator.clipboard.writeText(text)
    .then(() => {
      const copyBtn = document.querySelector(".copy-btn");
      const oldText = copyBtn.textContent;
      copyBtn.textContent = "Copied!";

      setTimeout(() => {
        copyBtn.textContent = oldText;
      }, 1400);
    })
    .catch(() => {
      showError("Could not copy result.");
    });
}

function downloadPDF() {
  const pdfContent = document.getElementById("pdfContent");

  if (!latestAnswerMarkdown || !pdfContent) {
    showError("No travel plan available to download.");
    return;
  }

  const downloadBtn = document.querySelector(".download-btn");
  const oldText = downloadBtn.textContent;
  downloadBtn.textContent = "Preparing PDF...";
  downloadBtn.disabled = true;

  const options = {
    margin: 0.5,
    filename: "ai-travel-plan.pdf",
    image: {
      type: "jpeg",
      quality: 0.98
    },
    html2canvas: {
      scale: 2,
      useCORS: true,
      backgroundColor: "#ffffff"
    },
    jsPDF: {
      unit: "in",
      format: "a4",
      orientation: "portrait"
    },
    pagebreak: {
      mode: ["avoid-all", "css", "legacy"]
    }
  };

  html2pdf()
    .set(options)
    .from(pdfContent)
    .save()
    .then(() => {
      downloadBtn.textContent = oldText;
      downloadBtn.disabled = false;
    })
    .catch(() => {
      downloadBtn.textContent = oldText;
      downloadBtn.disabled = false;
      showError("Could not download PDF.");
    });
}

document.addEventListener("keydown", function(event) {
  if (event.ctrlKey && event.key === "Enter") {
    sendMessage();
  }
});