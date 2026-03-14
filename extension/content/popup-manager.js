export class PopupManager {
    constructor(settingsManager) {
        this.settingsManager = settingsManager;
        this.margin = 10;
        this.popup = null; // Initialize as null
        this.shortcuts = {
            speak: "Alt+3", // Default fallback
        };
    }

    async init() {
        await this.createShadowPopup();
        await this.loadShortcuts();
        this.setupSettingsListener();
        this.watchForRemoval();
        return this;
    }

    async loadShortcuts() {
        try {
            const response = await chrome.runtime.sendMessage({
                type: 'get-kaprao-shortcuts'
            });

            if (response.success) {
                this.shortcuts = response.shortcuts;
            } else {
                console.log('Failed to load shortcuts:', response.error);
            }
        } catch (error) {
            console.log('Error loading shortcuts:', error);
            // Keep defaults
        }
    }

    watchForRemoval() {
        // Re-inject popup if DOM is rehydrated (Next.js, etc)
        const observer = new MutationObserver((mutations) => {
            const container = document.getElementById('kaprao-popup-container');

            if (!container) {
                this.init();
                observer.disconnect();
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: false
        });
    }


    async createShadowPopup() {
        // Preload all fonts in the main document first
        const fonts = [
            { family: 'Noto Sans Thai', url: 'assets/NotoSansThai-VariableFont_wdth,wght.ttf', weight: '100 900' },
            { family: 'Mali', url: 'assets/Mali-Light.ttf' },
            { family: 'Sriracha', url: 'assets/Sriracha-Regular.ttf' }
        ];

        for (const font of fonts) {
            const fontUrl = chrome.runtime.getURL(font.url);
            const fontFace = new FontFace(font.family, `url('${fontUrl}')`, {
                weight: font.weight || 'normal'
            });

            try {
                await fontFace.load();
                document.fonts.add(fontFace);
            } catch (e) {
                console.error(`Font loading failed for ${font.family}:`, e);
            }
        }
        
        // Create container in light DOM
        const container = document.createElement('div');
        container.id = 'kaprao-popup-container';
        document.body.appendChild(container);

        // Attach shadow root
        const shadow = container.attachShadow({ mode: 'open' });

        // Load CSS
        const cssUrl = chrome.runtime.getURL('styles/popup.css');
        const response = await fetch(cssUrl);
        const cssText = await response.text();

        // Create style element
        const style = document.createElement('style');
        style.textContent = cssText.replace(
            /url\(['"]?img\//g,
            `url('${chrome.runtime.getURL('img/')}`
        );

        shadow.appendChild(style);

        // Create popup element inside shadow DOM
        this.popup = document.createElement('div');
        this.popup.id = 'kaprao-popup';
        shadow.appendChild(this.popup);

        // Store references
        this.container = container;
        this.shadow = shadow;

        this.applyTheme();
        this.applyFont();
    }

    applyTheme() {
        if (!this.popup) return;

        const settings = this.settingsManager.getSettings();

        let theme = settings.theme;
        if (theme === 'system') {
            theme = window.matchMedia('(prefers-color-scheme: dark)').matches
                ? 'dark' : 'light';
        }

        this.popup.setAttribute('data-theme', theme);
    }

    applyFont() {
        if (!this.popup) return;

        const settings = this.settingsManager.getSettings();
        this.popup.setAttribute('data-font', settings.font);
    }

    setupSettingsListener() {
        // Listen for settings changes
        this.settingsManager.onChanged(() => {
            this.applyTheme();
            this.applyFont();
        });
    }

    show(results) {
        if (!this.popup) {
            console.error('Popup not created yet. Call createShadowPopup() first.');
            return;
        }
        this.popup.innerHTML = '';
        this.popup.innerHTML += Handlebars.templates.shortcutHint(this.shortcuts);
        this.popup.innerHTML += Handlebars.templates.popup(results);
        this.popup.style.display = 'flex';
    }

    hide() {
        this.popup.style.display = 'none';
    }

    position(x, y) {
        if (x + this.margin + this.popup.offsetWidth > window.innerWidth) {
            this.container.style.right = '0px';
            this.container.style.left = 'unset';
        } else {
            this.container.style.left = `${x}px`;
            this.container.style.right = 'unset';
        }

        if (y + this.margin + this.popup.offsetHeight > window.innerHeight) {
            this.container.style.bottom = `${window.innerHeight - y + this.margin}px`;
            this.container.style.top = 'unset';
        } else {
            this.container.style.top = `${y}px`;
            this.container.style.bottom = 'unset';
        }
    }

}