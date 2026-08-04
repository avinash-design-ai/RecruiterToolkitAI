document.addEventListener("DOMContentLoaded", () => {

    //------------------------------------------------------
    // CITY SEARCH
    //------------------------------------------------------

    const wageForm = document.getElementById("wageForm");

    if (wageForm) {

        const cityInput = document.getElementById("city");
        const loading = document.getElementById("loading");
        const results = document.getElementById("results");
        const submitButton = wageForm.querySelector("button");

        wageForm.addEventListener("submit", async (e) => {

            e.preventDefault();

            const city = cityInput.value.trim();

            if (!city) {
                alert("Please enter a city.");
                cityInput.focus();
                return;
            }

            submitButton.disabled = true;
            submitButton.innerHTML = "Searching...";

            loading.style.display = "block";
            results.innerHTML = "";

            try {

                const response = await fetch("/wage", {

                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify({
                        city: city
                    })

                });

                const data = await response.json();

                loading.style.display = "none";

                if (!response.ok) {

                    results.innerHTML = `
                        <div class="alert alert-danger">
                            ${data.detail || "Unable to retrieve wages."}
                        </div>
                    `;

                    return;

                }

                let html = `
                    <div class="alert alert-primary">
                        <h4>📍 ${data.county}</h4>
                        <strong>State:</strong> ${data.state}
                    </div>

                    <div class="row">
                `;

                for (const key in data) {

                    if (key === "county" || key === "state")
                        continue;

                    html += `
                        <div class="col-lg-6 col-xl-3 mb-4">

                            <div class="card shadow h-100">

                                <div class="card-body">

                                    <h5>${key}</h5>

                                    <hr>

                                    <small>Hourly Wage</small>

                                    <div class="text-success fw-bold">

                                        ${data[key].hourly}

                                    </div>

                                    <br>

                                    <small>Annual Wage</small>

                                    <div class="text-primary fw-bold">

                                        ${data[key].annual}

                                    </div>

                                </div>

                            </div>

                        </div>
                    `;

                }

                html += "</div>";

                results.innerHTML = html;

            }

            catch (err) {

                loading.style.display = "none";

                results.innerHTML = `
                    <div class="alert alert-danger">
                        ${err.message}
                    </div>
                `;

            }

            finally {

                submitButton.disabled = false;
                submitButton.innerHTML = "Get Wages";

            }

        });

    }

    //------------------------------------------------------
    // EXCEL UPLOAD
    //------------------------------------------------------

    const excelForm = document.getElementById("excelForm");

    if (excelForm) {

        excelForm.addEventListener("submit", async (e) => {

            e.preventDefault();

            const fileInput = document.getElementById("excelFile");
            const excelResults = document.getElementById("excelResults");

            if (fileInput.files.length === 0) {

                alert("Please choose an Excel file.");

                return;

            }

            const formData = new FormData();

            formData.append(
                "file",
                fileInput.files[0]
            );

            excelResults.innerHTML = `
                <div class="alert alert-info">

                    <div class="spinner-border spinner-border-sm"></div>

                    Processing Excel...

                </div>
            `;

            try {

                const response = await fetch("/wage/excel", {

                    method: "POST",

                    body: formData

                });

                const data = await response.json();

                if (!response.ok) {

                    excelResults.innerHTML = `
                        <div class="alert alert-danger">

                            Failed to process Excel.

                        </div>
                    `;

                    return;

                }

                excelResults.innerHTML = `
                    <div class="alert alert-success">

                        <h5>

                            ✅ Excel processed successfully

                        </h5>

                        <p>

                            Click below to download the updated file.

                        </p>

                        <a
                            class="btn btn-success"
                            href="/wage/download/${encodeURIComponent(data.filename)}">

                            ⬇ Download Updated Excel

                        </a>

                    </div>
                `;

            }

            catch (err) {

                excelResults.innerHTML = `
                    <div class="alert alert-danger">

                        ${err.message}

                    </div>
                `;

            }

        });

    }

});