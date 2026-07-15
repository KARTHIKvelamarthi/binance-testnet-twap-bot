document.addEventListener("DOMContentLoaded", () => {
    // State Variables
    let selectedSide = "BUY";
    let selectedType = "MARKET";

    // DOM Elements - Views
    const formView = document.getElementById("form-view");
    const confirmView = document.getElementById("confirm-view");
    const resultView = document.getElementById("result-view");

    // DOM Elements - Form Inputs
    const orderForm = document.getElementById("order-form");
    const symbolInput = document.getElementById("symbol");
    const quantityInput = document.getElementById("quantity");
    const priceInput = document.getElementById("price");
    const durationInput = document.getElementById("duration");
    const slicesInput = document.getElementById("slices");

    // DOM Elements - Selectors
    const buyBtn = document.getElementById("side-buy-btn");
    const sellBtn = document.getElementById("side-sell-btn");
    const tabBtns = document.querySelectorAll(".tab-btn");
    const conditionalFields = document.getElementById("conditional-fields");
    const priceGroup = document.getElementById("price-group");
    const twapGroup = document.getElementById("twap-group");

    // DOM Elements - Confirmation Summary
    const summarySymbol = document.getElementById("summary-symbol");
    const summarySide = document.getElementById("summary-side");
    const summaryType = document.getElementById("summary-type");
    const summaryQuantity = document.getElementById("summary-quantity");
    const summaryPrice = document.getElementById("summary-price");
    const summaryTwap = document.getElementById("summary-twap");
    const summaryPriceRow = document.getElementById("summary-price-row");
    const summaryTwapRow = document.getElementById("summary-twap-row");

    // DOM Elements - Confirmation Actions
    const confirmCancelBtn = document.getElementById("confirm-cancel-btn");
    const confirmSubmitBtn = document.getElementById("confirm-submit-btn");

    // DOM Elements - Result & Recent Orders
    const resultContent = document.getElementById("result-content");
    const resultResetBtn = document.getElementById("result-reset-btn");
    const recentOrdersList = document.getElementById("recent-orders-list");

    // Initial load
    loadRecentOrders();

    // 1. Side Selection Toggle
    buyBtn.addEventListener("click", () => setSide("BUY"));
    sellBtn.addEventListener("click", () => setSide("SELL"));

    function setSide(side) {
        selectedSide = side;
        if (side === "BUY") {
            buyBtn.classList.add("active");
            sellBtn.classList.remove("active");
        } else {
            sellBtn.classList.add("active");
            buyBtn.classList.remove("active");
        }
    }

    // 2. Order Type Tab Selection
    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            tabBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            setType(btn.getAttribute("data-type"));
        });
    });

    function setType(type) {
        selectedType = type;
        
        // Hide all conditional input groups first
        priceGroup.classList.add("hidden");
        twapGroup.classList.add("hidden");

        if (type === "LIMIT") {
            priceGroup.classList.remove("hidden");
            conditionalFields.classList.add("visible");
            priceInput.setAttribute("required", "true");
            durationInput.removeAttribute("required");
            slicesInput.removeAttribute("required");
        } else if (type === "TWAP") {
            twapGroup.classList.remove("hidden");
            conditionalFields.classList.add("visible");
            priceInput.removeAttribute("required");
            durationInput.setAttribute("required", "true");
            slicesInput.setAttribute("required", "true");
        } else {
            // MARKET
            conditionalFields.classList.remove("visible");
            priceInput.removeAttribute("required");
            durationInput.removeAttribute("required");
            slicesInput.removeAttribute("required");
        }
    }

    // 3. Form Submission - Show Confirmation Summary
    orderForm.addEventListener("submit", (e) => {
        e.preventDefault();
        
        // Clear previous error styles
        clearInputErrors();

        // Perform validation
        const isValid = validateFormFields();
        if (!isValid) return;

        // Transition to Confirmation View
        showView(confirmView);

        // Populate Confirmation Card
        summarySymbol.textContent = symbolInput.value.trim().toUpperCase();
        summarySide.textContent = selectedSide;
        
        // Dynamic colors for BUY/SELL labels
        summarySide.className = "summary-value side-label " + (selectedSide === "BUY" ? "buy" : "sell");
        summaryType.textContent = selectedType;
        summaryQuantity.textContent = parseFloat(quantityInput.value).toFixed(4);

        if (selectedType === "LIMIT") {
            summaryPriceRow.style.display = "flex";
            summaryTwapRow.style.display = "none";
            summaryPrice.textContent = parseFloat(priceInput.value).toFixed(2) + " USDT";
        } else if (selectedType === "TWAP") {
            summaryPriceRow.style.display = "none";
            summaryTwapRow.style.display = "flex";
            summaryTwap.textContent = `${durationInput.value}s / ${slicesInput.value} slices`;
        } else {
            summaryPriceRow.style.display = "none";
            summaryTwapRow.style.display = "none";
        }
    });

    // 4. Confirmation Controls
    confirmCancelBtn.addEventListener("click", () => {
        showView(formView);
    });

    confirmSubmitBtn.addEventListener("click", async () => {
        // Disable submission button during request
        confirmSubmitBtn.disabled = true;
        confirmSubmitBtn.textContent = "Submitting Order...";

        const payload = {
            symbol: symbolInput.value.trim().toUpperCase(),
            side: selectedSide,
            order_type: selectedType,
            quantity: parseFloat(quantityInput.value),
            price: selectedType === "LIMIT" ? parseFloat(priceInput.value) : null,
            duration: selectedType === "TWAP" ? parseInt(durationInput.value) : null,
            slices: selectedType === "TWAP" ? parseInt(slicesInput.value) : null
        };

        try {
            const response = await fetch("/api/order", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            const result = await response.json();

            if (response.ok && result.success) {
                renderResult(true, result);
            } else {
                renderResult(false, result);
            }
        } catch (error) {
            renderResult(false, { error_message: "Network connection lost or backend is offline." });
        } finally {
            confirmSubmitBtn.disabled = false;
            confirmSubmitBtn.textContent = "Confirm & Submit";
            showView(resultView);
        }
    });

    // 5. Result Reset Controls
    resultResetBtn.addEventListener("click", () => {
        // Reset volatile fields only, keep symbol and side for ease of reuse
        quantityInput.value = "";
        priceInput.value = "";
        durationInput.value = "";
        slicesInput.value = "";
        
        clearInputErrors();
        showView(formView);
    });

    // Helper functions
    function showView(viewElement) {
        [formView, confirmView, resultView].forEach(v => {
            v.classList.remove("active");
        });
        viewElement.classList.add("active");
    }

    function clearInputErrors() {
        document.querySelectorAll("input").forEach(inp => {
            inp.classList.remove("input-error");
            const errText = inp.parentNode.querySelector(".error-text");
            if (errText) errText.remove();
        });
    }

    function addInputError(inputEl, message) {
        inputEl.classList.add("input-error");
        const err = document.createElement("div");
        err.className = "error-text";
        err.textContent = message;
        inputEl.parentNode.appendChild(err);
    }

    function validateFormFields() {
        let isValid = true;

        if (!symbolInput.value.trim()) {
            addInputError(symbolInput, "Symbol is required.");
            isValid = false;
        }

        const qtyVal = parseFloat(quantityInput.value);
        if (isNaN(qtyVal) || qtyVal <= 0) {
            addInputError(quantityInput, "Quantity must be a positive number.");
            isValid = false;
        }

        if (selectedType === "LIMIT") {
            const prVal = parseFloat(priceInput.value);
            if (isNaN(prVal) || prVal <= 0) {
                addInputError(priceInput, "Price is required and must be positive.");
                isValid = false;
            }
        }

        if (selectedType === "TWAP") {
            const durVal = parseInt(durationInput.value);
            const slVal = parseInt(slicesInput.value);

            if (isNaN(durVal) || durVal <= 0) {
                addInputError(durationInput, "Duration is required and must be positive.");
                isValid = false;
            }
            if (isNaN(slVal) || slVal <= 0) {
                addInputError(slicesInput, "Slices is required and must be positive.");
                isValid = false;
            }
            if (!isNaN(durVal) && !isNaN(slVal) && durVal < slVal) {
                addInputError(durationInput, "Duration must be >= slices count.");
                isValid = false;
            }
        }

        return isValid;
    }

    function renderResult(isSuccess, data) {
        if (isSuccess) {
            resultContent.innerHTML = `
                <div class="result-card success">
                    <div class="result-icon">✓</div>
                    <h3>Order Successful</h3>
                    <p>Order executed successfully on the exchange.</p>
                    <div class="summary-card">
                        <div class="summary-row">
                            <span class="summary-label">Order ID</span>
                            <span class="summary-value">${data.order_id}</span>
                        </div>
                        <div class="summary-row">
                            <span class="summary-label">Status</span>
                            <span class="summary-value">${data.status}</span>
                        </div>
                        <div class="summary-row">
                            <span class="summary-label">Executed Qty</span>
                            <span class="summary-value">${data.executed_qty}</span>
                        </div>
                        <div class="summary-row">
                            <span class="summary-label">Avg Price</span>
                            <span class="summary-value">${data.avg_price}</span>
                        </div>
                    </div>
                </div>
            `;
        } else {
            const errMsg = data.detail || data.error_message || "An unexpected error occurred.";
            resultContent.innerHTML = `
                <div class="result-card failure">
                    <div class="result-icon">✗</div>
                    <h3>Order Failed</h3>
                    <p>The exchange or validator rejected this order request.</p>
                    <div class="summary-card" style="border-color: rgba(239, 68, 68, 0.3);">
                        <div class="summary-row" style="border-bottom: none; flex-direction: column; align-items: flex-start; gap: 8px;">
                            <span class="summary-label">Error Reason</span>
                            <span class="summary-value" style="color: var(--sell-red); word-break: break-all; text-align: left;">
                                ${errMsg}
                            </span>
                        </div>
                    </div>
                </div>
            `;
        }
        
        // Refresh recent orders
        loadRecentOrders();
    }

    async function loadRecentOrders() {
        try {
            const response = await fetch("/api/recent-orders");
            if (!response.ok) throw new Error("API call failed");
            
            const orders = await response.json();
            
            if (orders.length === 0) {
                recentOrdersList.innerHTML = `
                    <tr class="empty-row">
                        <td colspan="6">No recent orders found.</td>
                    </tr>
                `;
                return;
            }

            recentOrdersList.innerHTML = orders.map(ord => {
                const sideClass = ord.side.toLowerCase() === "buy" ? "buy" : "sell";
                let statusClass = "new";
                if (ord.status === "FILLED") statusClass = "filled";
                if (ord.status === "REJECTED") statusClass = "rejected";
                if (ord.status === "PARTIALLY_FILLED") statusClass = "partially_filled";

                return `
                    <tr>
                        <td>${ord.timestamp}</td>
                        <td style="font-weight: 600;">${ord.symbol}</td>
                        <td><span class="side-badge ${sideClass}">${ord.side}</span></td>
                        <td>${ord.type}</td>
                        <td><span class="status-badge ${statusClass}">${ord.status}</span></td>
                        <td style="color: var(--text-muted); font-size: 11px;">${ord.details}</td>
                    </tr>
                `;
            }).join("");

        } catch (error) {
            recentOrdersList.innerHTML = `
                <tr class="empty-row">
                    <td colspan="6" style="color: var(--sell-red);">Failed to retrieve recent orders list.</td>
                </tr>
            `;
        }
    }
});
