// Storybox Plus: the card of a Toniebox 2 for dashboards. It shows what the box's
// card on the page shows (what plays, volume, battery, headphones, sleep timer,
// next alarm, night mode) and has its buttons, but neither its settings nor the
// charge history. It is open to every user who may read the box's media player:
// the state comes from the integration's card command, the buttons call the
// media player's actions.
const {
  STYLE, BoxView, TEXTS,
} = await import(new URL(`./storybox-plus-common.js${new URL(import.meta.url).search}`, import.meta.url).href);

const CARD = "storybox-plus-box-card";
// What the card can leave out, each on by default (show_<part>: false hides it)
const PARTS = ["picture", "battery", "volume", "headphones", "sleep_timer", "next_alarm", "night_mode", "playback", "controls"];
const EDITOR = `${CARD}-editor`;
// The card asks again this often, for what has no entity of its own (ms)
const REFRESH = 30000;
// A changed entity is asked about after this pause, so a burst of changes asks once (ms)
const SETTLE = 400;

// The page's sheet, without its full-window frame
const CARD_STYLE = `
  :host { display: block; height: auto; background: none; }
  ha-card { height: 100%; }
`;

const texts = (hass) => ((hass?.locale?.language || hass?.language || "en").toLowerCase().startsWith("de") ? TEXTS.de : TEXTS.en);

