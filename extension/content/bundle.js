(() => {
  var __getOwnPropNames = Object.getOwnPropertyNames;
  var __esm = (fn, res) => function __init() {
    return fn && (res = (0, fn[__getOwnPropNames(fn)[0]])(fn = 0)), res;
  };
  var __commonJS = (cb, mod) => function __require() {
    return mod || (0, cb[__getOwnPropNames(cb)[0]])((mod = { exports: {} }).exports, mod), mod.exports;
  };

  // extension/content/highlighter.js
  var HighlightOverlay;
  var init_highlighter = __esm({
    "extension/content/highlighter.js"() {
      HighlightOverlay = class {
        constructor() {
          this.overlay = null;
          this.currentHighlights = [];
          this.range = document.createRange();
          this.initOverlay();
          this.watchForRemoval();
        }
        initOverlay() {
          this.overlay = document.createElement("div");
          this.overlay.id = "kaprao-overlay";
          this.overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 10000;
        `;
          document.body.appendChild(this.overlay);
        }
        watchForRemoval() {
          const observer = new MutationObserver((mutations) => {
            const overlay = document.getElementById("kaprao-overlay");
            if (!overlay) {
              this.initOverlay();
              observer.disconnect();
            }
          });
          observer.observe(document.body, {
            childList: true,
            subtree: false
          });
        }
        highlightWord(container, start, end, color = "rgba(255, 255, 0, 0.3)") {
          this.clearAll();
          try {
            this.range.setStart(container, start);
            this.range.setEnd(container, end);
            const rects = this.range.getClientRects();
            for (const rect of rects) {
              if (rect.width === 0 || rect.height === 0) continue;
              const highlight = document.createElement("div");
              highlight.style.cssText = `
                    position: absolute;
                    left: ${rect.left}px;
                    top: ${rect.top}px;
                    width: ${rect.width}px;
                    height: ${rect.height}px;
                    background-color: ${color};
                    border-radius: 2px;
                    pointer-events: none;
                `;
              this.overlay.appendChild(highlight);
              this.currentHighlights.push(highlight);
            }
          } catch (e) {
            console.error("Error creating highlight:", e);
          }
        }
        clearAll() {
          for (const highlight of this.currentHighlights) {
            if (highlight.parentNode) {
              highlight.remove();
            }
          }
          this.currentHighlights = [];
          this.range.collapse();
        }
        destroy() {
          this.clearAll();
          if (this.overlay && this.overlay.parentNode) {
            this.overlay.remove();
          }
        }
        getThaiVoice() {
          return new Promise((resolve) => {
            let voices = speechSynthesis.getVoices();
            if (voices.length) {
              resolve(this.pickThai(voices));
              return;
            }
            speechSynthesis.onvoiceschanged = () => {
              voices = speechSynthesis.getVoices();
              resolve(this.pickThai(voices));
            };
          });
        }
        pickThai(voices) {
          return voices.find(
            (v) => v.lang === "th-TH" && /siri|enhanced|premium/i.test(v.name)
          ) || voices.find((v) => v.lang === "th-TH");
        }
        speakPromise(text) {
          speechSynthesis.cancel();
          return new Promise(async (resolve) => {
            const u = new SpeechSynthesisUtterance(text);
            u.lang = "th-TH";
            u.rate = 1;
            u.pitch = 1;
            const thai = await this.getThaiVoice();
            if (!thai) {
              resolve;
              return;
            }
            u.voice = thai;
            u.onend = resolve;
            speechSynthesis.speak(u);
          });
        }
        async speakCurrent(audioElement = null) {
          if (!this.range) return;
          const text = this.range.toString();
          audioElement?.classList.add("playing");
          await this.speakPromise(text);
          audioElement?.classList.remove("playing");
        }
      };
    }
  });

  // extension/content/word-tracker.js
  function graphemeIndexToCharOffset(graphemes, gIndex) {
    gIndex = Math.min(gIndex, graphemes.length);
    let n = 0;
    for (let i = 0; i < gIndex; i++) {
      const g = graphemes[i];
      if (!g) {
        console.warn("Undefined grapheme", i, graphemes);
        continue;
      }
      n += g.length;
    }
    return n;
  }
  var WordTracker;
  var init_word_tracker = __esm({
    "extension/content/word-tracker.js"() {
      init_highlighter();
      WordTracker = class {
        constructor(popupManager) {
          this.popupManager = popupManager;
          this.highlightOverlay = new HighlightOverlay();
          this.enabled = true;
          this.segmentCache = /* @__PURE__ */ new WeakMap();
          this.currentCapture = null;
          this.cursorRange = document.createRange();
          this.lastMouseEvent = null;
          this.lastMouseMoveTime = 0;
          this.handleMouseMove = this.handleMouseMove.bind(this);
          this.handleMouseLeave = this.handleMouseLeave.bind(this);
          this.handleClickOutside = this.handleClickOutside.bind(this);
        }
        start() {
          document.addEventListener("mousemove", this.handleMouseMove);
          document.addEventListener("mouseleave", this.handleMouseLeave);
          document.removeEventListener("mouseup", this.handleClickOutside);
          document.addEventListener("mouseup", this.handleClickOutside);
          this.enabled = true;
        }
        stop() {
          document.removeEventListener("mousemove", this.handleMouseMove);
          document.removeEventListener("mouseleave", this.handleMouseLeave);
          document.removeEventListener("mouseup", this.handleClickOutside);
          this.enabled = false;
          this.cleanup();
        }
        pause() {
          document.removeEventListener("mousemove", this.handleMouseMove);
          document.removeEventListener("mouseleave", this.handleMouseLeave);
          this.enabled = false;
        }
        isCursorOverText(node, offset, x, y) {
          this.cursorRange.setStart(node, offset);
          this.cursorRange.setEnd(node, offset);
          const rects = this.cursorRange.getClientRects();
          if (!rects.length || rects.length > 1) return false;
          const rect = rects[0];
          const padding = 25;
          if (x >= rect.left - padding && x <= rect.right + padding && y >= rect.top - padding && y <= rect.bottom + padding) {
            return true;
          }
          return false;
        }
        async handleMouseMove(e) {
          if (!this.enabled || this.popupManager.persisted) return;
          this.lastMouseEvent = e;
          this.popupManager.position(e.clientX, e.clientY);
          const ele = document.elementFromPoint(e.clientX, e.clientY);
          const range = document.caretRangeFromPoint(e.clientX, e.clientY);
          if (["TEXTAREA", "INPUT", "SELECT", "HTML", "BODY"].includes(
            ele?.tagName ?? "UNDEFINED_TAG"
          ) || !range || range.startContainer.nodeType !== Node.TEXT_NODE) {
            this.cleanup();
            return;
          }
          const node = range.startContainer;
          const offset = range.startOffset;
          const text = node.data;
          if (!this.isCursorOverText(node, offset, e.clientX, e.clientY)) {
            this.cleanup();
            return;
          }
          if (!/[ก-๙]/.test(text)) {
            this.cleanup();
            return;
          }
          if (this.currentCapture && this.currentCapture.text === text && // ← Compare text instead of node
          offset >= this.currentCapture.startChar && offset < this.currentCapture.endChar) {
            return;
          }
          const response = await chrome.runtime.sendMessage({
            action: "kapraoSegment",
            text,
            offset
          });
          const result = response?.result;
          if (!result) {
            this.highlightOverlay.clearAll();
            this.cleanup();
            return;
          }
          const { match } = result;
          const startGi = match.start;
          const surface = match.surface;
          const startChar = graphemeIndexToCharOffset(result.graphemes, startGi);
          const endChar = graphemeIndexToCharOffset(
            result.graphemes,
            startGi + match.length
          );
          this.currentCapture = {
            text,
            node,
            startChar,
            endChar,
            entries: result.entries
          };
          this.currentWord = node;
          this.highlightOverlay.highlightWord(node, startChar, endChar);
          this.popupManager.show(result);
        }
        handleMouseLeave() {
          if (this.popupManager.persisted) return;
          this.cleanup();
        }
        handleClickOutside(e) {
          if (!this.popupManager.persisted) return;
          if (e.composedPath().includes(this.popupManager.popup)) return;
          this.popupManager.unpersist();
          this.start();
        }
        cleanup() {
          if (this.popupManager.persisted) return;
          this.highlightOverlay.clearAll();
          this.popupManager.hide();
          this.currentCapture = null;
        }
      };
    }
  });

  // extension/content/popup-manager.js
  var PopupManager;
  var init_popup_manager = __esm({
    "extension/content/popup-manager.js"() {
      PopupManager = class {
        constructor(settingsManager) {
          this.settingsManager = settingsManager;
          this.margin = 10;
          this.popup = null;
          this.shortcuts = {
            speak: "Alt+3"
            // Default fallback
          };
          this.persisted = false;
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
              type: "get-kaprao-shortcuts"
            });
            if (response.success) {
              this.shortcuts = response.shortcuts;
            } else {
              console.log("Failed to load shortcuts:", response.error);
            }
          } catch (error) {
            console.log("Error loading shortcuts:", error);
          }
        }
        watchForRemoval() {
          const observer = new MutationObserver((mutations) => {
            const container = document.getElementById("kaprao-popup-container");
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
          const fonts = [
            { family: "Noto Sans Thai", url: "assets/NotoSansThai-VariableFont_wdth,wght.ttf", weight: "100 900" },
            { family: "Mali", url: "assets/Mali-Light.ttf" },
            { family: "Sriracha", url: "assets/Sriracha-Regular.ttf" }
          ];
          for (const font of fonts) {
            const fontUrl = chrome.runtime.getURL(font.url);
            const fontFace = new FontFace(font.family, `url('${fontUrl}')`, {
              weight: font.weight || "normal"
            });
            try {
              await fontFace.load();
              document.fonts.add(fontFace);
            } catch (e) {
              console.error(`Font loading failed for ${font.family}:`, e);
            }
          }
          const container = document.createElement("div");
          container.id = "kaprao-popup-container";
          document.body.appendChild(container);
          const shadow = container.attachShadow({ mode: "open" });
          const cssUrl = chrome.runtime.getURL("styles/popup.css");
          const response = await fetch(cssUrl);
          const cssText = await response.text();
          const style = document.createElement("style");
          style.textContent = cssText.replace(
            /url\(['"]?img\//g,
            `url('${chrome.runtime.getURL("img/")}`
          );
          shadow.appendChild(style);
          this.popup = document.createElement("div");
          this.popup.id = "kaprao-popup";
          shadow.appendChild(this.popup);
          this.container = container;
          this.shadow = shadow;
          this.applyTheme();
          this.applyFont();
          this.applyPronunciation();
        }
        applyTheme() {
          if (!this.popup) return;
          const settings = this.settingsManager.getSettings();
          let theme = settings.theme;
          if (theme === "system") {
            theme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
          }
          this.popup.setAttribute("data-theme", theme);
        }
        applyFont() {
          if (!this.popup) return;
          const settings = this.settingsManager.getSettings();
          this.popup.setAttribute("data-font", settings.font);
        }
        applyPronunciation() {
          if (!this.popup) return;
          const settings = this.settingsManager.getSettings();
          this.popup.setAttribute("data-show-pronunciation", settings.showPronunciation);
        }
        setupSettingsListener() {
          this.settingsManager.onChanged(() => {
            this.applyTheme();
            this.applyFont();
            this.applyPronunciation();
          });
        }
        show(results) {
          if (!this.popup) {
            console.error("Popup not created yet. Call createShadowPopup() first.");
            return;
          }
          this.popup.innerHTML = "";
          this.popup.innerHTML += Handlebars.templates.shortcutHint(this.shortcuts);
          this.popup.innerHTML += Handlebars.templates.popup(results);
          this.popup.style.display = "flex";
        }
        hide() {
          if (this.persisted) return;
          this.popup.style.display = "none";
        }
        togglePersist() {
          if (this.persisted) {
            this.unpersist();
          } else {
            this.persist();
          }
        }
        persist() {
          if (this.popup.style.display === "none") return;
          this.persisted = true;
          this.popup.classList.add("persisted");
          this.container.style.pointerEvents = "auto";
        }
        unpersist() {
          this.persisted = false;
          this.container.style.pointerEvents = "none";
          this.popup.classList.remove("persisted");
          this.hide();
        }
        position(x, y) {
          if (this.persisted) return;
          if (x + this.margin + this.popup.offsetWidth > window.innerWidth) {
            this.container.style.right = "0px";
            this.container.style.left = "unset";
          } else {
            this.container.style.left = `${x}px`;
            this.container.style.right = "unset";
          }
          if (y + this.margin + this.popup.offsetHeight > window.innerHeight) {
            this.container.style.bottom = `${window.innerHeight - y + this.margin}px`;
            this.container.style.top = "unset";
          } else {
            this.container.style.top = `${y}px`;
            this.container.style.bottom = "unset";
          }
        }
      };
    }
  });

  // extension/content/settings.js
  var SettingsManager;
  var init_settings = __esm({
    "extension/content/settings.js"() {
      SettingsManager = class {
        constructor() {
          this.settings = {
            theme: "system",
            font: "loopless",
            showPronunciation: true
          };
          this.listeners = /* @__PURE__ */ new Set();
        }
        async load() {
          return new Promise((resolve) => {
            chrome.storage.sync.get({
              theme: "system",
              font: "loopless",
              showPronunciation: true
            }, (items) => {
              this.settings = items;
              this.notifyListeners();
              resolve(this.settings);
            });
          });
        }
        getSettings() {
          return { ...this.settings };
        }
        get(key) {
          return this.settings[key];
        }
        onChanged(callback) {
          this.listeners.add(callback);
          chrome.runtime.onMessage.addListener((message) => {
            if (message.action === "kapraoSettingsChanged") {
              this.settings = message.settings;
              this.notifyListeners();
            }
          });
          const handleSystemThemeChange = () => {
            if (this.settings.theme === "system") {
              this.notifyListeners();
            }
          };
          window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", handleSystemThemeChange);
          return () => {
            this.listeners.delete(callback);
            window.matchMedia("(prefers-color-scheme: dark)").removeEventListener("change", handleSystemThemeChange);
          };
        }
        // New: Notify all listeners
        notifyListeners() {
          this.listeners.forEach((callback) => {
            try {
              callback(this.settings);
            } catch (error) {
              console.error("Settings listener error:", error);
            }
          });
        }
      };
    }
  });

  // extension/content/content.js
  var require_content = __commonJS({
    "extension/content/content.js"() {
      init_word_tracker();
      init_popup_manager();
      init_settings();
      function registerHandlebarsHelpers() {
        Handlebars.registerHelper("join", function(array, separator) {
          return array ? array.join(separator) : "";
        });
        Handlebars.registerHelper("eq", function(a, b) {
          return a === b;
        });
        Handlebars.registerHelper("gt", (a, b) => a > b);
        Handlebars.registerHelper("lte", (a, b) => a <= b);
        Handlebars.registerHelper("and", (a, b) => a && b);
        Handlebars.registerPartial(
          "entryBlock",
          Handlebars.templates.entryBlock
        );
        Handlebars.registerHelper("joinSyllables", function(roman) {
          roman = roman.replace(/([kpt])•h/g, "$1~h");
          roman = roman.replace(/([^ptks])•ng/g, "$1~ng");
          roman = roman.replace(/ng•(?![ptkslmnhrwyjc]g?)/g, "ng~");
          roman = roman.replace(/•/g, "");
          roman = roman.replace(/~/g, "\u2022");
          roman = roman.normalize("NFC");
          return roman;
        });
        Handlebars.registerHelper("spanifyThai", function(text) {
          text = text.replace(/</g, "&lt;");
          text = text.replace(/>/g, "&gt;");
          text = text.replace(/\[([ก-๙ ]+?)\s/g, '<span lang="th">$1</span> ');
          return text;
        });
      }
      var settingsManager;
      var popupManager;
      var wordTracker;
      async function init() {
        try {
          settingsManager = new SettingsManager();
          await settingsManager.load();
          registerHandlebarsHelpers();
          popupManager = new PopupManager(settingsManager);
          await popupManager.init();
          wordTracker = new WordTracker(popupManager);
          chrome.runtime.sendMessage({ action: "getKapraoState" }, (response) => {
            if (response?.enabled === true) {
              wordTracker.start();
            }
          });
        } catch (error) {
          console.error("Kaprao initialization error:", error);
        }
      }
      chrome.runtime.onMessage.addListener((message) => {
        if (message.action === "enableKaprao") {
          if (message.enabled) {
            wordTracker.start();
          } else {
            wordTracker.stop();
          }
          console.log("Kaprao extension", message.enabled ? "enabled" : "disabled");
        } else if (message.action === "kapraoSettingsChanged") {
          settingsManager.settings = message.settings;
          settingsManager.notifyListeners();
        } else if (message.action === "speakCurrent") {
          const audioElement = popupManager.popup.querySelector("#shortcut-hint");
          wordTracker.highlightOverlay.speakCurrent(audioElement);
        } else if (message.action === "persistPopup") {
          popupManager.togglePersist();
          if (popupManager.persisted) {
            wordTracker.pause();
          } else {
            wordTracker.start();
          }
        }
      });
      init();
    }
  });
  require_content();
})();
