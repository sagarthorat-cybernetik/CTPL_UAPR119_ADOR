/* ============================================================
   BTS Monitoring System — Admin Threshold Panel
   Handles: Fetch, Edit, Save, Reset Thresholds
   ============================================================ */

const form = document.getElementById("thresholdForm");
const formHeaders = document.getElementById("headersForm");
const resetBtn = document.getElementById("resetDefaults");
const resetHeadersBtn = document.getElementById("resetHeadersDefaults");
const jsonView = document.getElementById("thresholdJsonView");

// Default safe threshold limits
const DEFAULT_THRESHOLDS = {
   "charge": {
      "Cell_Deviation_min": 50,
      "Cell_Deviation_max": 50,
      "cell_deviation_step": 1,
      "Capacity_min": 1000,
      "Capacity_max": 1000,
      "capacity_step": 1,
      "Pack_Voltage_min": 48,
      "Pack_Voltage_max": 48,
      "pack_voltage_step": 1,
      "Max_Cell_Voltage_min": 4.2,
      "Max_Cell_Voltage_max": 4.2,
      "Max_Cell_Voltage_step": 1,
      "Min_Cell_Voltage_min": 3.0,
      "Min_Cell_Voltage_max": 3.0,
      "Min_Cell_Voltage_step": 1,
      "Max_Cell_Temperature_min": 60,
      "Max_Cell_Temperature_max": 60,
      "Max_Cell_Temperature_step": 1,
      "Min_Cell_Temperature_min": 0,
      "Min_Cell_Temperature_max": 0,
      "Min_Cell_Temperature_step": 1,
      "SOC_min": 20,
      "SOC_max": 20,
      "SOC_step": 1,
      "End_SOC_min": 20,
      "End_SOC_max": 20,
      "End_SOC_step": 1,
      "temperature_difference_min": 15,
      "temperature_difference_max": 15,
      "temperature_difference_step": 1,
      "hrc_min": 0.5,
      "hrc_max": 1.5,
      "hrc_step": 1
    },
    "discharge": {
      "Cell_Deviation_min": 5,
      "Cell_Deviation_max": 50,
      "cell_deviation_step": 1,
      "Capacity_min": 1000,
      "Capacity_max": 1000,
      "capacity_step": 1,
      "Pack_Voltage_min": 48,
      "Pack_Voltage_max": 48,
      "pack_voltage_step": 1,
      "Max_Cell_Voltage_min": 4.2,
      "Max_Cell_Voltage_max": 4.2,
      "Max_Cell_Voltage_step": 1,
      "Min_Cell_Voltage_min": 3.0,
      "Min_Cell_Voltage_max": 3.0,
      "Min_Cell_Voltage_step": 1,
      "Max_Cell_Temperature_min": 60,
      "Max_Cell_Temperature_max": 60,
      "Max_Cell_Temperature_step": 1,
      "Min_Cell_Temperature_min": 0,
      "Min_Cell_Temperature_max": 0,
      "Min_Cell_Temperature_step": 1,
      "SOC_min": 20,
      "SOC_max": 20,
      "SOC_step": 1,
      "End_SOC_min": 20,
      "End_SOC_max": 20,
      "End_SOC_step": 1,
      "temperature_difference_min": 15,
      "temperature_difference_max": 15,
      "temperature_difference_step": 1,
      "hrd_min": 0.5,
      "hrd_max": 1.5,
      "hrd_step": 1
    }
};
const DEFAULT_HEADERS = {
  "Cell_Deviation": "Cell Deviation (mV)",
  "Capacity": "Capacity (mAh)",
  "Pack_Voltage": "Pack Voltage (V)",
  "Max_Cell_Voltage": "Max Cell Voltage (V)",
  "Min_Cell_Voltage": "Min Cell Voltage (V)",
  "Max_Cell_Temperature": "Max Cell Temperature (C)",
  "Min_Cell_Temperature": "Min Cell Temperature (C)",
  "SOC": "SOC (%)",
  "Temperature_Difference": "Temp Difference ∆T (Manual)",
  "Sheet_Name_Cell_Deviation": "1",
  "Sheet_Name_Capacity": "1",
  "Sheet_Name_Pack_Voltage": "1",
  "Sheet_Name_Max_Cell_Voltage": "1",
  "Sheet_Name_Min_Cell_Voltage": "1",
  "Sheet_Name_Max_Cell_Temperature": "1",
  "Sheet_Name_Min_Cell_Temperature": "1",
  "Sheet_Name_SOC": "1",
  "Sheet_Name_Temperature_Difference": "1"
};

/* ============================================================
   1️⃣ Fetch Current Thresholds
   ============================================================ */
async function loadThresholds() {
  try {
    const res = await BTS.apiFetch(`${BTS.API_BASE}/api/thresholds`);
    if (!res) return;
    const data = await res.json();
    // console.log(data);
    
    populateForm(data);
    populateHeadersForm(data["Headers"]);
  } catch (err) {
    console.error("Error loading thresholds:", err);
  }
}

/* ============================================================
   2️⃣ Populate Form Inputs
   ============================================================ */