if (!customElements.get(CARD)) {
  class StoryboxPlusBoxCard extends BoxView(HTMLElement) {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._box_ = null;
      this._error = null;
      this._upgrade(["hass"]);
      this.shadowRoot.addEventListener("click", (e) => {
        const target = e.composedPath().find((el) => el instanceof Element && el.hasAttribute?.("data-act"));
        if (!target || target.hasAttribute("disabled")) return;
        const act = target.getAttribute("data-act");
        if (act.startsWith("ctl:")) {
          const [, , command, value] = act.split(":");
          this._command(command, value);
        }
      });
    }

    static getConfigElement() {
      return document.createElement(EDITOR);
    }

    // The first media player of the integration, for the card picker's preview
    static getStubConfig(hass) {
      const found = Object.values(hass?.entities || {}).find(
        (e) => e.platform === "storybox_plus" && e.entity_id.startsWith("media_player."),
      );
      return { entity: found?.entity_id || "" };
    }

    setConfig(config) {
      if (!config || typeof config !== "object") throw new Error("Invalid configuration");
      this._config = { ...config };
      this._box_ = null;
      this._error = null;
      this._seen = undefined;
      if (this._hass) this._load();
      this._render();
    }

    set hass(hass) {
      const first = !this._hass;
      this._hass = hass;
      const state = this._config?.entity ? hass.states[this._config.entity] : undefined;
      // The media player changes with what plays, the volume and the connection: ask again then
      if (first || state !== this._seen) {
        this._seen = state;
        window.clearTimeout(this._settle);
        this._settle = window.setTimeout(() => this._load(), first ? 0 : SETTLE);
      }
    }

    connectedCallback() {
      this._timer = window.setInterval(() => this._load(), REFRESH);
      this._ticker = window.setInterval(() => this._tick(), 1000);
      if (this._hass) this._load();
    }

    disconnectedCallback() {
      window.clearInterval(this._timer);
      window.clearInterval(this._ticker);
      window.clearTimeout(this._settle);
    }

    getCardSize() {
      return 4;
    }

    getGridOptions() {
      return { columns: 12, min_columns: 6 };
    }

    async _load() {
      const entity = this._config?.entity;
      if (!this._hass || !entity || document.visibilityState === "hidden") return this._render();
      try {
        this._box_ = await this._hass.callWS({ type: "storybox_plus/box/card", entity_id: entity });
        this._error = null;
        // The box's word on the volume counts again
        this._volSent = null;
      } catch (err) {
        this._box_ = null;
        this._error = err?.code === "unauthorized" ? "denied" : err?.code === "unknown_box" ? "unknown" : "failed";
        this._errorText = err?.message || "";
      }
      this._render();
    }

    // The buttons are the media player's actions, which every user may call
    async _command(command, value) {
      const b = this._box_;
      if (!b || !this._hass || this._ctlBusy) return;
      const target = { entity_id: this._config.entity };
      const calls = {
        play: ["media_player", "media_play", {}],
        pause: ["media_player", "media_pause", {}],
        next: ["media_player", "media_next_track", {}],
        previous: ["media_player", "media_previous_track", {}],
        volume: ["media_player", "volume_set", { volume_level: Number(value) / (b.volume_max || 13) }],
        sleep: ["storybox_plus", "set_sleep_timer", { minutes: Number(value) }],
        sleep_clear: ["storybox_plus", "clear_sleep_timer", {}],
      };
      const call = calls[command];
      if (!call) return;
      this._ctlBusy = b.id;
      this._ctlError = null;
      this._render();
      try {
        await this._hass.callService(call[0], call[1], call[2], target);
        // The next press goes on from the level just sent, until the box answers
        if (command === "volume") {
          b.volume = Number(value);
          this._volSent = { box: b.id };
        }
      } catch (err) {
        this._ctlError = { id: b.id, message: err?.message || String(err) };
      }
      this._ctlBusy = null;
      this._render();
      window.setTimeout(() => this._load(), 1500);
    }

    _render() {
      const t = this._t;
      let body;
      if (!this._config?.entity) body = this._card("", this._alert(t.cardNoEntity, "info"));
      else if (this._error) {
        const text = this._error === "denied" ? t.cardDenied : this._error === "unknown" ? t.cardUnknown : `${t.failed}: ${this._errorText}`;
        body = this._card("", this._alert(text, this._error === "failed" ? "error" : "warning"));
      } else if (!this._box_) body = this._card("", `<div class="muted">${t.loading}</div>`);
      else body = this._box(this._box_, false, this._config);
      const html = `<style>${STYLE}${CARD_STYLE}</style>${body}`;
      if (html === this._html) return;
      this._html = html;
      this.shadowRoot.innerHTML = html;
      this._tick();
    }
  }

  class StoryboxPlusBoxCardEditor extends HTMLElement {
    setConfig(config) {
      this._config = { ...config };
      this._render();
    }

    set hass(hass) {
      this._hass = hass;
      this._render();
    }

    _render() {
      if (!this._hass || !this._config) return;
      const t = texts(this._hass);
      if (!this._form) {
        this._form = document.createElement("ha-form");
        this._form.addEventListener("value-changed", (e) => {
          const value = { ...e.detail.value };
          // Only what is turned off is written; on is the default
          for (const part of PARTS) if (value[`show_${part}`] !== false) delete value[`show_${part}`];
          const kept = Object.fromEntries(Object.entries(this._config).filter(([k]) => !k.startsWith("show_")));
          this._config = { ...kept, ...value };
          this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config }, bubbles: true, composed: true }));
        });
        this.appendChild(this._form);
      }
      this._form.hass = this._hass;
      this._form.schema = [
        { name: "entity", required: true, selector: { entity: { domain: "media_player", integration: "storybox_plus" } } },
        {
          name: "show", type: "expandable", flatten: true, title: t.cardShow, expanded: true,
          schema: [{ type: "grid", name: "", flatten: true, column_min_width: "200px",
            schema: PARTS.map((part) => ({ name: `show_${part}`, selector: { boolean: {} } })) }],
        },
      ];
      // A part shows unless turned off
      this._form.data = { entity: this._config.entity || "", ...Object.fromEntries(PARTS.map((part) => [`show_${part}`, this._config[`show_${part}`] !== false])) };
      this._form.computeLabel = (field) => (field.name === "entity" ? t.cardEntity : t[field.name] || field.name);
    }
  }

  customElements.define(CARD, StoryboxPlusBoxCard);
  customElements.define(EDITOR, StoryboxPlusBoxCardEditor);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: CARD,
    name: `Storybox Plus · ${texts(document.querySelector("home-assistant")?.hass).cardName}`,
    description: texts(document.querySelector("home-assistant")?.hass).cardDescription,
    preview: true,
    documentationURL: "https://github.com/n-schilling/ha-storybox-plus#dashboard-card",
  });
}
