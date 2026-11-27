// Storybox Plus: the dashboard card of the Tonieboxes 2. It shows every user what
// is going on: what plays, online or not, the battery, volume, headphones, the
// sleep timer, the next alarm, the night mode, and whether the chapter that plays
// is a favourite. It reads the entities of the boxes and nothing else; its buttons
// the star and the list of chapters call actions every user may call on a box's
// media player anyway. Neither settings nor the charge history: those are on the page.
//
// Without a box in its configuration it shows every Toniebox 2, from the list the
// summary entity of each account carries. It is as high as what it shows; given
// fewer rows in a sections view it draws itself large, then medium, then small,
// and keeps the first that fits.
const {
  STYLE, BoxView, textsFor, esc,
} = await import(new URL(`./storybox-plus-common.js${new URL(import.meta.url).search}`, import.meta.url).href);

const CARD = "storybox-plus-card";
const EDITOR = `${CARD}-editor`;
const DOMAIN = "storybox_plus";
// Every action the buttons may call, each on the box's media player
const ACTIONS = [
  "media_player.media_play", "media_player.media_pause", "media_player.media_next_track", "media_player.media_previous_track",
  "media_player.volume_up", "media_player.volume_down", "storybox_plus.set_sleep_timer", "storybox_plus.clear_sleep_timer",
  "storybox_plus.set_favourite", "media_player.play_media",
];
// The entities of a box the card reads beside its media player, by the integration's own keys
const KEYS = ["connectivity", "battery", "charging", "headphones", "night_mode", "sleep_timer", "next_alarm"];
// The card from most to least: what does not fit is left out in this order
const SIZES = ["large", "medium", "small"];
// What the card can leave out, from the least important to the most: the buttons
// go first, the name and whether the box is online always show
const PARTS = ["controls", "night_mode", "next_alarm", "sleep_timer", "headphones", "volume", "picture", "battery", "playback"];
// The parts only the large card has
const DETAILS = ["controls", "night_mode", "next_alarm", "sleep_timer", "headphones", "volume"];
// What informs a resident is on; the night mode of the light ring is for whoever set it up
const OFF = ["night_mode"];
const DEFAULTS = { size: "auto", ...Object.fromEntries(PARTS.map((part) => [`show_${part}`, !OFF.includes(part)])) };

const known = (state) => (state && state.state !== "unavailable" && state.state !== "unknown" ? state : null);
const number = (value) => (value === null || value === undefined || value === "" || !Number.isFinite(Number(value)) ? null : Number(value));
// The language of the last card that got its data, for the editor's labels
let language = "en";
const texts = (lang, onLoad) => textsFor(lang, onLoad);

