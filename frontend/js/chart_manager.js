class GoldChartManager {
    constructor(mainContainerId) {
        this.mainContainer = document.getElementById(mainContainerId);

        this.chart = null;
        this.candlestickSeries = null;
        this.ema9Series = null;
        this.ema21Series = null;
        this.ema50Series = null;
        this.bbUpperSeries = null;
        this.bbLowerSeries = null;
        this.latestEma = null;

        this.initCharts();
    }

    initCharts() {
        const LWC = window.LightweightCharts || (typeof LightweightCharts !== 'undefined' ? LightweightCharts : null);
        if (!this.mainContainer || !LWC) {
            console.warn("LightweightCharts library not loaded.");
            return;
        }

        const initialWidth = this.mainContainer.clientWidth || 800;
        const initialHeight = this.mainContainer.clientHeight || 450;

        // Main Candle Chart
        this.chart = LWC.createChart(this.mainContainer, {
            width: initialWidth,
            height: initialHeight,
            layout: {
                backgroundColor: 'transparent',
                textColor: '#9CA3AF',
            },
            grid: {
                vertLines: { color: 'rgba(255, 255, 255, 0.04)' },
                horzLines: { color: 'rgba(255, 255, 255, 0.04)' },
            },
            crosshair: {
                mode: LightweightCharts.CrosshairMode.Normal,
            },
            rightPriceScale: {
                borderColor: 'rgba(255, 255, 255, 0.1)',
            },
            timeScale: {
                borderColor: 'rgba(255, 255, 255, 0.1)',
                timeVisible: true,
                secondsVisible: false,
                rightOffset: 6,
            },
        });

        // Candlesticks
        this.candlestickSeries = this.chart.addCandlestickSeries({
            upColor: '#00E676',
            downColor: '#FF1744',
            borderVisible: false,
            wickUpColor: '#00E676',
            wickDownColor: '#FF1744',
        });

        // EMAs (titles and price lines removed to prevent blocking latest candles and markers)
        this.ema9Series = this.chart.addLineSeries({
            color: '#FFD700',
            lineWidth: 1.5,
            priceLineVisible: false,
            lastValueVisible: false,
        });
        this.ema21Series = this.chart.addLineSeries({
            color: '#29B6F6',
            lineWidth: 1.5,
            priceLineVisible: false,
            lastValueVisible: false,
        });
        this.ema50Series = this.chart.addLineSeries({
            color: '#AB47BC',
            lineWidth: 2,
            priceLineVisible: false,
            lastValueVisible: false,
        });

        // Bollinger Bands
        this.bbUpperSeries = this.chart.addLineSeries({
            color: 'rgba(255, 255, 255, 0.3)',
            lineWidth: 1,
            lineStyle: 2,
            priceLineVisible: false,
            lastValueVisible: false,
        });
        this.bbLowerSeries = this.chart.addLineSeries({
            color: 'rgba(255, 255, 255, 0.3)',
            lineWidth: 1,
            lineStyle: 2,
            priceLineVisible: false,
            lastValueVisible: false,
        });

        // Crosshair legend handler for live EMA values without obstructing candles
        this.chart.subscribeCrosshairMove((param) => {
            if (!param || !param.time || !param.seriesPrices) {
                this.renderLegend(this.latestEma);
                return;
            }
            const getPrice = (series) => {
                const val = param.seriesPrices.get(series);
                if (val == null) return null;
                if (typeof val === 'number') return val;
                if (typeof val === 'object' && val.close != null) return val.close;
                return null;
            };
            const e9 = getPrice(this.ema9Series);
            const e21 = getPrice(this.ema21Series);
            const e50 = getPrice(this.ema50Series);

            this.renderLegend({
                ema9: e9 != null ? e9 : (this.latestEma ? this.latestEma.ema9 : null),
                ema21: e21 != null ? e21 : (this.latestEma ? this.latestEma.ema21 : null),
                ema50: e50 != null ? e50 : (this.latestEma ? this.latestEma.ema50 : null),
            });
        });

        // Auto resize
        const resizeHandler = () => {
            if (this.chart && this.mainContainer) {
                const w = this.mainContainer.clientWidth;
                const h = this.mainContainer.clientHeight;
                if (w > 0 && h > 0) {
                    this.chart.applyOptions({ width: w, height: h });
                }
            }
        };

        window.addEventListener('resize', resizeHandler);
        window.addEventListener('orientationchange', () => setTimeout(resizeHandler, 200));
        setTimeout(resizeHandler, 100);
        setTimeout(resizeHandler, 300);
        setTimeout(resizeHandler, 800);
    }

    updateData(candleData) {
        if (!candleData || candleData.length === 0 || !this.candlestickSeries) return;


        const candles = [];
        const ema9Data = [];
        const ema21Data = [];
        const ema50Data = [];
        const bbUpperData = [];
        const bbLowerData = [];
        const rsiData = [];
        const markers = [];

        let prevSignalType = null;

        candleData.forEach(item => {
            // Unix timestamp in seconds
            const time = new Date(item.timestamp).getTime() / 1000;

            candles.push({
                time: time,
                open: item.open,
                high: item.high,
                low: item.low,
                close: item.close
            });

            if (item.ema_9) ema9Data.push({ time, value: item.ema_9 });
            if (item.ema_21) ema21Data.push({ time, value: item.ema_21 });
            if (item.ema_50) ema50Data.push({ time, value: item.ema_50 });
            if (item.bb_upper) bbUpperData.push({ time, value: item.bb_upper });
            if (item.bb_lower) bbLowerData.push({ time, value: item.bb_lower });
            if (item.rsi_14) rsiData.push({ time, value: item.rsi_14 });

            // Buy / Sell Markers: Only plot on Signal Transitions (Reversals) or Strong Signals
            const currSignal = item.signal_type;
            const isSignalChange = (prevSignalType !== currSignal && currSignal !== "NEUTRAL");
            const isStrong = (currSignal === "STRONG_BUY" || currSignal === "STRONG_SELL");

            if (isSignalChange || (isStrong && prevSignalType !== currSignal)) {
                if (currSignal === "STRONG_BUY") {
                    markers.push({
                        time: time,
                        position: 'belowBar',
                        color: '#00E676',
                        shape: 'arrowUp',
                        text: '強買'
                    });
                } else if (currSignal === "BUY") {
                    markers.push({
                        time: time,
                        position: 'belowBar',
                        color: '#00E676',
                        shape: 'arrowUp',
                        text: '買'
                    });
                } else if (currSignal === "STRONG_SELL") {
                    markers.push({
                        time: time,
                        position: 'aboveBar',
                        color: '#FF1744',
                        shape: 'arrowDown',
                        text: '強賣'
                    });
                } else if (currSignal === "SELL") {
                    markers.push({
                        time: time,
                        position: 'aboveBar',
                        color: '#FF1744',
                        shape: 'arrowDown',
                        text: '賣'
                    });
                }
            }

            if (currSignal !== "NEUTRAL") {
                prevSignalType = currSignal;
            }
        });


        this.candlestickSeries.setData(candles);
        this.ema9Series.setData(ema9Data);
        this.ema21Series.setData(ema21Data);
        this.ema50Series.setData(ema50Data);
        this.bbUpperSeries.setData(bbUpperData);
        this.bbLowerSeries.setData(bbLowerData);
        
        if (this.candlestickSeries.setMarkers && document.getElementById("toggleSignals").checked) {
            this.candlestickSeries.setMarkers(markers);
        }

        // Update latest EMA values for overlay legend
        for (let i = candleData.length - 1; i >= 0; i--) {
            const item = candleData[i];
            if (item && (item.ema_9 != null || item.ema_21 != null || item.ema_50 != null)) {
                this.latestEma = {
                    ema9: item.ema_9,
                    ema21: item.ema_21,
                    ema50: item.ema_50,
                };
                this.renderLegend(this.latestEma);
                break;
            }
        }

        if (this.chart && this.mainContainer) {
            const w = this.mainContainer.clientWidth;
            const h = this.mainContainer.clientHeight;
            if (w > 0 && h > 0) {
                this.chart.applyOptions({ width: w, height: h });
            }
        }

        this.chart.timeScale().fitContent();
    }

    renderLegend(data) {
        if (!data) return;
        const legEMA9 = document.getElementById("legEMA9");
        const legEMA21 = document.getElementById("legEMA21");
        const legEMA50 = document.getElementById("legEMA50");
        if (legEMA9 && data.ema9 != null) legEMA9.textContent = Number(data.ema9).toFixed(2);
        if (legEMA21 && data.ema21 != null) legEMA21.textContent = Number(data.ema21).toFixed(2);
        if (legEMA50 && data.ema50 != null) legEMA50.textContent = Number(data.ema50).toFixed(2);
    }

    setEMAVisible(visible) {
        if (this.ema9Series) this.ema9Series.applyOptions({ visible });
        if (this.ema21Series) this.ema21Series.applyOptions({ visible });
        if (this.ema50Series) this.ema50Series.applyOptions({ visible });
        const legend = document.getElementById("chartLegend");
        if (legend) legend.style.display = visible ? "flex" : "none";
    }

    setBBVisible(visible) {
        if (this.bbUpperSeries) this.bbUpperSeries.applyOptions({ visible });
        if (this.bbLowerSeries) this.bbLowerSeries.applyOptions({ visible });
    }
}
