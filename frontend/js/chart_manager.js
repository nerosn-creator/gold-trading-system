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

        // EMAs
        this.ema9Series = this.chart.addLineSeries({ color: '#FFD700', lineWidth: 1, title: 'EMA 9' });
        this.ema21Series = this.chart.addLineSeries({ color: '#29B6F6', lineWidth: 1, title: 'EMA 21' });
        this.ema50Series = this.chart.addLineSeries({ color: '#AB47BC', lineWidth: 2, title: 'EMA 50' });

        // Bollinger Bands
        this.bbUpperSeries = this.chart.addLineSeries({ color: 'rgba(255, 255, 255, 0.3)', lineWidth: 1, lineStyle: 2 });
        this.bbLowerSeries = this.chart.addLineSeries({ color: 'rgba(255, 255, 255, 0.3)', lineWidth: 1, lineStyle: 2 });

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

        if (this.chart && this.mainContainer) {
            const w = this.mainContainer.clientWidth;
            const h = this.mainContainer.clientHeight;
            if (w > 0 && h > 0) {
                this.chart.applyOptions({ width: w, height: h });
            }
        }

        this.chart.timeScale().fitContent();
    }

    setEMAVisible(visible) {
        if (this.ema9Series) this.ema9Series.applyOptions({ visible });
        if (this.ema21Series) this.ema21Series.applyOptions({ visible });
        if (this.ema50Series) this.ema50Series.applyOptions({ visible });
    }

    setBBVisible(visible) {
        if (this.bbUpperSeries) this.bbUpperSeries.applyOptions({ visible });
        if (this.bbLowerSeries) this.bbLowerSeries.applyOptions({ visible });
    }
}