// The page's sheet without its full-window frame; the large card lays itself out by
// its width: side by side from 600 px (a wide, low tile such as half of a wall
// display), stacked below, compact under 300 px (a quarter of a sections view)
const CARD_STYLE = `
  :host { display: block; height: 100%; background: none; }
  ha-card { height: 100%; container-type: inline-size; overflow: hidden; }
  .content.fill { height: 100%; }
  .heading { padding: 12px 16px 0; font-size: var(--ha-font-size-l, 16px); font-weight: var(--ha-font-weight-medium, 500); }
  .box + .box { border-top: 1px solid var(--divider-color); }
  /* A box that is switched off is nothing to worry about */
  .dot.err { background: var(--secondary-text-color); opacity: 0.6; }
  .card-header { padding: 12px 16px 8px; font-size: var(--ha-font-size-xl, 20px); line-height: 28px; font-weight: var(--ha-font-weight-normal, 400); }
  .box-body { display: grid; grid-template-columns: minmax(0, 1fr); grid-template-areas: "facts" "now" "ctl"; }
  .box-body > .facts { grid-area: facts; }
  .box-body > .now { grid-area: now; min-width: 0; }
  .box-body > .ctl { grid-area: ctl; min-width: 0; }
  @container (min-width: 600px) {
    .box-body { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); grid-template-areas: "now facts" "now ctl";
      gap: 0 24px; align-items: start; }
    .box-body > .facts { margin-bottom: 4px; }
    .box-body > .ctl .controls { margin-top: 0; }
  }
  /* Narrower than side by side: tighter spacing and buttons, so the card still
     fits a low tile such as the third of a wall display (370 x 262 px) */
  @container (max-width: 599px) {
    .box-pic { width: 32px; height: 32px; }
    .facts { gap: 4px 16px; margin-bottom: 8px; }
    .progress { margin-top: 6px; }
    .controls { margin: 2px 0 0; --mdc-icon-button-size: 40px; }
    .card-content { padding-bottom: 8px; }
  }
  @container (max-width: 299px) {
    .card-header { gap: 6px; }
    .box-pic { width: 28px; height: 28px; }
    .box-name { font-size: var(--ha-font-size-l, 16px); }
    .facts { gap: 2px 12px; margin-bottom: 8px; font-size: var(--ha-font-size-s, 13px); }
    .pic { width: 40px; height: 40px; }
    .controls { flex-wrap: wrap; gap: 0; }
    .controls .ctl-gap { display: none; }
    .sleep-pick { display: none; }
  }
  /* Home Assistant's buttons have no height until they have drawn themselves */
  .controls { min-height: 48px; }
  /* The small card: one row per box, a name line and one second line */
  .compact { display: flex; align-items: center; gap: 10px; height: 56px; padding: 0 16px; cursor: pointer; }
  .content.fill .compact:only-child { height: 100%; }
  .compact .box-pic { width: 32px; height: 32px; margin: 0; }
  .compact .who { flex: 1; min-width: 0; }
  .compact .name { display: flex; align-items: center; gap: 6px; font-weight: var(--ha-font-weight-medium, 500); line-height: 20px; }
  .compact .name span:first-child { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .compact .sub { font-size: var(--ha-font-size-xs, 12px); line-height: 16px; color: var(--secondary-text-color);
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .compact .status { flex: none; }
`;

