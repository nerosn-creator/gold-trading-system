document.addEventListener("DOMContentLoaded", () => {
    let currentTf = "1h";
    let chartManager = null;

    // Initialize Chart
    chartManager = new GoldChartManager("candleChartContainer");

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
    document.getElementById("toggleEMA").addEventListener("change", (e) => {
        chartManager.setEMAVisible(e.target.checked);
    });

    document.getElementById("toggleBB").addEventListener("change", (e) => {
        chartManager.setBBVisible(e.target.checked);
    });

    document.getElementById("toggleSignals").addEventListener("change", () => {
        loadDashboardData();
    });

    // Backtest Button
    document.getElementById("runBacktestBtn").addEventListener("click", () => {
        runBacktest();
    });

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

    if (paperBuyBtn) paperBuyBtn.addEventListener("click", () => placePaperTrade("BUY"));
    if (paperSellBtn) paperSellBtn.addEventListener("click", () => placePaperTrade("SELL"));
    if (paperCloseBtn) paperCloseBtn.addEventListener("click", closePaperTrade);
    if (paperResetBtn) paperResetBtn.addEventListener("click", resetPaperAccount);

    // Toggle Mode Button for First Bank Section
    const toggleQuoteViewBtn = document.getElementById("toggleQuoteViewBtn");
    const nativeQuoteBoard = document.getElementById("nativeQuoteBoard");
    const iframeQuoteWrapper = document.getElementById("iframeQuoteWrapper");
    const toggleQuoteModeText = document.getElementById("toggleQuoteModeText");

    if (toggleQuoteViewBtn) {
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


    async function loadPaperAccount() {
        try {
            const res = await fetch("/api/paper/account");
            const data = await res.json();
            
            if (paperEquity) paperEquity.textContent = `$${data.equity.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
            
            const pnl = data.unrealized_pnl || 0;
            const pnlPct = data.unrealized_pnl_pct || 0;
            const sign = pnl >= 0 ? "+" : "";
            if (paperPnL) {
                paperPnL.textContent = `${sign}$${pnl.toFixed(2)} (${sign}${pnlPct.toFixed(2)}%)`;
                paperPnL.className = `p-val ${pnl > 0 ? "bullish" : (pnl < 0 ? "bearish" : "neutral")}`;
            }

            const positions = data.positions || (data.position ? [data.position] : []);
            
            if (positions.length > 0 && paperPosStatus && paperPositionBox) {
                let htmlContent = "";
                let hasBuy = false;
                let hasSell = false;
                
                positions.forEach((pos, idx) => {
                    const sideText = pos.side === "BUY" ? "做多 (BUY)" : "做空 (SELL)";
                    const sideClass = pos.side === "BUY" ? "active-buy" : "active-sell";
                    if (pos.side === "BUY") hasBuy = true;
                    if (pos.side === "SELL") hasSell = true;
                    
                    htmlContent += `<div style="margin-bottom: 4px;"><strong>${sideText}</strong> @ $${pos.entry_price.toFixed(2)} (${pos.amount_oz} 盎司)</div>`;
                });
                
                paperPosStatus.innerHTML = htmlContent;
                
                if (hasBuy && hasSell) paperPositionBox.className = "paper-pos-box"; // Mixed
                else if (hasBuy) paperPositionBox.className = "paper-pos-box active-buy";
                else paperPositionBox.className = "paper-pos-box active-sell";
                
                if (paperCloseBtn) paperCloseBtn.disabled = false;
            } else if (paperPosStatus && paperPositionBox) {
                paperPosStatus.textContent = "目前無持倉倉位";
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
            const res = await fetch(`/api/paper/trade?side=${side}&amount_oz=${amount}`, { method: "POST" });
            const data = await res.json();
            loadPaperAccount();
        } catch (e) {
            console.error("Paper trade failed:", e);
        }
    }

    async function closePaperTrade() {
        try {
            const res = await fetch("/api/paper/close", { method: "POST" });
            const data = await res.json();
            loadPaperAccount();
        } catch (e) {
            console.error("Paper close failed:", e);
        }
    }

    async function resetPaperAccount() {
        try {
            const res = await fetch("/api/paper/reset", { method: "POST" });
            const data = await res.json();
            loadPaperAccount();
        } catch (e) {
            console.error("Paper reset failed:", e);
        }
    }

    function updateSummaryUI(summary) {
        if (!summary || !summary.current_price) return;

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

        signalBadge.textContent = getChineseSignalText(summary.signal_type);
        signalBadge.className = `signal-badge ${summary.signal_type}`;

        signalScore.textContent = `${summary.signal_score > 0 ? "+" : ""}${summary.signal_score}`;
        signalTime.textContent = `更新時間: ${summary.timestamp.split(" ")[1] || summary.timestamp}`;

        // TP / SL
        document.getElementById("tpPrice").textContent = `$${summary.take_profit.toFixed(2)}`;
        document.getElementById("slPrice").textContent = `$${summary.stop_loss.toFixed(2)}`;

        // Indicators Monitor
        document.getElementById("rsiValue").textContent = summary.rsi_14;
        document.getElementById("macdValue").textContent = summary.macd_hist;
        document.getElementById("atrValue").textContent = summary.atr_14;
        document.getElementById("emaRatio").textContent = `${summary.ema_9} / ${summary.ema_50}`;

        // Reasons List
        const reasonsList = document.getElementById("reasonsList");
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
            document.getElementById("runBacktestBtn").textContent = "計算中...";
            const res = await fetch(`/api/gold/backtest?symbol=XAUUSD&interval=${currentTf}`);
            const result = await res.json();
            
            document.getElementById("btWinRate").textContent = `${result.win_rate_pct}%`;
            document.getElementById("btReturn").textContent = `${result.total_return_pct > 0 ? "+" : ""}${result.total_return_pct}%`;
            document.getElementById("btPF").textContent = result.profit_factor;
            document.getElementById("btMDD").textContent = `-${result.max_drawdown_pct}%`;

            document.getElementById("runBacktestBtn").innerHTML = '<i class="fa-solid fa-check"></i> 完成';
            setTimeout(() => {
                document.getElementById("runBacktestBtn").innerHTML = '<i class="fa-solid fa-play"></i> 執行回測';
            }, 2000);
        } catch (err) {
            console.error("Backtest failed:", err);
            document.getElementById("runBacktestBtn").innerHTML = '<i class="fa-solid fa-play"></i> 執行回測';
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