function populateForm(data) {
  // take the data and extract uniques keys and accordinly populate the dropdowns and keep first dropdown selected
  const finaldata = data;
  data = data["Thresholds"];
  let dropdownOptions = new Set();
  dropdownOptions.add("Select Models");
  Object.keys(data).forEach(key => {
    dropdownOptions.add(key);
  });
  const dropdown = document.getElementById("modelSelect");
  dropdown.innerHTML = "";
  
  dropdownOptions.forEach((value, index) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    dropdown.appendChild(option);
  });
  // add the add new option at the end of the dropdown as it will be text and when selected it will open a prompt to add new model name and ask for password and accordingly add that model to the dropdown 
  const addNewOption = document.createElement("option");
  addNewOption.value = "add_new_model";
  addNewOption.textContent = "Add New Model";
  dropdown.appendChild(addNewOption);
  dropdown.value = dropdown.options[1].value; // select first model by default

  // add the event listener to dropdown to repopulate the form on change
  dropdown.addEventListener("change", (e) => {
    populateHeadersForm(finaldata["Headers"]);
    const selectedModel = e.target.value;
    // console.log(selectedModel);
    
    if (selectedModel === "add_new_model") {
      const newModelName = prompt("Enter new model name:");
      const password = prompt("Enter admin password to add new model:");
      if (password === "admin123" && newModelName) {
        // add new model to the dropdown
        const option = document.createElement("option");
        option.value = newModelName;
        option.textContent = newModelName;
        dropdown.insertBefore(option, addNewOption);
        dropdown.value = newModelName;
        // initialize the form with default thresholds
        populateForm({...data, [newModelName]: {"CDC": DEFAULT_THRESHOLDS, "Sanity": DEFAULT_THRESHOLDS}});
        alert(`New model "${newModelName}" added. Please set thresholds and save.`);
      } else {
        alert("Incorrect password or invalid model name. Cannot add new model.");
        dropdown.value = dropdown.options[1].value; // revert to first model
      }
      return;
    }
    try {
      const testtypeSelect = document.getElementById("testTypeSelect");
      const selectedTestType = testtypeSelect.value;
      const modelData = data[selectedModel];
      const finalData = modelData[selectedTestType];

      for (const mode of ["charge", "discharge"]) {    
        for (const [key, value] of Object.entries(finalData[mode])) {
          const inputName = `${mode}_${key.toLowerCase()}`;
          const input = form.querySelector(`[name="${inputName}"]`);
          if (input) {
            input.value = value;
          } else {
            console.warn(`Input not found for: ${inputName}`);
          }
        }
      }
    } catch (err) {
      console.error("Error populating form for selected model:", err);
    }
  });
  
  
  const model = dropdown.options[1].value; // select first model by default
  const modelData = data[model];
  const testtypeSelect = document.getElementById("testTypeSelect");
  const testType = testtypeSelect.options[0].value; // select first test type by default
  const finalData = modelData[testType];

  
  // add event listener to test type dropdown
  testtypeSelect.addEventListener("change", (e) => {
    populateHeadersForm(finaldata["Headers"]);
    const selectedTestType = e.target.value;
    const selectedModel = dropdown.value;
    const modelData = data[selectedModel];
    const finalData = modelData[selectedTestType];
    for (const mode of ["charge", "discharge"]) {
      for (const [key, value] of Object.entries(finalData[mode])) {
        const inputName = `${mode}_${key.toLowerCase()}`; 
        const input = form.querySelector(`[name="${inputName}"]`);
        if (input) {
          input.value = value;
        }
        else {
          console.warn(`Input not found for: ${inputName}`);
        }
      }
    }
  });
  for (const mode of ["charge", "discharge"]) {    
    for (const [key, value] of Object.entries(finalData[mode])) {
      const inputName = `${mode}_${key.toLowerCase()}`;
      const input = form.querySelector(`[name="${inputName}"]`);
      if (input) {
        input.value = value;
      } else {
        console.warn(`Input not found for: ${inputName}`);
      }
    }
  }
}

function populateHeadersForm(data) {
  // console.log(data);
  
  // read the model name and test type
  const modelSelect = document.getElementById("modelSelect");
  const selectedModel = modelSelect.value;
  const testtypeSelect = document.getElementById("testTypeSelect");
  const selectedTestType = testtypeSelect.value;
  const modelData = data[selectedModel];
  const finalData = modelData[selectedTestType]['header'];
  for (const [key, value] of Object.entries(finalData)) {
    const inputName = `header_${key.toLowerCase()}`;
    const input = formHeaders.querySelector(`[name="${inputName}"]`);
    if (input) {
      input.value = value || "";
    }
    else {
      console.warn(`Input not found for: ${inputName}`);
    }
  }
}

/* ============================================================
   3️⃣ Save Thresholds
   ============================================================ */