if (!customElements.get(CARD)) {
  class StoryboxPlusBoxCard extends BoxView(HTMLElement) {
    static getStubConfig() {
      return {};
    }

    // Home Assistant's form shows a part that is not in the configuration as off; the
    // editor element shows what the card does: the defaults with the configuration on top
    static getConfigElement() {
      return document.createElement(EDITOR);
    }

    // A field for every option, the parts in one expandable group
    static getConfigForm() {
      const t = texts(language);
      return {
        schema: [
          { name: "entity", selector: { entity: { filter: { integration: DOMAIN, domain: "media_player" } } } },
          { name: "title", selector: { text: {} } },
          {
            name: "size",
            selector: { select: { mode: "dropdown", options: [["auto", t.sizeAuto], ["small", t.sizeSmall], ["medium", t.sizeMedium], ["large", t.sizeLarge]]
              .map(([value, label]) => ({ value, label })) } },
          },
          {
            type: "expandable", name: "parts", title: t.cardShow, flatten: true,
            schema: [...PARTS].reverse().map((part) => ({ name: `show_${part}`, selector: { boolean: {} } })),
          },
        ],
        computeLabel: (field) => {
          const now = texts(language);
          return { entity: now.cardEntity, title: now.cardTitle, size: now.cardSize }[field.name] ?? now[field.name] ?? field.name;
        },
      };
    }

    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._config = { ...DEFAULTS };
      this._key = null;
      // The entities of each box by their keys, looked up once per registry
      this._found = new Map();
      this._over = new Set();
      this._upgrade(["hass", "layout"]);
    }

    setConfig(config) {
      if (!config || typeof config !== "object") throw new Error("Invalid configuration");
      this._config = { ...DEFAULTS, ...config };
      this._key = null;
      this._render();
    }

    set hass(hass) {
      this._hass = hass;
      language = hass?.locale?.language || hass?.language || language;
      this._render();
    }

    // Home Assistant sets it: "grid" in a sections view, where the card has a fixed height
    set layout(layout) {
      this._layout = layout;
      this._key = null;
      this._render();
    }

    getCardSize() {
      return 4;
    }

    // As high as what it shows, until someone gives it fewer rows
    getGridOptions() {
      return { columns: 6, rows: "auto", min_columns: 3, min_rows: 1 };
    }

    connectedCallback() {
      this._observer = new ResizeObserver(() => {
        this._key = null;
        this._render();
      });
      this._observer.observe(this);
      // What the card shows grows after it was measured (a picture loads, a button
      // draws itself): measure again then, and only then
      this._grown = new ResizeObserver(() => {
        const card = this.shadowRoot.querySelector("ha-card");
        const content = this.shadowRoot.querySelector(".content");
        // Only a size that turned out too high gives way, to the next smaller one:
        // it is remembered, so the card never goes back and forth
        if (!card || !content || !this._drawn || this._drawn.last || content.scrollHeight <= this._room(card) + 1) return;
        this._over.add(this._drawn.size);
        this._key = null;
        this._render();
      });
      this._watch();
      this._ticker = window.setInterval(() => this._tick(), 1000);
      if (!this._listening) {
        this._listening = true;
        this.shadowRoot.addEventListener("click", (e) => this._clicked(e));
        // A row that opens something reacts to Enter and Space as well
        this.shadowRoot.addEventListener("keydown", (e) => {
          const el = e.composedPath()[0];
          if ((e.key === "Enter" || e.key === " ") && (el?.hasAttribute?.("data-entity") || el?.matches?.("li[role=button][data-act]"))) {
            e.preventDefault();
            this._clicked(e);
          }
        });
      }
      this._render();
    }

    disconnectedCallback() {
      this._observer?.disconnect();
      this._grown?.disconnect();
      window.clearInterval(this._ticker);
    }

    // The height the card has for its content
    _room(card) {
      const style = getComputedStyle(card);
      return card.clientHeight - parseFloat(style.paddingTop) - parseFloat(style.paddingBottom);
    }

    _watch() {
      const content = this.shadowRoot.querySelector(".content");
      if (content && this._grown) {
        this._grown.disconnect();
        this._grown.observe(content);
      }
    }

    _clicked(e) {
      const path = e.composedPath().filter((el) => el instanceof Element);
      const button = path.find((el) => el.hasAttribute("data-act"));
      if (button) {
        if (button.hasAttribute("disabled")) return;
        const [kind, player, command, value] = button.getAttribute("data-act").split(":");
        if (kind === "ctl") this._command(player, command, value);
        // The star of the chapter that plays, or of one in the list: the chapter it was
        // drawn for (its index from 0) and the state it does not show yet
        const wanted = button.getAttribute("aria-pressed") !== "true";
        if (kind === "star") this._command(player, "star", { chapter: Number(button.dataset.i), favourite: wanted });
        if (kind === "starch") this._command(player, "star", { chapter: Number(command), favourite: wanted });
        // The list of chapters opens above the dashboard; a chapter chosen there plays and closes it
        if (kind === "tracks") {
          this._tracks = player;
          this._renderOverlay();
        }
        if (kind === "jump") {
          this._tracks = null;
          this._renderOverlay();
          this._command(player, "chapter", command);
        }
        return;
      }
      // A tap on a small row opens Home Assistant's own dialog of the box: reading, no action
      const row = path.find((el) => el.hasAttribute("data-entity"));
      if (row) this.dispatchEvent(new CustomEvent("hass-more-info", { detail: { entityId: row.dataset.entity }, bubbles: true, composed: true }));
    }

    // The media players of the boxes to show: the one configured, else every box the
    // summary entities of the accounts list. null: a configured one that is no box of ours
    _players() {
      const hass = this._hass;
      const c = this._config;
      if (c.entity) return hass.states[c.entity] && hass.entities?.[c.entity]?.platform === DOMAIN ? [c.entity] : null;
      const players = [];
      for (const entry of Object.values(hass.entities || {})) {
        if (entry.platform !== DOMAIN || entry.translation_key !== "boxes") continue;
        for (const box of hass.states[entry.entity_id]?.attributes.boxes || []) {
          if (hass.states[box.entity_id] && !players.includes(box.entity_id)) players.push(box.entity_id);
        }
      }
      return players;
    }

    // The entities of a box by their keys: those of the media player's device
    _entities(player) {
      const hass = this._hass;
      const kept = this._found.get(player);
      if (kept?.registry === hass.entities) return kept;
      const device = hass.entities?.[player]?.device_id;
      const ids = {};
      if (device) {
        for (const entry of Object.values(hass.entities)) {
          if (entry.platform === DOMAIN && entry.device_id === device && KEYS.includes(entry.translation_key)) ids[entry.translation_key] = entry.entity_id;
        }
      }
      const found = { registry: hass.entities, ids, device };
      this._found.set(player, found);
      return found;
    }

    // A box as the shared drawing takes it, read from its entities
    _read(player) {
      const hass = this._hass;
      const state = hass.states[player];
      const { ids, device } = this._entities(player);
      const of = (key) => known(hass.states[ids[key]]);
      const a = state.attributes;
      const named = hass.devices?.[device];
      const online = of("connectivity") ? of("connectivity").state === "on"
        : state.state === "off" ? false : known(state) ? true : null;
      const figure = a.media_album_name || null;
      const playing = state.state === "playing";
      const paused = state.state === "paused";
      const track = number(a.media_track);
      const level = number(a.volume_level);
      const phones = of("headphones");
      // The state in Home Assistant's own word
      const word = hass.formatEntityState ? hass.formatEntityState(state) : state.state;
      return {
        id: player,
        name: named?.name_by_user || named?.name || a.friendly_name || player,
        generation: "toniebox_2",
        image_url: a.box_picture,
        online,
        word,
        battery: number(of("battery")?.state),
        charging: of("charging")?.state === "on",
        volume: null,
        volume_percent: level === null ? null : Math.round(level * 100),
        headphones: phones?.state === "on" ? { connected: true, battery: number(phones.attributes.battery) } : null,
        sleep_timer: of("sleep_timer") ? { state: "on", until: of("sleep_timer").state } : null,
        bedtime: of("next_alarm") ? { next_alarm: { at: of("next_alarm").state, due: of("next_alarm").attributes.due === true } } : null,
        night: of("night_mode")?.state === "on" ? { mode: { enabled: true }, phase: "night" } : null,
        playback: figure || playing || paused ? {
          tonie_id: figure || player,
          tonie_name: figure,
          image_url: a.entity_picture ? hass.hassUrl(a.entity_picture) : null,
          chapter: track === null ? null : track - 1,
          chapter_title: a.media_title && a.media_title !== figure ? a.media_title : null,
          chapters: number(a.chapters),
          // Every chapter by name, length and star, for the list
          chapter_list: Array.isArray(a.chapter_list) ? a.chapter_list : [],
          // Whether the chapter that plays is a favourite; null while no chapter is known
          favourite: typeof a.favourite === "boolean" ? a.favourite : null,
          playing,
          paused,
          state_text: word,
          position: number(a.media_position),
          duration: number(a.media_duration),
          received_at: a.media_position_updated_at || null,
        } : null,
      };
    }

    // The buttons are actions of the media player, which every user may call
    async _command(player, command, value) {
      if (!this._hass || this._ctlBusy) return;
      const calls = {
        play: ["media_player.media_play", {}],
        pause: ["media_player.media_pause", {}],
        next: ["media_player.media_next_track", {}],
        previous: ["media_player.media_previous_track", {}],
        volume_up: ["media_player.volume_up", {}],
        volume_down: ["media_player.volume_down", {}],
        sleep: ["storybox_plus.set_sleep_timer", { minutes: Number(value) }],
        sleep_clear: ["storybox_plus.clear_sleep_timer", {}],
        // The chapter counted from 1, and whether it gets the star or loses it
        star: ["storybox_plus.set_favourite", { chapter: Number(value?.chapter) + 1, favourite: !!value?.favourite }],
        // The media ID names the figure, so a chapter of a figure taken off meanwhile is refused
        chapter: ["media_player.play_media", { media_content_type: "track", media_content_id: `chapter:${this._hass.states[player]?.attributes.tonie_id}:${Number(value)}` }],
      };
      const [action, data] = calls[command] || [];
      if (!ACTIONS.includes(action)) return;
      this._ctlBusy = player;
      this._ctlError = null;
      this._render();
      try {
        await this._hass.callService(...action.split("."), data, { entity_id: player });
      } catch (err) {
        // The integration's own refusals read their own line
        this._ctlError = { id: player, err: err?.translation_domain === DOMAIN && err.translation_key ? { code: err.translation_key } : err };
      }
      this._ctlBusy = null;
      this._render();
    }

    // The list of chapters of the box whose button was pressed, in Home Assistant's dialog
    _renderOverlay() {
      const host = this.shadowRoot.getElementById("overlay");
      if (!host || (!this._tracks && !host.firstElementChild)) return;
      this._renderTracks(host, this._tracks && this._hass?.states[this._tracks] ? this._read(this._tracks) : null, {
        busy: this._ctlBusy === this._tracks,
        error: this._ctlError?.id === this._tracks ? this._error(this._ctlError.err) : null,
      });
    }

    _render() {
      if (!this._hass || !this.isConnected) return;
      this._renderOverlay();
      const players = this._players();
      const boxes = (players || []).map((player) => this._read(player));
      const fixed = this._layout === "grid";
      const key = JSON.stringify([players === null, boxes, this._config, this._lang, this._textsVersion, this._hass.locale, fixed,
        this.clientWidth, this.clientHeight, this._ctlBusy || "", this._ctlError ? [this._ctlError.id, this._ctlError.err?.code || ""] : ""]);
      if (key === this._key) return;
      this._key = key;
      const root = this.shadowRoot;
      let card = root.querySelector("ha-card");
      if (!card) {
        // The frame stays: a new ha-card shows its content only once it has drawn
        // itself, so what is measured right after creating it would be nothing
        root.innerHTML = `<style>${STYLE}${CARD_STYLE}</style><ha-card><div class="content"></div></ha-card><div id="overlay"></div>`;
        card = root.querySelector("ha-card");
        this._watch();
        card.updateComplete?.then(() => {
          this._key = null;
          this._render();
        });
      }
      const content = root.querySelector(".content");
      // Draws the card and says whether its content is higher than the card
      const draw = (html, whole = false) => {
        content.className = `content${whole ? " fill" : ""}`;
        content.innerHTML = html;
        return content.scrollHeight > this._room(card) + 1;
      };
      this._drawn = null;
      const t = this._t;
      if (!boxes.length) {
        // A configured entity that is no box of ours, or no box at all
        draw(`<div class="card-content bare">${this._alert(players === null ? t.cardUnknown : t.cardMissing, players === null ? "warning" : "info")}</div>`);
        return;
      }
      const c = this._config;
      const wanted = SIZES.includes(c.size) ? [c.size] : SIZES;
      // The sizes that turned out too high for this space and these parts: Home
      // Assistant's buttons draw themselves after the card measured
      const shape = JSON.stringify([this.clientWidth, this.clientHeight, c, fixed,
        boxes.map((b) => [b.online, !!b.playback, b.playback?.playing, !!b.headphones, !!b.sleep_timer, !!b.bedtime, !!b.night, b.battery === null])]);
      if (shape !== this._shape) {
        this._shape = shape;
        this._over = new Set();
      }
      for (const size of wanted) {
        const last = size === wanted[wanted.length - 1];
        if (fixed && !last && this._over.has(size)) continue;
        const overflows = draw(this._view(boxes, size), size === "small");
        this._drawn = { size, last };
        // Only a card with a fixed height can be too small for what it shows
        if (!fixed || !overflows) break;
        this._over.add(size);
      }
      // A second line that is cut off gives way to a shorter one. Measured beside the
      // line, to the fraction of a pixel: scrollWidth and clientWidth are whole
      // numbers and call a text that is a hair too wide a fit
      for (const line of content.querySelectorAll(".sub[data-lines]")) {
        const probe = document.createElement("span");
        probe.className = line.className;
        probe.style.cssText = "position: absolute; visibility: hidden; overflow: visible; width: auto; display: inline-block;";
        line.parentElement.appendChild(probe);
        const room = line.getBoundingClientRect().width;
        for (const text of JSON.parse(line.dataset.lines)) {
          line.textContent = text;
          probe.textContent = text;
          if (probe.getBoundingClientRect().width <= room) break;
        }
        probe.remove();
      }
      this._tick();
    }

    // The card in one size. One box takes the title as its name; several get it as a heading
    _view(boxes, size) {
      const c = this._config;
      const single = boxes.length === 1;
      const heading = c.title && !single ? `<div class="heading">${esc(c.title)}</div>` : "";
      // The medium card is the large one without what only the large one has
      const shown = size === "large" ? c : { ...c, ...Object.fromEntries(DETAILS.map((part) => [`show_${part}`, false])) };
      return heading + boxes.map((box) => {
        const b = single && c.title ? { ...box, name: c.title } : box;
        if (size === "small") return this._compact(b);
        const { title, body } = this._boxParts(b, false, shown);
        return `<div class="box"><h1 class="card-header">${title}</h1><div class="card-content">${body}</div></div>`;
      }).join("");
    }

    // One row: the name with its dot, and one second line, the first of these that fits
    _compact(b) {
      const t = this._t;
      const c = this._config;
      const p = c.show_playback ? b.playback : null;
      const figure = p ? p.tonie_name || t.unknownFigure : "";
      const lines = [];
      if (b.online === false) lines.push(b.word);
      else if (p?.playing) lines.push(...(p.chapter_title ? [`${figure} · ${p.favourite ? "★ " : ""}${p.chapter_title}`] : []), figure, b.word);
      else if (p?.paused) lines.push(`${figure} · ${b.word}`, figure, b.word);
      else if (p) lines.push(figure);
      else lines.push(c.show_playback ? t.nothing : b.word);
      const pic = c.show_picture && typeof b.image_url === "string" && /^https?:\/\//i.test(b.image_url) ? `<img class="box-pic" src="${esc(b.image_url)}" alt="">` : "";
      const battery = c.show_battery && Number.isFinite(b.battery) ? `<span class="status"><span class="fact">${this._batteryLevel(b)}</span></span>` : "";
      return `<div class="compact" data-entity="${esc(b.id)}" role="button" tabindex="0">${pic}<div class="who">` +
        `<div class="name"><span>${esc(b.name)}</span>${this._dot(b)}</div>` +
        `<div class="sub" data-lines="${esc(JSON.stringify(lines))}">${esc(lines[0])}</div></div>${battery}</div>`;
    }
  }

  // Home Assistant's form over the card's schema, with the defaults filled in. Only
  // what differs from a default is written to the configuration
  class StoryboxPlusBoxCardEditor extends HTMLElement {
    setConfig(config) {
      this._config = { ...config };
      this._render();
    }

    set hass(hass) {
      this._hass = hass;
      language = hass?.locale?.language || hass?.language || language;
      // A language that is still being fetched builds the form anew once it is here
      this._textsArrived ||= () => {
        this._language = null;
        this._render();
      };
      texts(language, this._textsArrived);
      this._render();
    }

    _render() {
      if (!this._hass || !this._config) return;
      if (!this._form) {
        this._form = document.createElement("ha-form");
        this._form.addEventListener("value-changed", (e) => {
          e.stopPropagation();
          const value = { ...e.detail.value };
          for (const [name, usual] of Object.entries(DEFAULTS)) if (value[name] === usual) delete value[name];
          for (const name of ["entity", "title"]) if (!value[name]) delete value[name];
          this._config = value;
          this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: value }, bubbles: true, composed: true }));
        });
        this.appendChild(this._form);
      }
      if (this._language !== language) {
        this._language = language;
        const form = StoryboxPlusBoxCard.getConfigForm();
        this._form.schema = form.schema;
        this._form.computeLabel = form.computeLabel;
      }
      this._form.hass = this._hass;
      this._form.data = { ...DEFAULTS, ...this._config };
    }
  }

  customElements.define(CARD, StoryboxPlusBoxCard);
  customElements.define(EDITOR, StoryboxPlusBoxCardEditor);
  window.customCards = window.customCards || [];
  if (!window.customCards.some((card) => card.type === CARD)) {
    const t = texts(document.querySelector("home-assistant")?.hass?.language);
    window.customCards.push({
      type: CARD,
      name: `Storybox Plus · ${t.cardName}`,
      description: t.cardDescription,
      preview: true,
      documentationURL: "https://github.com/n-schilling/ha-storybox-plus#dashboard-card",
    });
  }
}
