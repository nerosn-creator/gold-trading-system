document.addEventListener("DOMContentLoaded", () => {
    let currentTf = "1h";
    let chartManager = null;

    // Initialize Chart
    if (typeof GoldChartManager !== "undefined") {
        chartManager = new GoldChartManager("candleChartContainer");
    }

    // Timeframe selector buttons
    const tfButtons = document.querySelectorAll(".tf-btn");
    tfButtons.forEach(btn => {
        btn.addEventListener("click", (e) => {
            tfButtons.forEach(b => b.classList.remove("active"));
            e.target.classList.add("active");
            currentTf = e.target.getAttribute("data-tf");
            loadDashboardData();
        });
    });

    // Refresh button
    const refreshBtn = document.getElementById("refreshBtn");
    if (refreshBtn) {
        refreshBtn.addEventListener("click", () => {
            loadDashboardData();
        });
    }

    // Toggle switches
    const toggleEMA = document.getElementById("toggleEMA");
    if (toggleEMA && chartManager) {
        toggleEMA.addEventListener("change", (e) => {
            chartManager.setEMAVisible(e.target.checked);
        });
    }

    const toggleBB = document.getElementById("toggleBB");
    if (toggleBB && chartManager) {
        toggleBB.addEventListener("change", (e) => {
            chartManager.setBBVisible(e.target.checked);
        });
    }

    const toggleSignals = document.getElementById("toggleSignals");
    if (toggleSignals) {
        toggleSignals.addEventListener("change", () => {
            loadDashboardData();
        });
    }

    // Backtest Button
    const runBacktestBtn = document.getElementById("runBacktestBtn");
    if (runBacktestBtn) {
        runBacktestBtn.addEventListener("click", () => {
            runBacktest();
        });
    }

    // AI Optimization Button
    const runOptimizeBtn = document.getElementById("runOptimizeBtn");
    if (runOptimizeBtn) {
        runOptimizeBtn.addEventListener("click", runAIOptimization);
    }

    // Paper Trading Elements
    const paperEquity = document.getElementById("paperEquity");
    const paperPnL = document.getElementById("paperPnL");
    const paperPositionBox = document.getElementById("paperPositionBox");
    const paperPosStatus = document.getElementById("paperPosStatus");

    const paperBuyBtn = document.getElementById("paperBuyBtn");
    const paperSellBtn = document.getElementById("paperSellBtn");
    const paperCloseBtn = document.getElementById("paperCloseBtn");
    const paperResetBtn = document.getElementById("paperResetBtn");
    const paperAmountOz = document.getElementById("paperAmountOz");
    const paperAmountMinus = document.getElementById("paperAmountMinus");
    const paperAmountPlus = document.getElementById("paperAmountPlus");

    if (paperBuyBtn) paperBuyBtn.addEventListener("click", () => placePaperTrade("BUY"));
    if (paperSellBtn) paperSellBtn.addEventListener("click", () => placePaperTrade("SELL"));
    if (paperCloseBtn) paperCloseBtn.addEventListener("click", () => closePaperTrade(null));
    if (paperResetBtn) paperResetBtn.addEventListener("click", resetPaperAccount);

    if (paperAmountMinus && paperAmountOz) {
        paperAmountMinus.addEventListener("click", () => {
            let val = parseFloat(paperAmountOz.value) || 1.0;
            val = Math.max(0.1, parseFloat((val - 0.5).toFixed(1)));
            paperAmountOz.value = val;
        });
    }

    if (paperAmountPlus && paperAmountOz) {
        paperAmountPlus.addEventListener("click", () => {
            let val = parseFloat(paperAmountOz.value) || 1.0;
            val = Math.min(100.0, parseFloat((val + 0.5).toFixed(1)));
            paperAmountOz.value = val;
        });
    }

    // Toggle Mode Button for First Bank Section
    const toggleQuoteViewBtn = document.getElementById("toggleQuoteViewBtn");
    const nativeQuoteBoard = document.getElementById("nativeQuoteBoard");
    const iframeQuoteWrapper = document.getElementById("iframeQuoteWrapper");
    const toggleQuoteModeText = document.getElementById("toggleQuoteModeText");

    if (toggleQuoteViewBtn && nativeQuoteBoard && iframeQuoteWrapper && toggleQuoteModeText) {
        toggleQuoteViewBtn.addEventListener("click", () => {
            if (iframeQuoteWrapper.style.display === "none") {
                iframeQuoteWrapper.style.display = "block";
                nativeQuoteBoard.style.display = "none";
                toggleQuoteModeText.textContent = "切換原生手機版";
            } else {
                iframeQuoteWrapper.style.display = "none";
                nativeQuoteBoard.style.display = "flex";
                toggleQuoteModeText.textContent = "切換原廠網頁";
            }
        });
    }

    // Event & News Tabs
    const tabCal = document.getElementById("tabCalendarBtn");
    const tabNw = document.getElementById("tabNewsBtn");
    const calContainer = document.getElementById("eventsTimelineContainer");
    const nwContainer = document.getElementById("liveNewsContainer");

    if (tabCal && tabNw && calContainer && nwContainer) {
        tabCal.addEventListener("click", () => {
            calContainer.style.display = "block";
            nwContainer.style.display = "none";
            tabCal.style.background = "rgba(255,215,0,0.15)";
            tabCal.style.color = "var(--gold-primary)";
            tabCal.style.borderColor = "var(--gold-primary)";
            tabNw.style.background = "rgba(255,255,255,0.05)";
            tabNw.style.color = "var(--text-muted)";
            tabNw.style.borderColor = "rgba(255,255,255,0.1)";
        });

        tabNw.addEventListener("click", () => {
            calContainer.style.display = "none";
            nwContainer.style.display = "block";
            tabNw.style.background = "rgba(41,98,255,0.2)";
            tabNw.style.color = "#82B1FF";
            tabNw.style.borderColor = "#82B1FF";
            tabCal.style.background = "rgba(255,255,255,0.05)";
            tabCal.style.color = "var(--text-muted)";
            tabCal.style.borderColor = "rgba(255,255,255,0.1)";
        });
    }

    // Initial Data Fetching
    loadDashboardData();
    loadPaperAccount();
    loadMacroLongTerm();
    loadDailyEvents();
    loadOptimizationStatus();
    loadFirstBankRates();
    loadSpotQuoteBoard();

    // Auto polling every 15 seconds
    setInterval(() => {
        loadDashboardData(true);
        loadPaperAccount();
        loadMacroLongTerm();
        loadDailyEvents();
        loadOptimizationStatus();
        loadFirstBankRates();
        loadSpotQuoteBoard();
    }, 15000);

    async function loadDashboardData(silent = false) {
        try {
            // Fetch candles & signal analysis
            const res = await fetch(`/api/gold/candles?symbol=XAUUSD&interval=${currentTf}`);
            const json = await res.json();
            
            if (json && json.data && chartManager) {
                try {
                    chartManager.updateData(json.data);
                } catch (e) {
                    console.warn("Chart rendering warning:", e);
                }
            }

            // Fetch latest summary
            const sumRes = await fetch(`/api/gold/summary?symbol=XAUUSD&interval=${currentTf}`);
            const summary = await sumRes.json();
            
            updateSummaryUI(summary);

        } catch (err) {
            console.error("Error fetching dashboard data:", err);
        }
    }

    async function loadFirstBankRates() {
        try {
            const res = await fetch("/api/gold/firstbank");
            const data = await res.json();
            
            if (!data) return;

            const fbGramSell = document.getElementById("fbGramSell");
            const fbGramBuy = document.getElementById("fbGramBuy");
            const fbUsdSell = document.getElementById("fbUsdSell");
            const fbUsdBuy = document.getElementById("fbUsdBuy");

            if (fbGramSell) {
                const usdOzSell = data.usd_gold_sell ? Number(data.usd_gold_sell).toFixed(2) : "0.00";
                fbGramSell.textContent = `NT$ ${data.gram_sell.toLocaleString()} / 公克 (1盎司: $${usdOzSell} 美元)`;
            }
            if (fbGramBuy) {
                const usdOzBuy = data.usd_gold_buy ? Number(data.usd_gold_buy).toFixed(2) : "0.00";
                fbGramBuy.textContent = `NT$ ${data.gram_buy.toLocaleString()} / 公克 (1盎司: $${usdOzBuy} 美元)`;
            }

            if (fbUsdSell && data.usd_spot_sell) fbUsdSell.textContent = data.usd_spot_sell.toFixed(3);
            if (fbUsdBuy && data.usd_spot_buy) fbUsdBuy.textContent = data.usd_spot_buy.toFixed(3);

        } catch (e) {
            console.error("Failed to load First Bank gold rates:", e);
        }
    }

    async function loadSpotQuoteBoard() {
        try {
            const res = await fetch("/api/gold/spot_quote");
            const data = await res.json();
            if (!data) return;

            const sqDate = document.getElementById("sqDate");
            const sqTime = document.getElementById("sqTime");
            const sqBuy = document.getElementById("sqBuy");
            const sqSell = document.getElementById("sqSell");
            const sqLast = document.getElementById("sqLast");
            const sqChange = document.getElementById("sqChange");
            const sqPrevClose = document.getElementById("sqPrevClose");
            const sqOpen = document.getElementById("sqOpen");
            const sqHigh = document.getElementById("sqHigh");
            const sqLow = document.getElementById("sqLow");

            const sqTwdOz = document.getElementById("sqTwdOz");
            const sqTwdChien = document.getElementById("sqTwdChien");
            const sqTwdGram = document.getElementById("sqTwdGram");
            const sqFutPrice = document.getElementById("sqFutPrice");
            const sqFutSpread = document.getElementById("sqFutSpread");

            if (sqDate) sqDate.textContent = data.date || "----/--/--";
            if (sqTime) sqTime.textContent = data.time || "--:--:--";
            if (sqBuy) sqBuy.textContent = `$${data.buy_price}`;
            if (sqSell) sqSell.textContent = `$${data.sell_price}`;
            if (sqLast) sqLast.textContent = `$${data.last_price}`;
            
            if (sqChange) {
                const isBull = data.change >= 0;
                const sign = isBull ? "▲" : "▼";
                const changeStr = `${sign} ${Math.abs(data.change).toFixed(2)} (${isBull ? "+" : ""}${data.change_pct}%)`;
                sqChange.textContent = changeStr;
                sqChange.className = `nq-val ${isBull ? "bullish" : "bearish"}`;
            }

            if (sqPrevClose) sqPrevClose.textContent = `$${data.prev_close}`;
            if (sqOpen) sqOpen.textContent = `$${data.open}`;
            if (sqHigh) sqHigh.textContent = `$${data.high}`;
            if (sqLow) sqLow.textContent = `$${data.low}`;

            if (sqTwdOz && data.twd_per_oz) sqTwdOz.textContent = `NT$ ${data.twd_per_oz}`;
            if (sqTwdChien && data.twd_per_chien) sqTwdChien.textContent = `NT$ ${data.twd_per_chien}`;
            if (sqTwdGram && data.twd_per_gram) sqTwdGram.textContent = `NT$ ${data.twd_per_gram}`;
            if (sqFutPrice && data.futures_gc1) sqFutPrice.textContent = `$${data.futures_gc1}`;
            if (sqFutSpread && data.spread_futures) {
                sqFutSpread.textContent = `${data.spread_futures}`;
                sqFutSpread.className = `tm-val ${parseFloat(data.spread_futures) >= 0 ? "bullish" : "bearish"}`;
            }

            if (data.trend_points && Array.isArray(data.trend_points)) {
                renderSpotTrendChart(data.trend_points);
            }
        } catch (err) {
            console.error("Error loading spot quote board:", err);
        }
    }

    function renderSpotTrendChart(points) {
        const canvas = document.getElementById("spotTrendCanvas");
        if (!canvas || !points || points.length < 2) return;
        
        const ctx = canvas.getContext("2d");
        const dpr = window.devicePixelRatio || 1;
        const rect = canvas.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return;
        
        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        ctx.scale(dpr, dpr);

        const width = rect.width;
        const height = rect.height;
        const padding = { top: 15, right: 60, bottom: 22, left: 10 };

        ctx.clearRect(0, 0, width, height);

        const prices = points.map(p => p.price);
        const minPrice = Math.min(...prices);
        const maxPrice = Math.max(...prices);
        const range = (maxPrice - minPrice) || 1;

        const isBullish = points[points.length - 1].price >= points[0].price;
        const strokeColor = isBullish ? "#00E676" : "#FF1744";
        const gradientStart = isBullish ? "rgba(0, 230, 118, 0.25)" : "rgba(255, 23, 68, 0.25)";
        const gradientEnd = "rgba(0, 0, 0, 0.0)";

        const chartWidth = width - padding.left - padding.right;
        const chartHeight = height - padding.top - padding.bottom;

        const getX = (idx) => padding.left + (idx / (points.length - 1)) * chartWidth;
        const getY = (price) => padding.top + chartHeight - ((price - minPrice) / range) * chartHeight;

        // Background grid lines & labels
        ctx.strokeStyle = "rgba(255, 255, 255, 0.05)";
        ctx.lineWidth = 1;
        ctx.font = "10px Outfit, sans-serif";
        ctx.fillStyle = "#9CA3AF";

        // Top line & label
        ctx.beginPath();
        ctx.moveTo(padding.left, getY(maxPrice));
        ctx.lineTo(width - padding.right, getY(maxPrice));
        ctx.stroke();
        ctx.fillText(`$${maxPrice.toFixed(2)}`, width - padding.right + 6, getY(maxPrice) + 3);

        // Bottom line & label
        ctx.beginPath();
        ctx.moveTo(padding.left, getY(minPrice));
        ctx.lineTo(width - padding.right, getY(minPrice));
        ctx.stroke();
        ctx.fillText(`$${minPrice.toFixed(2)}`, width - padding.right + 6, getY(minPrice) + 3);

        // Draw Fill Gradient
        const grad = ctx.createLinearGradient(0, padding.top, 0, height - padding.bottom);
        grad.addColorStop(0, gradientStart);
        grad.addColorStop(1, gradientEnd);

        ctx.beginPath();
        ctx.moveTo(getX(0), getY(points[0].price));
        for (let i = 1; i < points.length; i++) {
            ctx.lineTo(getX(i), getY(points[i].price));
        }
        ctx.lineTo(getX(points.length - 1), height - padding.bottom);
        ctx.lineTo(getX(0), height - padding.bottom);
        ctx.closePath();
        ctx.fillStyle = grad;
        ctx.fill();

        // Draw Smooth Trend Line
        ctx.beginPath();
        ctx.strokeStyle = strokeColor;
        ctx.lineWidth = 2;
        ctx.moveTo(getX(0), getY(points[0].price));
        for (let i = 1; i < points.length; i++) {
            ctx.lineTo(getX(i), getY(points[i].price));
        }
        ctx.stroke();

        // Draw Time labels
        ctx.fillStyle = "#6B7280";
        ctx.fillText(points[0].time, padding.left, height - 4);
        const midIdx = Math.floor(points.length / 2);
        ctx.fillText(points[midIdx].time, getX(midIdx) - 12, height - 4);
        ctx.fillText(points[points.length - 1].time, getX(points.length - 1) - 20, height - 4);

        // Draw Latest Price Pulsing Dot
        const lastX = getX(points.length - 1);
        const lastY = getY(points[points.length - 1].price);

        ctx.beginPath();
        ctx.arc(lastX, lastY, 4, 0, Math.PI * 2);
        ctx.fillStyle = strokeColor;
        ctx.fill();
        ctx.strokeStyle = "#FFFFFF";
        ctx.lineWidth = 1.5;
        ctx.stroke();
    }

    // ==========================================
    // Robust Paper Trading Engine (v3)
    // ==========================================
    const PAPER_STORAGE_KEY = "gold_paper_trading_account_v3";

    function getLocalPaperAccount() {
        try {
            const raw = localStorage.getItem(PAPER_STORAGE_KEY);
            if (raw) {
                const parsed = JSON.parse(raw);
                if (parsed && typeof parsed.cash === "number" && Array.isArray(parsed.positions)) {
                    return parsed;
                }
            }
        } catch (e) {
            console.warn("Error reading paper account from localStorage:", e);
        }
        return {
            initial_balance: 100000.0,
            cash: 100000.0,
            positions: [],
            trades: []
        };
    }

    function saveLocalPaperAccount(account) {
        try {
            localStorage.setItem(PAPER_STORAGE_KEY, JSON.stringify(account));
        } catch (e) {
            console.warn("Error saving paper account to localStorage:", e);
        }
    }

    function getPaperCurrentPrice() {
        if (window.currentGoldPrice && window.currentGoldPrice > 0) {
            return window.currentGoldPrice;
        }
        const heroSpotPrice = document.getElementById("heroSpotPrice");
        if (heroSpotPrice && heroSpotPrice.textContent) {
            const parsed = parseFloat(heroSpotPrice.textContent.replace(/[^0-9.]/g, ""));
            if (parsed > 0) return parsed;
        }
        const tickerPrice = document.getElementById("tickerPrice");
        if (tickerPrice && tickerPrice.textContent) {
            const parsed = parseFloat(tickerPrice.textContent.replace(/[^0-9.]/g, ""));
            if (parsed > 0) return parsed;
        }
        return 4450.0;
    }

    function loadPaperAccount() {
        try {
            const account = getLocalPaperAccount();
            const currentPrice = getPaperCurrentPrice();
            const positions = account.positions || [];

            let totalUnrealizedPnl = 0.0;
            let totalEntryValue = 0.0;

            positions.forEach(pos => {
                let posPnl = 0.0;
                if (pos.side === "BUY") {
                    posPnl = (currentPrice - pos.entry_price) * pos.amount_oz;
                } else {
                    posPnl = (pos.entry_price - currentPrice) * pos.amount_oz;
                }
                pos.currentPnl = posPnl;
                totalUnrealizedPnl += posPnl;
                totalEntryValue += pos.entry_price * pos.amount_oz;
            });

            const equity = account.cash + totalUnrealizedPnl;
            const pnlPct = totalEntryValue > 0 ? (totalUnrealizedPnl / totalEntryValue) * 100 : 0.0;

            if (paperEquity) {
                paperEquity.textContent = `$${equity.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
            }

            const sign = totalUnrealizedPnl >= 0 ? "+" : "";
            if (paperPnL) {
                paperPnL.textContent = `${sign}$${totalUnrealizedPnl.toFixed(2)} (${sign}${pnlPct.toFixed(2)}%)`;
                paperPnL.className = `p-val ${totalUnrealizedPnl > 0 ? "bullish" : (totalUnrealizedPnl < 0 ? "bearish" : "neutral")}`;
            }

            if (positions.length > 0 && paperPosStatus && paperPositionBox) {
                let htmlContent = "";
                positions.forEach((pos, idx) => {
                    const sideIsBuy = pos.side === "BUY";
                    const sideClass = sideIsBuy ? "buy" : "sell";
                    const sideText = sideIsBuy ? "多" : "空";
                    const pnlSign = pos.currentPnl >= 0 ? "+" : "";
                    const pnlClass = pos.currentPnl >= 0 ? "bullish" : "bearish";
                    const posId = pos.id || `pos_${idx}`;

                    htmlContent += `
                        <div class="paper-pos-item ${sideClass}">
                            <span class="pos-badge ${sideClass}">${sideText}</span>
                            <div class="pos-info-text">
                                <span>@ $${pos.entry_price.toFixed(2)} (${pos.amount_oz}oz)</span>
                                <span class="pos-pnl ${pnlClass}">${pnlSign}$${pos.currentPnl.toFixed(2)}</span>
                            </div>
                            <button type="button" class="pos-single-close-btn" onclick="window.closeSinglePaperPos('${posId}')" title="平掉此單">平倉</button>
                        </div>
                    `;
                });

                paperPosStatus.innerHTML = htmlContent;
                paperPositionBox.className = "paper-pos-box has-pos";
                if (paperCloseBtn) paperCloseBtn.disabled = false;
            } else if (paperPosStatus && paperPositionBox) {
                paperPosStatus.innerHTML = '<span style="color: var(--text-dim);">目前無持倉倉位</span>';
                paperPositionBox.className = "paper-pos-box empty";
                if (paperCloseBtn) paperCloseBtn.disabled = true;
            }
        } catch (e) {
            console.error("Failed to load paper account:", e);
        }
    }

    async function placePaperTrade(side) {
        try {
            const amountInput = document.getElementById("paperAmountOz");
            const amount = amountInput ? parseFloat(amountInput.value) || 1.0 : 1.0;
            if (amount <= 0) {
                alert("請輸入大於 0 的手數");
                return;
            }

            const currentPrice = getPaperCurrentPrice();
            const now = new Date();
            const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
            const dateStr = `${now.getFullYear()}/${(now.getMonth()+1).toString().padStart(2, '0')}/${now.getDate().toString().padStart(2, '0')} ${timeStr}`;

            const account = getLocalPaperAccount();
            if (!account.positions) account.positions = [];

            const newPos = {
                id: "pos_" + Date.now() + "_" + Math.floor(Math.random() * 1000),
                side: side.toUpperCase(),
                entry_price: currentPrice,
                amount_oz: amount,
                entry_time: dateStr,
                tp: side === "BUY" ? currentPrice * 1.02 : currentPrice * 0.98,
                sl: side === "BUY" ? currentPrice * 0.98 : currentPrice * 1.02
            };

            account.positions.push(newPos);
            saveLocalPaperAccount(account);
            loadPaperAccount();
        } catch (e) {
            console.error("Paper trade failed:", e);
        }
    }

    async function closePaperTrade(targetPosId = null) {
        try {
            const account = getLocalPaperAccount();
            let positions = account.positions || [];
            if (positions.length === 0) return;

            const exitPrice = getPaperCurrentPrice();
            const now = new Date();
            const exitTime = `${now.getFullYear()}/${(now.getMonth()+1).toString().padStart(2, '0')}/${now.getDate().toString().padStart(2, '0')} ${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;

            if (!account.trades) account.trades = [];

            if (targetPosId) {
                // Close single specific position
                const posIndex = positions.findIndex((p, idx) => (p.id === targetPosId || `pos_${idx}` === targetPosId));
                if (posIndex !== -1) {
                    const pos = positions[posIndex];
                    let profit = 0;
                    if (pos.side === "BUY") {
                        profit = (exitPrice - pos.entry_price) * pos.amount_oz;
                    } else {
                        profit = (pos.entry_price - exitPrice) * pos.amount_oz;
                    }

                    account.trades.push({
                        side: pos.side,
                        entry_time: pos.entry_time,
                        entry_price: pos.entry_price,
                        exit_time: exitTime,
                        exit_price: exitPrice,
                        amount_oz: pos.amount_oz,
                        profit: parseFloat(profit.toFixed(2)),
                        win: profit > 0
                    });

                    account.cash = parseFloat((account.cash + profit).toFixed(2));
                    positions.splice(posIndex, 1);
                }
            } else {
                // Close all positions
                let totalProfit = 0;
                positions.forEach(pos => {
                    let profit = 0;
                    if (pos.side === "BUY") {
                        profit = (exitPrice - pos.entry_price) * pos.amount_oz;
                    } else {
                        profit = (pos.entry_price - exitPrice) * pos.amount_oz;
                    }
                    totalProfit += profit;

                    account.trades.push({
                        side: pos.side,
                        entry_time: pos.entry_time,
                        entry_price: pos.entry_price,
                        exit_time: exitTime,
                        exit_price: exitPrice,
                        amount_oz: pos.amount_oz,
                        profit: parseFloat(profit.toFixed(2)),
                        win: profit > 0
                    });
                });

                account.cash = parseFloat((account.cash + totalProfit).toFixed(2));
                positions = [];
            }

            account.positions = positions;
            saveLocalPaperAccount(account);
            loadPaperAccount();
        } catch (e) {
            console.error("Paper close failed:", e);
        }
    }

    // Expose close single position function to global window for onclick handler
    window.closeSinglePaperPos = function(id) {
        closePaperTrade(id);
    };

    async function resetPaperAccount() {
        try {
            if (!confirm("確定要重置模擬交易帳戶？資金將恢復為 $100,000 USD 並清空所有持倉。")) {
                return;
            }
            const defaultAccount = {
                initial_balance: 100000.0,
                cash: 100000.0,
                positions: [],
                trades: []
            };
            saveLocalPaperAccount(defaultAccount);
            loadPaperAccount();
        } catch (e) {
            console.error("Paper reset failed:", e);
        }
    }

    function updateSummaryUI(summary) {
        if (!summary || !summary.current_price) return;
        window.currentGoldPrice = summary.current_price;
        loadPaperAccount();

        // Update Live Gold Price Hero Banner
        const heroSpotPrice = document.getElementById("heroSpotPrice");
        const heroPriceChange = document.getElementById("heroPriceChange");
        const heroOpen = document.getElementById("heroOpen");
        const heroHigh = document.getElementById("heroHigh");
        const heroLow = document.getElementById("heroLow");
        const heroRange = document.getElementById("heroRange");

        if (heroSpotPrice) heroSpotPrice.textContent = `$${summary.current_price.toFixed(2)}`;

        const chg = summary.price_change || 0;
        const pct = summary.price_change_pct || 0;
        const sign = chg >= 0 ? "+" : "";

        if (heroPriceChange) {
            heroPriceChange.textContent = `${sign}${chg.toFixed(2)} (${sign}${pct.toFixed(2)}%)`;
            heroPriceChange.className = `hero-change-badge ${chg > 0 ? "bullish" : (chg < 0 ? "bearish" : "neutral")}`;
        }

        if (heroOpen) heroOpen.textContent = summary.open ? `$${summary.open.toFixed(2)}` : `$${summary.current_price.toFixed(2)}`;
        if (heroHigh) heroHigh.textContent = summary.high ? `$${summary.high.toFixed(2)}` : `$${summary.current_price.toFixed(2)}`;
        if (heroLow) heroLow.textContent = summary.low ? `$${summary.low.toFixed(2)}` : `$${summary.current_price.toFixed(2)}`;

        if (heroRange && summary.high && summary.low) {
            const range = summary.high - summary.low;
            heroRange.textContent = `$${range.toFixed(2)}`;
        }

        // Ticker
        const tickerPrice = document.getElementById("tickerPrice");
        const tickerChange = document.getElementById("tickerChange");
        
        if (tickerPrice) tickerPrice.textContent = `$${summary.current_price.toFixed(2)}`;
        if (tickerChange) {
            tickerChange.textContent = `${sign}${chg.toFixed(2)} (${sign}${pct.toFixed(2)}%)`;
            tickerChange.className = `ticker-change ${chg > 0 ? "bullish" : (chg < 0 ? "bearish" : "neutral")}`;
        }

        // Signal Badge
        const signalBadge = document.getElementById("signalBadge");
        const signalScore = document.getElementById("signalScore");
        const signalTime = document.getElementById("signalTime");

        if (signalBadge) {
            signalBadge.textContent = getChineseSignalText(summary.signal_type);
            signalBadge.className = `signal-badge ${summary.signal_type}`;
        }

        if (signalScore) signalScore.textContent = `${summary.signal_score > 0 ? "+" : ""}${summary.signal_score}`;
        if (signalTime) signalTime.textContent = `更新時間: ${summary.timestamp ? (summary.timestamp.split(" ")[1] || summary.timestamp) : "--:--"}`;

        // TP / SL
        const tpPrice = document.getElementById("tpPrice");
        const slPrice = document.getElementById("slPrice");
        if (tpPrice && summary.take_profit) tpPrice.textContent = `$${summary.take_profit.toFixed(2)}`;
        if (slPrice && summary.stop_loss) slPrice.textContent = `$${summary.stop_loss.toFixed(2)}`;

        // Indicators Monitor
        const rsiValue = document.getElementById("rsiValue");
        const macdValue = document.getElementById("macdValue");
        const atrValue = document.getElementById("atrValue");
        const emaRatio = document.getElementById("emaRatio");

        if (rsiValue) rsiValue.textContent = summary.rsi_14;
        if (macdValue) macdValue.textContent = summary.macd_hist;
        if (atrValue) atrValue.textContent = summary.atr_14;
        if (emaRatio) emaRatio.textContent = `${summary.ema_9} / ${summary.ema_50}`;

        // Reasons List
        const reasonsList = document.getElementById("reasonsList");
        if (reasonsList) {
            reasonsList.innerHTML = "";
            if (summary.reasons && summary.reasons.length > 0) {
                summary.reasons.forEach(r => {
                    const li = document.createElement("li");
                    li.textContent = r;
                    reasonsList.appendChild(li);
                });
            } else {
                const li = document.createElement("li");
                li.textContent = "多空指標力道均衡，無顯著突破條件。";
                reasonsList.appendChild(li);
            }
        }
    }

    function getChineseSignalText(sigType) {
        switch (sigType) {
            case "STRONG_BUY": return "強烈買進 (Strong Buy)";
            case "BUY": return "買進 (Buy)";
            case "NEUTRAL": return "觀望 (Neutral)";
            case "SELL": return "賣出 (Sell)";
            case "STRONG_SELL": return "強烈賣出 (Strong Sell)";
            default: return sigType;
        }
    }

    async function runBacktest() {
        try {
            const btn = document.getElementById("runBacktestBtn");
            if (btn) btn.textContent = "計算中...";
            const res = await fetch(`/api/gold/backtest?symbol=XAUUSD&interval=${currentTf}`);
            const result = await res.json();
            
            const btWinRate = document.getElementById("btWinRate");
            const btReturn = document.getElementById("btReturn");
            const btPF = document.getElementById("btPF");
            const btMDD = document.getElementById("btMDD");

            if (btWinRate) btWinRate.textContent = `${result.win_rate_pct}%`;
            if (btReturn) btReturn.textContent = `${result.total_return_pct > 0 ? "+" : ""}${result.total_return_pct}%`;
            if (btPF) btPF.textContent = result.profit_factor;
            if (btMDD) btMDD.textContent = `-${result.max_drawdown_pct}%`;

            if (btn) {
                btn.innerHTML = '<i class="fa-solid fa-check"></i> 完成';
                setTimeout(() => {
                    btn.innerHTML = '<i class="fa-solid fa-play"></i> 執行回測';
                }, 2000);
            }
        } catch (err) {
            console.error("Backtest failed:", err);
            const btn = document.getElementById("runBacktestBtn");
            if (btn) btn.innerHTML = '<i class="fa-solid fa-play"></i> 執行回測';
        }
    }

    async function loadMacroLongTerm() {
        try {
            const res = await fetch("/api/gold/longterm");
            const data = await res.json();
            
            if (!data || data.status === "ERROR") return;

            const ratingEl = document.getElementById("macroRatingText");
            const zoneEl = document.getElementById("macroAccumulateZone");
            const target3MEl = document.getElementById("macroTarget3M");
            const target6MEl = document.getElementById("macroTarget6M");
            const sma200El = document.getElementById("macroSMA200");

            if (ratingEl) ratingEl.textContent = data.rating_text;
            if (zoneEl) zoneEl.textContent = data.accumulate_zone;
            if (target3MEl) target3MEl.textContent = `$${data.target_3m.toFixed(2)}`;
            if (target6MEl) target6MEl.textContent = `$${data.target_6m.toFixed(2)}`;
            if (sma200El) sma200El.textContent = `$${data.sma_200.toFixed(2)}`;

            // Technical proofs list
            const proofsList = document.getElementById("macroProofsList");
            if (proofsList && data.technical_proofs) {
                proofsList.innerHTML = "";
                data.technical_proofs.forEach(pf => {
                    const li = document.createElement("li");
                    li.textContent = pf;
                    proofsList.appendChild(li);
                });
            }

        } catch (e) {
            console.error("Failed to load long-term macro strategy:", e);
        }
    }

    async function loadDailyEvents() {
        try {
            const res = await fetch("/api/gold/events");
            const data = await res.json();
            
            if (!data) return;

            // Date & Live Sync Indicator
            const updateDateEl = document.getElementById("eventUpdateDate");
            if (updateDateEl && data.date) {
                updateDateEl.textContent = `📅 ${data.date}`;
            }

            // Macro Sentiment Tag
            const sentimentTag = document.getElementById("eventSentimentTag");
            if (sentimentTag && data.macro_sentiment) {
                sentimentTag.textContent = data.macro_sentiment.sentiment_label;
            }

            // Key Drivers List
            const driversList = document.getElementById("driversList");
            if (driversList && data.macro_sentiment && data.macro_sentiment.key_drivers) {
                driversList.innerHTML = "";
                data.macro_sentiment.key_drivers.forEach(d => {
                    const li = document.createElement("li");
                    li.textContent = d;
                    driversList.appendChild(li);
                });
            }

            // Events Timeline List
            const eventsList = document.getElementById("eventsList");
            if (eventsList && data.events) {
                eventsList.innerHTML = "";
                data.events.forEach(ev => {
                    const li = document.createElement("li");
                    li.className = `event-item ${ev.impact}`;
                    li.innerHTML = `
                        <div class="event-top">
                            <span class="event-time"><i class="fa-regular fa-clock"></i> ${ev.time}</span>
                            <span class="event-impact ${ev.impact}">${ev.impact === 'HIGH' ? '🔴 重大' : '🟡 中等'}</span>
                        </div>
                        <div class="event-title">${ev.title}</div>
                        <div class="event-vals">
                            <span>預期: <strong>${ev.forecast}</strong></span>
                            <span>前值: <strong>${ev.previous}</strong></span>
                        </div>
                        <div class="event-analysis">${ev.analysis}</div>
                    `;
                    eventsList.appendChild(li);
                });
            }

            // Live News List
            const liveNewsList = document.getElementById("liveNewsList");
            if (liveNewsList && data.live_news) {
                liveNewsList.innerHTML = "";
                if (data.live_news.length === 0) {
                    liveNewsList.innerHTML = "<li style='color:var(--text-muted); font-size:11px;'>暫無即時快訊，請稍候重新載入</li>";
                } else {
                    data.live_news.forEach(nw => {
                        const li = document.createElement("li");
                        li.className = "event-item";
                        li.style.borderLeftColor = "var(--accent-blue, #2962FF)";
                        li.innerHTML = `
                            <div class="event-top">
                                <span class="event-time" style="color:var(--gold-primary); font-weight:600;"><i class="fa-solid fa-bolt"></i> ${nw.source || '即時快訊'}</span>
                                <span class="event-time">${nw.pub_date ? nw.pub_date.slice(0, 16) : ''}</span>
                            </div>
                            <a href="${nw.link || '#'}" target="_blank" rel="noopener noreferrer" style="color:var(--text-primary); font-size:11px; line-height:1.4; font-weight:600; text-decoration:none; margin: 2px 0; display:block;">
                                ${nw.title} <i class="fa-solid fa-arrow-up-right-from-square" style="font-size:9px; opacity:0.6; margin-left:2px;"></i>
                            </a>
                        `;
                        liveNewsList.appendChild(li);
                    });
                }
            }

        } catch (e) {
            console.error("Failed to load daily events:", e);
        }
    }

    async function loadOptimizationStatus() {
        try {
            const res = await fetch("/api/gold/optimize_status");
            const data = await res.json();
            
            if (!data) return;

            const genBadge = document.getElementById("aiGenBadge");
            const winRateEl = document.getElementById("aiEvolvedWinRate");
            const wEMA = document.getElementById("wEMA");
            const wMACD = document.getElementById("wMACD");
            const wRSI = document.getElementById("wRSI");
            const wADX = document.getElementById("wADX");

            if (genBadge) genBadge.textContent = `Gen ${data.generation || 1} 自適應優化`;
            if (winRateEl) winRateEl.textContent = `${(data.win_rate_pct || 54.17).toFixed(2)}%`;
            if (wEMA) wEMA.textContent = `${data.ema_weight || 30}%`;
            if (wMACD) wMACD.textContent = `${data.macd_weight || 25}%`;
            if (wRSI) wRSI.textContent = `${data.rsi_weight || 20}%`;
            if (wADX) wADX.textContent = `${data.adx_threshold || 20}`;

        } catch (e) {
            console.error("Failed to load optimization status:", e);
        }
    }

    async function runAIOptimization() {
        try {
            const btn = document.getElementById("runOptimizeBtn");
            if (btn) btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 進化中...';
            
            const res = await fetch("/api/gold/optimize", { method: "POST" });
            const data = await res.json();

            loadOptimizationStatus();
            loadDashboardData();

            if (btn) {
                btn.innerHTML = '<i class="fa-solid fa-check"></i> 已升級進化';
                setTimeout(() => {
                    btn.innerHTML = '<i class="fa-solid fa-bolt"></i> 啟動 AI 權重進化';
                }, 2000);
            }
        } catch (e) {
            console.error("AI Optimization failed:", e);
        }
    }
});