async function saveThresholds(e) {
  e.preventDefault();
  const modelSelect = document.getElementById("modelSelect");
  const selectedModel = modelSelect.value;
  const testtypeSelect = document.getElementById("testTypeSelect");
  const selectedTestType = testtypeSelect.value;
  
  const newThresholds = {};
 // ✅ ensure test type level exists
  if (!newThresholds[selectedModel]) {
    newThresholds[selectedModel] = {};
  }

  // ✅ ensure model level exists
  if (!newThresholds[selectedModel][selectedTestType]) {
    newThresholds[selectedModel][selectedTestType] = {};
  }

  for (const mode of ["charge", "discharge"]) {
    newThresholds[selectedModel][selectedTestType][mode] = {};
    for (const [key, _] of Object.entries(DEFAULT_THRESHOLDS[mode])) {
      const inputName = `${mode}_${key.toLowerCase()}`;
      const input = form.querySelector(`[name="${inputName}"]`);
      if (input) {
        newThresholds[selectedModel][selectedTestType][mode][key] = input.value;
      }
    }
  }
  console.log(newThresholds);
  
  try {
    const res = await BTS.apiFetch(`${BTS.API_BASE}/api/thresholds`, {
      method: "POST",
      headers: BTS.getAuthHeaders(),
      body: JSON.stringify(newThresholds),
    });

    if (res && res.ok) {
      const data = await res.json();
      alert("✅ Thresholds saved successfully!");
    } else {
      alert("⚠️ Failed to save thresholds.");
    }
  } catch (err) {
    console.error("Error saving thresholds:", err);
  }
}

async function saveHeaders(e) {
  e.preventDefault();
  const newHeaders = {};
  // read the model name and test type
  const modelSelect = document.getElementById("modelSelect");
  const selectedModel = modelSelect.value;
  const testtypeSelect = document.getElementById("testTypeSelect");
  const selectedTestType = testtypeSelect.value;
  if (!newHeaders[selectedModel]) {
    newHeaders[selectedModel] = {};
  }
  if (!newHeaders[selectedModel][selectedTestType]) {
    newHeaders[selectedModel][selectedTestType] = {};
  }
  newHeaders[selectedModel][selectedTestType]["header"] = {};

  // read the non-standard checkbox value
  const nonStandardCheckbox = document.querySelector('input[name="non-standard"]');
  newHeaders[selectedModel][selectedTestType]["non_standard"] = nonStandardCheckbox.checked ? 1 : 0;

  for (const [key, _] of Object.entries(DEFAULT_HEADERS)) {
    const inputName = `header_${key.toLowerCase()}`;
    const input = formHeaders.querySelector(`[name="${inputName}"]`);
    if (input) {
      newHeaders[selectedModel][selectedTestType]["header"][key] = input.value;
    }
  }
  // console.log(newHeaders);
  try {
    const res = await BTS.apiFetch(`${BTS.API_BASE}/api/headers`, {
      method: "POST",
      headers: BTS.getAuthHeaders(),
      body: JSON.stringify(newHeaders),
    });
    if (res && res.ok) {
      const data = await res.json();
      alert("✅ Headers saved successfully!");
    } else {
      alert("⚠️ Failed to save headers.");
    }
  } catch (err) {
    console.error("Error saving headers:", err);
  }
}
/* ============================================================
   4️⃣ Reset to Default Thresholds
   ============================================================ */
async function resetToDefaults() {
  if (!confirm("Reset to default safe limits?")) return;

  try {
    for (const mode of ["charge", "discharge"]) {    
    for (const [key, value] of Object.entries(DEFAULT_THRESHOLDS[mode])) {
      const inputName = `${mode}_${key.toLowerCase()}`;
      const input = form.querySelector(`[name="${inputName}"]`);
      if (input) {
        input.value = value;
      } else {
        console.warn(`Input not found for: ${inputName}`);
      }
    }
  }

  //   const res = await BTS.apiFetch(`${BTS.API_BASE}/api/thresholds`, {
  //     method: "POST",
  //     headers: BTS.getAuthHeaders(),
  //     body: JSON.stringify(DEFAULT_THRESHOLDS),
  //   });

  //   if (res && res.ok) {
  //     alert("✅ Thresholds reset to default values!");
  //   } else {
  //     alert("⚠️ Failed to reset thresholds.");
  //   }
  } catch (err) {
    console.error("Error resetting thresholds:", err);
  }
}


/* ============================================================
   6️⃣ Initialize Admin Page
   ============================================================ */
document.addEventListener("DOMContentLoaded", () => {
  if (!form) return;

  loadThresholds();

  form.addEventListener("submit", saveThresholds);
  formHeaders.addEventListener("submit", saveHeaders);
  resetBtn.addEventListener("click", resetToDefaults);
  resetHeadersBtn.addEventListener("click", () => {populateHeadersForm(DEFAULT_HEADERS)});
  const nonStandardCheckbox = document.querySelector('input[name="non-standard"]');
  nonStandardCheckbox.addEventListener("change", (e) => {
    const isChecked = e.target.checked;
    const headerCellDeviationInput = document.querySelector('input[name="header_cell_deviation"]');
    if (isChecked) {
      // disable header cell deviation input
      headerCellDeviationInput.disabled = true;
    }
    else {
      // enable header cell deviation input
      headerCellDeviationInput.disabled = false;
    }
  });
});
