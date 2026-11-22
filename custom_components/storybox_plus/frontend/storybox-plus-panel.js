// Storybox Plus panel: the page in the sidebar where administrators see their
// boxes with the live state, the figures of the household with their chapters,
// the listening statistics and the setup. Four areas (Boxes, Figures,
// Listening, Setup), each with its pages as tabs below the header, in Home
// Assistant's own frame for pages with tabs (hass-tabs-subpage): the areas in
// the header, at the bottom on a phone. A box or a figure opens as a subpage
// with a back arrow and its views as tabs. Explanations sit behind an (i) with
// Home Assistant's tooltip; errors read one line by their kind; numbers follow
// the number format of the user's profile. Everything comes from the
// integration over the WebSocket API; the version shows at the bottom of the
// setup overview.
// The boxes are asked again this often while their area is open (ms)
const REFRESH = 10000;
// A chart with more days than this groups them by week
const WEEKS_FROM = 120;

// What the page shares with the dashboard card; the version of this script keeps both in step
const {
  MDI, esc, icon, iconButton, fill, time, safeUrl, pad, hm, mmss, hours, cap, dayKey, parseDay, WEEKDAYS, clock, STYLE, BoxView,
  fieldNumber, numOrNull,
} = await import(new URL(`./storybox-plus-common.js${new URL(import.meta.url).search}`, import.meta.url).href);

if (!customElements.get("storybox-plus-panel")) {
  const PANEL_PATH = "/storybox-plus";
  // Home Assistant's own page of the integration, behind the cog in the header
  const INTEGRATION_PATH = "/config/integrations/integration/storybox_plus";
  // How often a creative figure is read again while the cloud converts its chapters (ms)
  const CONVERT_REFRESH = 15000;
  // Audio the cloud converts; the list only helps the file picker, the cloud decides
  const AUDIO_TYPES = "audio/*,.mp3,.m4a,.m4b,.aac,.ogg,.oga,.opus,.wav,.flac,.wma";

  // The four areas and their pages: area, icon, text, pages (page, text)
  const AREAS = [
    ["boxes", "boxes", "tabBoxes", [["overview", "pgBoxes"]]],
    ["figures", "figuresArea", "tabFigures", [["list", "pgFigures"], ["tunes", "pgTunes"]]],
    ["listening", "listening", "tabListening", [["summary", "pgSummary"], ["times", "pgTimes"]]],
    ["setup", "setup", "tabSetup", [["overview", "pgSetup"], ["household", "pgHousehold"], ["preferences", "pgPreferences"], ["log", "pgLog"]]],
  ];
  // The addresses of before the areas (#tab), as bookmarks still have them
  const OLD_HASH = { boxes: "boxes/overview", figures: "figures/list", listening: "listening/summary", preferences: "setup/preferences" };
  // The views of a box and of a figure: view, text
  const BOX_VIEWS = [["settings", "vSettings"], ["night", "vNight"], ["bedtimes", "vBedtimes"], ["battery", "vBattery"]];
  const FIG_VIEWS = [["chapters", "vChapters"], ["settings", "vSettings"], ["tune", "vTune"], ["add", "vAdd"]];
  const KINDS = ["all", "content", "creative", "disc"];
  // Period, days asked from the backend (null: since the setup)
  const RANGES = [["7", 7], ["30", 30], ["365", 365], ["all", null]];
  // The settings of a box by topic: group, settings
  const BOX_GROUPS = [
    ["grpGeneral", ["name", "max_volume", "max_headphone_volume", "language", "age_mode"]],
    ["grpLight", ["lightring_brightness", "led_level"]],
    ["grpBedtime", ["bedtime_lightring_brightness", "bedtime_max_volume", "bedtime_max_headphone_volume"]],
    ["grpControls", ["skipping_enabled", "skipping_direction", "scrubbing_enabled", "accelerometer_enabled", "tap_direction"]],
  ];
  // The settings of an account on the page Preferences
  const PREF_KEYS = ["analytics", "auto_lock", "mark_read"];
  // How long listening sums are kept (days, 0: all) and the bounds of the file size from the app (MB)
  const ANALYTICS_DAYS = ["365", "730", "1825", "0"];
  const FETCH_MB = [10, 2000];
  // The choice of Piper's own default voice; a select shows an empty value as none
  const DEFAULT_VOICE = "default";
  // The integration's log levels, and how many of its latest lines the page shows
  const LOG_LEVELS = ["debug", "info", "warning", "error"];
  const LOG_LINES = 500;
  const LOG_MAX_DAYS = 90;

  // In-app navigation like Home Assistant's own links, no page reload
  const navigate = (path, replace = false) => {
    if (replace) window.history.replaceState(null, "", path);
    else window.history.pushState(null, "", path);
    window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace } }));
  };

  const PAGE_STYLE = `
    hass-tabs-subpage { height: 100%; }
    .actions { display: flex; align-items: center; }
    .stamp { color: var(--secondary-text-color); font-size: var(--ha-font-size-m, 14px); white-space: nowrap;
      margin-inline-end: 4px; font-variant-numeric: tabular-nums; }
    @media (max-width: 600px) { .stamp { display: none; } }
    #refresh.spin { animation: spin 1s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .subname { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .log { font-family: var(--ha-font-family-code, ui-monospace, monospace); font-size: 12px; line-height: 1.5;
      max-height: 70vh; overflow: auto; }
    .log-line { display: flex; gap: 8px; padding: 2px 0; border-bottom: 1px solid var(--divider-color); }
    .log-time, .log-level, .log-source { flex: none; color: var(--secondary-text-color); white-space: nowrap; }
    .log-level { width: 5.5em; }
    .log-msg { flex: 1; min-width: 0; overflow-wrap: anywhere; }
    .log-line.warning .log-level { color: var(--warning-color); }
    .log-line.error .log-level, .log-line.critical .log-level { color: var(--error-color); }
    @media (max-width: 600px) { .log-line { flex-wrap: wrap; } .log-msg { flex-basis: 100%; } }
    .page { display: flex; flex-direction: column; min-height: 100%; }
    .subtabs { flex: none; padding: 0 16px; }
    .sheet { width: 100%; max-width: 1040px; margin: 0 auto; padding: 16px 16px 88px; display: flex; flex-direction: column; gap: 16px; }
    .narrow .sheet { padding: 8px 8px 88px; gap: 8px; }
    .sheet > ha-card, .sheet > ha-alert, .grid > ha-card { margin: 0; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 16px; align-items: start; }
    .narrow .grid { grid-template-columns: 1fr; gap: 8px; }
    /* The title of a card as Home Assistant draws it, with room for the (i) at its end */
    .card-header { display: flex; align-items: center; gap: 4px; margin: 0; padding: 12px 8px 12px 16px; min-height: 48px;
      color: var(--ha-card-header-color, var(--primary-text-color)); font-size: var(--ha-card-header-font-size, var(--ha-font-size-2xl, 24px));
      font-weight: var(--ha-font-weight-normal, 400); line-height: var(--ha-line-height-condensed, 1.2); }
    .card-header ha-icon-button.help { margin-inline-start: auto; }
    .card-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px; padding: 8px 16px 12px; border-top: 1px solid var(--divider-color); }
    ha-icon-button.help { --mdc-icon-button-size: 32px; --mdc-icon-size: 18px; --ha-icon-button-size: 32px; color: var(--secondary-text-color); flex: none; }
    ha-tooltip { --max-width: min(360px, 90vw); }
    .alertact { display: flex; align-items: center; gap: 4px; }
    .about { text-align: center; color: var(--secondary-text-color); font-size: var(--ha-font-size-s, 12px); padding: 8px 0 24px; }
    .loading { display: flex; justify-content: center; padding: 24px; }
    /* Settings rows as on Home Assistant's own settings pages */
    ha-settings-row { --settings-row-content-width: 100%; padding: 0 16px; }
    ha-settings-row + ha-settings-row:not([narrow]) { border-top: 1px solid var(--divider-color); }
    ha-settings-row .heading { display: inline-flex; align-items: center; gap: 2px; }
    ha-settings-row .haform { width: 240px; max-width: 100%; }
    ha-settings-row.num .haform { width: 160px; }
    ha-settings-row.bool .haform { width: auto; }
    ha-settings-row[narrow] .haform { width: 100%; }
    ha-settings-row .value { color: var(--secondary-text-color); }
    ha-card.rows .card-content { padding: 0 0 8px; }
    /* Rows of a list; a row that opens something reacts to the mouse and the keyboard */
    ha-card.list .card-content { padding: 0 0 8px; }
    .item { display: flex; align-items: center; gap: 12px; padding: 8px 16px; min-height: 56px; }
    .item + .item { border-top: 1px solid var(--divider-color); }
    .item[role=button] { cursor: pointer; outline: none; }
    .item[role=button]:hover, .item[role=button]:focus-visible { background: color-mix(in srgb, var(--primary-text-color) 5%, transparent); }
    .item > ha-svg-icon.go { color: var(--secondary-text-color); }
    .item .text { display: flex; flex: 1; flex-direction: column; min-width: 0; }
    .item .main { flex: 1; min-width: 0; display: flex; align-items: center; gap: 12px; cursor: pointer; outline: none; border-radius: 8px; }
    .item .main:focus-visible { background: color-mix(in srgb, var(--primary-text-color) 5%, transparent); }
    .badges { display: inline-flex; flex-wrap: wrap; align-items: center; justify-content: flex-end; gap: 4px; flex: none; }
    .narrow .badges { max-width: 40%; }
    .lock { display: inline-flex; color: var(--secondary-text-color); }
    .lock ha-svg-icon { --mdc-icon-size: 18px; }
    .filters { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center; }
    .filters .haform { flex: 1 1 260px; min-width: 0; }
    .count { margin: 0 0 0 4px; }
    .bar-row { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 0 0 8px; }
    .form-row { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; }
    .form-row .haform { flex: 1 1 260px; min-width: 0; }
    .card-content .haform + .bar-row, .card-content ha-alert { margin-top: 8px; }
    .card-content ha-alert { display: block; }
    .chapters { list-style: none; margin: 0; padding: 0; }
    .chapters li { display: flex; align-items: center; gap: 10px; padding: 2px 0; min-height: 40px; line-height: 20px; }
    .chapters li + li { border-top: 1px solid var(--divider-color); }
    .chapters .no { flex: none; min-width: 24px; text-align: right; }
    .ch-title { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .ch-tools { display: inline-flex; flex: none; margin-right: -8px; }
    ha-icon-button.star.on { color: var(--state-active-color, var(--amber-color, #ffc107)); }
    ha-icon-button.danger:hover { color: var(--error-color); }
    .head-fig { display: flex; align-items: center; gap: 16px; }
    .head-fig .pic { width: 72px; height: 72px; }
    .member-avatar { flex: none; width: 32px; height: 32px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center;
      font-weight: var(--ha-font-weight-medium, 500); background: color-mix(in srgb, var(--primary-color) 16%, transparent); color: var(--primary-color); }
    .step { flex: none; width: 32px; height: 32px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center;
      background: color-mix(in srgb, var(--primary-text-color) 8%, transparent); color: var(--secondary-text-color); }
    .step.done { background: color-mix(in srgb, var(--success-color) 18%, transparent); color: var(--success-color); }
    .alarm-mark { display: inline-flex; vertical-align: middle; color: var(--secondary-text-color); }
    .alarm-mark ha-svg-icon { --mdc-icon-size: 16px; }
    .sched-form { padding: 8px 16px 12px; }
    .sched-form .haform { display: block; margin-bottom: 8px; }
    .batt-big { display: flex; align-items: center; gap: 8px; font-size: var(--ha-font-size-2xl, 24px); margin: 0 0 6px; }
    table { border-collapse: collapse; width: 100%; }
    table.cycles th, table.cycles td { padding: 4px 10px 4px 0; text-align: left; white-space: nowrap; font-variant-numeric: tabular-nums; }
    table.cycles th { font-weight: var(--ha-font-weight-normal, 400); font-size: var(--ha-font-size-xs, 12px); color: var(--secondary-text-color); }
    table.cycles th:last-child, table.cycles td:last-child { width: 100%; padding-right: 0; }
    table.cycles tbody tr + tr td { border-top: 1px solid var(--divider-color); }
    .scroll { overflow-x: auto; }
    .pf { display: flex; align-items: center; gap: 8px; }
    .pf .bar { flex: 1 1 32px; height: 5px; }
    .pf span { min-width: 44px; text-align: right; color: var(--secondary-text-color); }
    ha-control-select.range { max-width: 520px; --control-select-thickness: 40px; }
    .total { display: flex; align-items: baseline; gap: 6px; }
    .total .big { font-size: 44px; line-height: 52px; font-weight: 300; font-variant-numeric: tabular-nums; }
    .total .unit { font-size: var(--ha-font-size-l, 18px); color: var(--secondary-text-color); }
    .compare { margin-top: 8px; }
    .top { list-style: none; margin: 0; padding: 0; }
    .top li { display: flex; align-items: center; gap: 12px; padding: 6px 0; }
    .top li + li { border-top: 1px solid var(--divider-color); }
    .rank { flex: none; width: 20px; text-align: right; }
    .top .bar { margin-top: 6px; height: 5px; }
    .top .len { min-width: 44px; text-align: right; }
    table.kv th { text-align: left; font-weight: var(--ha-font-weight-normal, 400); padding: 8px 16px 8px 0; }
    table.kv td { padding: 8px 0; text-align: right; color: var(--secondary-text-color); font-variant-numeric: tabular-nums; white-space: nowrap; }
    table.kv tr + tr th, table.kv tr + tr td { border-top: 1px solid var(--divider-color); }
    .chart { width: 100%; height: auto; display: block; }
    .chart .grid { stroke: var(--divider-color); stroke-width: 1; vector-effect: non-scaling-stroke; }
    .chart text { fill: var(--secondary-text-color); font-size: 12px; }
    .chart .fill { fill: var(--primary-color); pointer-events: none; }
    .chart .hit { fill: transparent; }
    .chart .hit:hover { fill: color-mix(in srgb, var(--primary-text-color) 6%, transparent); }
    .heat-boxes { margin-bottom: 12px; }
    .heatmap { display: grid; grid-template-columns: auto repeat(24, minmax(0, 1fr)); gap: 2px; align-items: center; }
    .hm-day { font-size: var(--ha-font-size-xs, 12px); color: var(--secondary-text-color); padding-right: 6px; }
    .hm-cell { aspect-ratio: 1; border-radius: 2px; min-height: 8px;
      background: color-mix(in srgb, var(--primary-color) calc(var(--a) * 100%), color-mix(in srgb, var(--primary-text-color) 6%, transparent)); }
    .hm-hour { font-size: var(--ha-font-size-xs, 11px); color: var(--secondary-text-color); }
    .len, .no, .rank { color: var(--secondary-text-color); font-variant-numeric: tabular-nums; }
  `;

  class StoryboxPlusPanel extends BoxView(HTMLElement) {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._area = "boxes";
      this._page = "overview";
      // The box or figure open as a subpage, and its view
      this._key = null;
      this._view = null;
      this._overview = null;
      this._library = null;
      this._stats = {};
      // Errors of the data the page shows, by the key of _fetch: { text, detail }
      this._errors = {};
      // When each kind of data last came from the integration, for the stamp in the header
      this._stamps = {};
      this._loading = new Set();
      this._query = "";
      this._kind = "all";
      this._range = "30";
      this._heatBox = "";
      this._frameKey = null;
      this._sheetHtml = null;
      // Settings typed but not saved: scope ("box:<id>", "night:<id>", "fig:<id>",
      // "home:<id>", "pref:<entry>") -> { setting: value }; one save button for them
      this._drafts = {};
      this._saving = false;
      // An error of the last action, shown above the page: { text, detail }
      this._note = null;
      // A line that says what an action did: { kind, text }
      this._done = null;
      // The chapters of one creative figure being rearranged: { id, chapters, saving, renaming, clearStep }
      this._edit = null;
      // Uploads per creative figure: { total, done, name, error, link, stage, pct }
      this._uploads = {};
      // The forms to add from a link and from a text, per figure
      this._link = {};
      this._speak = {};
      // Content from a code: { tonie, token, busy }
      this._code = { tonie: null, token: "", busy: false };
      // Vouchers per account: { code, busy, done }
      this._voucher = {};
      this._tunePick = {};
      // The bedtime being edited: { box, id (null: new), data, saving, confirm }
      this._sched = null;
      this._uploadTarget = null;
      // The forms on the sheet: id -> { schema, data, onChange, aria }, drawn as ha-form
      this._forms = {};
      // The (i) of the page drawn: a fresh id each
      this._hid = 0;
      this._bindOnce();
      this._upgrade(["hass", "narrow", "route", "panel"]);
    }

    set hass(hass) {
      const first = !this._hass;
      const lang = this._hass?.language;
      this._hass = hass;
      if (first) {
        this._ensure(true);
        this._syncTimers();
      }
      if (first || hass.language !== lang) this._render();
      // The frame and the forms need the new hass
      for (const el of this.shadowRoot.querySelectorAll("hass-tabs-subpage, ha-form")) el.hass = hass;
    }

    set narrow(narrow) {
      if (this._narrow === narrow) return;
      this._narrow = narrow;
      this._render();
    }

    // The address: /<area>/<page>, a box or figure ?key=…, its view &view=…; an old
    // address (#tab) goes to its new place, an area alone to its first page, nothing
    // to the boxes (to the setup while no account is loaded)
    set route(route) {
      const parts = (route?.path || "").split("/").filter(Boolean);
      const { pathname, search, hash } = window.location;
      const old = OLD_HASH[(hash || "").slice(1)];
      if (!parts.length && old) {
        navigate(`${PANEL_PATH}/${old}`, true);
        return;
      }
      const area = AREAS.find((a) => a[0] === parts[0]);
      if (!area) {
        this._defaulted = true;
        navigate(`${PANEL_PATH}/boxes/overview`, true);
        return;
      }
      if (!area[3].some(([p]) => p === parts[1])) {
        navigate(`${PANEL_PATH}/${area[0]}/${area[3][0][0]}${search}`, true);
        return;
      }
      // The same address again (Home Assistant after the query was read): nothing to do
      if (pathname + search === this._href && this._area === area[0] && this._page === parts[1]) return;
      this._href = pathname + search;
      this._route = { prefix: PANEL_PATH, path: `/${area[0]}/${parts[1]}` };
      const query = new URLSearchParams(search);
      this._setPage(area[0], parts[1], query.get("key"), query.get("view"));
    }

    set panel(panel) {
      this._panelInfo = panel;
    }

    connectedCallback() {
      // Home Assistant passes a new route only when the path changes: an address that
      // changes only its query (another box, &view=night) is read here
      this._onLocation = () => {
        const { pathname, search } = window.location;
        if (!pathname.startsWith(`${PANEL_PATH}/`) || pathname + search === this._href) return;
        this.route = { prefix: PANEL_PATH, path: pathname.slice(PANEL_PATH.length) };
      };
      this._onVisible = () => {
        this._syncTimers();
        if (document.visibilityState === "visible") this._ensure(true);
      };
      window.addEventListener("location-changed", this._onLocation);
      window.addEventListener("popstate", this._onLocation);
      document.addEventListener("visibilitychange", this._onVisible);
      this._syncTimers();
      if (this._hass) this._ensure();
    }

    disconnectedCallback() {
      window.removeEventListener("location-changed", this._onLocation);
      window.removeEventListener("popstate", this._onLocation);
      document.removeEventListener("visibilitychange", this._onVisible);
      this._syncTimers();
    }

    // Changing the page: from a tab, a row, the address
    _setPage(area, page, key, view) {
      const fresh = area !== this._area;
      const changed = fresh || page !== this._page || (key || null) !== this._key;
      this._area = area;
      this._page = page;
      this._key = key || null;
      this._view = view || null;
      if (changed) {
        this._note = null;
        this._done = null;
        this._drafts = {};
        this._sched = null;
        this._edit = null;
      }
      this._ensure(fresh);
      this._syncTimers();
      this._render();
    }

    _go(path) {
      navigate(path.startsWith("/") ? path : `${PANEL_PATH}/${path}`);
    }

    // A box or a figure opened from a list: a subpage
    get _sub() {
      if (!this._key) return null;
      if (this._area === "boxes") return "box";
      if (this._area === "figures" && this._page === "list") return "fig";
      return null;
    }

    // ---- Data ----

    // Loads what the open page shows; every page needs the overview once, for the
    // accounts, the version and, on the figures, the boxes' names
    _ensure(fresh = false) {
      if (!this._hass || document.visibilityState === "hidden") return;
      const area = this._area;
      if (fresh || !this._overview || area === "boxes" || area === "setup") this._loadOverview();
      const lib = area === "figures" || (area === "setup" && this._page === "overview");
      if (lib && (fresh || !this._library)) this._loadLibrary();
      if (area === "listening" && (fresh || !this._stats[this._range])) this._loadStats(this._range);
      if (area === "setup" && this._page === "log") this._loadLog();
    }

    // The boxes are polled and their progress ticks only while their area shows; the
    // figures are watched for a conversion only while theirs does
    _syncTimers() {
      const visible = this.isConnected && document.visibilityState === "visible";
      const live = visible && this._area === "boxes";
      if (live && !this._poll) {
        // While a bedtime or a setting is being changed, the page stays as it is
        this._poll = window.setInterval(() => {
          if (!this._sched && !this._dirty && !this._typing()) this._loadOverview();
        }, REFRESH);
        this._ticker = window.setInterval(() => this._tick(), 1000);
      } else if (!live && this._poll) {
        window.clearInterval(this._poll);
        window.clearInterval(this._ticker);
        this._poll = this._ticker = null;
      }
      const figures = visible && this._area === "figures";
      if (figures && !this._convPoll) {
        this._convPoll = window.setInterval(() => this._refreshConverting(), CONVERT_REFRESH);
      } else if (!figures && this._convPoll) {
        window.clearInterval(this._convPoll);
        this._convPoll = null;
      }
    }

    async _fetch(key, msg, keep) {
      if (!this._hass || this._loading.has(key)) return;
      this._loading.add(key);
      this._update();
      try {
        keep(await this._hass.callWS(msg));
        this._stamps[key] = new Date();
        delete this._errors[key];
      } catch (err) {
        this._errors[key] = this._error(err);
      }
      this._loading.delete(key);
      this._render();
    }

    _loadOverview() {
      return this._fetch("overview", { type: "storybox_plus/overview" }, (d) => {
        this._overview = d;
        this._keepVolume();
        // Opened without an address while no account is loaded: the setup is where to start
        if (this._defaulted) {
          this._defaulted = false;
          if (!d.entries.some((e) => e.loaded) && this._area === "boxes" && !this._key) navigate(`${PANEL_PATH}/setup/overview`, true);
        }
      });
    }

    _loadLibrary() {
      return this._fetch("library", { type: "storybox_plus/library" }, (d) => { this._library = d; });
    }

    _loadLog() {
      return this._fetch("log", { type: "storybox_plus/log", limit: LOG_LINES }, (d) => { this._log = d; });
    }

    _loadStats(range) {
      const days = RANGES.find(([k]) => k === range)?.[1] ?? null;
      return this._fetch(`stats:${range}`, { type: "storybox_plus/analytics", days, limit: 10 }, (d) => { this._stats[range] = d; });
    }

    // The data the open page shows, by the key of _fetch: the stamp and the spinning
    // refresh button in the header are about these
    get _dataKey() {
      if (this._area === "figures") return "library";
      if (this._area === "listening") return `stats:${this._range}`;
      if (this._area === "setup" && this._page === "log") return "log";
      return "overview";
    }

    _boxById(id) {
      return this._overview?.boxes.find((b) => b.id === id) || null;
    }

    _figure(id) {
      return this._library?.tonies.find((x) => x.id === id) || null;
    }

    _loadedEntries() {
      return (this._overview?.entries || []).filter((e) => e.loaded && e.preferences);
    }

    // The households of the accounts; one shared by two accounts shows once
    _households() {
      const seen = new Map();
      for (const e of this._loadedEntries()) for (const h of e.households || []) if (!seen.has(h.id)) seen.set(h.id, { ...h, entry: e });
      return [...seen.values()];
    }

    // A box as the integration answered it replaces the one in the overview
    _replaceBox(box) {
      const boxes = this._overview?.boxes || [];
      const i = boxes.findIndex((x) => x.id === box?.id);
      if (i >= 0) boxes[i] = box;
    }

    // A figure as the cloud answered it replaces the one in the library
    _replaceTonie(tonie) {
      if (!tonie?.id || !this._library) return;
      const i = this._library.tonies.findIndex((x) => x.id === tonie.id);
      if (i >= 0) this._library.tonies[i] = tonie;
      else this._library.tonies.push(tonie);
    }

    // ---- Settings typed but not saved ----

    // The values saved for a scope; null when its thing is gone
    _saved(scope) {
      const [kind, id] = scope.split(/:(.*)/s);
      if (kind === "box") {
        const b = this._boxById(id);
        if (!b?.settings) return null;
        const values = { name: b.name || "", ...b.settings.values };
        // A Toniebox 1 knows four steps, chosen from a list of words
        if (b.generation !== "toniebox_2") {
          for (const k of ["max_volume", "max_headphone_volume"]) if (k in values) values[k] = String(values[k]);
          // Kept in Home Assistant, not in the cloud: the entity that tells whether the box is in the network
          values.presence_entity = b.presence_entity || null;
        }
        return values;
      }
      if (kind === "night") {
        const b = this._boxById(id);
        if (!b?.night) return null;
        const m = b.night.mode;
        const ring = b.settings?.values?.lightring_brightness;
        return m
          ? { enabled: !!m.enabled, start: m.start, end: m.end, night: m.night, day: m.day }
          : { enabled: false, start: "19:00", end: "07:00", night: 10, day: Number.isFinite(ring) ? ring : 60 };
      }
      if (kind === "fig") {
        const f = this._figure(id);
        if (!f) return null;
        const values = { volume: f.volume ? String(f.volume) : "box" };
        if (f.kind === "creative") {
          values.name = f.name;
          values.live = !!f.live;
          if (f.chapters.length > 1) values.shuffle_on_swap = !!f.shuffle_on_swap;
        } else {
          values.locked = !!f.locked;
          if (f.favourites) values.favourites = !!f.favourites.active;
        }
        return values;
      }
      if (kind === "home") {
        const h = this._households().find((x) => x.id === id);
        return h ? { name: h.name || "" } : null;
      }
      if (kind === "pref") {
        const p = this._loadedEntries().find((e) => e.entry_id === id)?.preferences;
        if (!p) return null;
        return {
          ...Object.fromEntries(PREF_KEYS.map((k) => [k, !!p[k]])),
          analytics_days: String(p.analytics_days ?? 730),
          voice: p.voice ? `${p.voice_language}|${p.voice}` : DEFAULT_VOICE,
          fetch_max_mb: p.fetch_max_mb ?? 200,
        };
      }
      if (kind === "log") return this._log ? { level: this._log.level, days: this._log.days } : null;
      return null;
    }

    _value(scope, name) {
      const d = this._drafts[scope];
      return d && name in d ? d[name] : this._saved(scope)?.[name];
    }

    _same(a, b) {
      if (typeof a === "number" || typeof b === "number") return a != null && b != null && Number(a) === Number(b);
      if (typeof a === "string" && typeof b === "string") return a.trim() === b.trim();
      return (a ?? null) === (b ?? null);
    }

    // What differs from the saved values
    _changed(scope) {
      const d = this._drafts[scope];
      const s = this._saved(scope);
      if (!d || !s) return {};
      return Object.fromEntries(Object.entries(d).filter(([k, v]) => k in s && !this._same(v, s[k])));
    }

    // The settings shown on the page open
    get _pageScopes() {
      const sub = this._sub;
      if (sub === "box") return this._boxView === "night" ? [`night:${this._key}`] : this._boxView === "settings" ? [`box:${this._key}`] : [];
      if (sub === "fig") return this._figView === "settings" ? [`fig:${this._key}`] : [];
      if (this._area === "setup" && this._page === "household") return this._households().map((h) => `home:${h.id}`);
      if (this._area === "setup" && this._page === "preferences") return this._loadedEntries().map((e) => `pref:${e.entry_id}`);
      if (this._area === "setup" && this._page === "log") return this._log ? ["log:all"] : [];
      return [];
    }

    get _dirty() {
      return this._pageScopes.some((s) => Object.keys(this._changed(s)).length > 0);
    }

    _setDraft(scope, name, value) {
      (this._drafts[scope] ||= {})[name] = value;
      this._update();
    }

    // The save button: every changed setting of the page, each scope in one call or a few
    async _save() {
      if (this._saving || !this._hass) return;
      const scopes = this._pageScopes.filter((s) => Object.keys(this._changed(s)).length);
      if (!scopes.length) return;
      this._saving = true;
      this._note = null;
      this._update();
      try {
        for (const scope of scopes) {
          await this._saveScope(scope, this._changed(scope));
          delete this._drafts[scope];
        }
      } catch (err) {
        this._note = this._error(err);
      }
      this._saving = false;
      this._render();
    }

    async _saveScope(scope, ch) {
      const [kind, id] = scope.split(/:(.*)/s);
      const invalid = () => {
        throw { code: "invalid_format", message: "" };
      };
      const num = (v) => (Number.isFinite(Number(v)) && v !== null && v !== "" ? Math.round(Number(v)) : invalid());
      const ws = (msg) => this._hass.callWS(msg);
      if (kind === "box") {
        const saved = this._saved(scope);
        const msg = { type: "storybox_plus/box/settings", box_id: id };
        for (const [k, v] of Object.entries(ch)) {
          if (k === "name") msg.name = String(v || "").trim() || invalid();
          else if (k === "presence_entity") msg[k] = v || null;
          else if (typeof saved[k] === "number" || k === "max_volume" || k === "max_headphone_volume") msg[k] = num(v);
          else msg[k] = v;
        }
        this._replaceBox(await ws(msg));
      } else if (kind === "night") {
        const d = { ...this._saved(scope), ...this._drafts[scope] };
        const start = clock(d.start) || invalid();
        const end = clock(d.end) || invalid();
        this._replaceBox(await ws({ type: "storybox_plus/night/set", box_id: id, enabled: !!d.enabled, start, end, night: num(d.night), day: num(d.day) }));
      } else if (kind === "fig") {
        const f = this._figure(id);
        if ("name" in ch || "live" in ch) {
          const msg = { type: "storybox_plus/figure/update", tonie_id: id };
          if ("name" in ch) msg.name = String(ch.name || "").trim() || invalid();
          if ("live" in ch) msg.live = !!ch.live;
          this._replaceTonie(await ws(msg));
        }
        const fig = () => this._figure(id) || f;
        if ("volume" in ch) {
          fig().volume = (await ws({ type: "storybox_plus/figure/volume", tonie_id: id, level: ch.volume === "box" ? null : Number(ch.volume) })).volume;
        }
        if ("locked" in ch) fig().locked = (await ws({ type: "storybox_plus/figure/lock", tonie_id: id, locked: !!ch.locked })).locked;
        if ("shuffle_on_swap" in ch) {
          fig().shuffle_on_swap = (await ws({ type: "storybox_plus/figure/shuffle_on_swap", tonie_id: id, enabled: !!ch.shuffle_on_swap })).shuffle_on_swap;
        }
        if ("favourites" in ch && fig().favourites) {
          fig().favourites = (await ws({ type: "storybox_plus/favourites/set", tonie_id: id, chapters: fig().favourites.chapters, active: !!ch.favourites })).favourites;
        }
      } else if (kind === "home") {
        const name = String(ch.name || "").trim() || invalid();
        const answer = await ws({ type: "storybox_plus/household/rename", household_id: id, name });
        for (const e of this._loadedEntries()) {
          for (const h of e.households || []) {
            if (h.id !== id) continue;
            h.name = name;
            e.title = answer.entry_title;
          }
        }
      } else if (kind === "log") {
        const msg = { type: "storybox_plus/log/set" };
        if ("level" in ch) msg.level = ch.level;
        if ("days" in ch) {
          msg.days = num(ch.days);
          if (msg.days < 0 || msg.days > LOG_MAX_DAYS) invalid();
        }
        const answer = await ws(msg);
        this._log = { ...this._log, level: answer.level, days: answer.days, effective: answer.effective };
        this._loadLog();
      } else if (kind === "pref") {
        const entry = this._loadedEntries().find((e) => e.entry_id === id);
        const msg = { type: "storybox_plus/preferences/set", entry_id: id };
        for (const k of PREF_KEYS) if (k in ch) msg[k] = ch[k];
        if ("analytics_days" in ch) msg.analytics_days = Number(ch.analytics_days);
        if ("fetch_max_mb" in ch) {
          msg.fetch_max_mb = num(ch.fetch_max_mb);
          if (msg.fetch_max_mb < FETCH_MB[0] || msg.fetch_max_mb > FETCH_MB[1]) invalid();
        }
        if ("voice" in ch) {
          const [language, voice] = ch.voice === DEFAULT_VOICE ? [] : String(ch.voice || "").split("|");
          msg.voice = voice || null;
          msg.voice_language = voice ? language : null;
        }
        entry.preferences = await ws(msg);
        if ("analytics" in ch) {
          // The integration sets the account up anew; the counted sums change with it
          this._stats = {};
          window.setTimeout(() => this._loadOverview(), 4000);
        }
      }
    }

    // ---- Events ----

    // One listener each on the shadow root: the content under it is redrawn
    _bindOnce() {
      const root = this.shadowRoot;
      root.addEventListener("click", (e) => {
        const target = e.target.closest?.("[data-act]");
        // A switch tells its new state with "change"
        if (!target || target.tagName === "HA-SWITCH" || target.hasAttribute("disabled")) return;
        this._act(target.dataset.act, target);
      });
      // Rows that open something are buttons: Enter and Space open them;
      // Enter in the link field adds the link, as the button does
      root.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && e.target.closest?.(".haform[data-enter]")) {
          e.preventDefault();
          const slot = e.target.closest(".haform[data-enter]");
          this._act(slot.dataset.enter, slot);
          return;
        }
        const row = e.target.closest?.("[role=button][data-act]");
        if (!row || e.target !== row || (e.key !== "Enter" && e.key !== " ")) return;
        e.preventDefault();
        row.click();
      });
      root.addEventListener("change", (e) => {
        const sw = e.target.closest?.("ha-switch[data-act]");
        if (sw) this._act(sw.dataset.act, sw);
        // The hidden file field of the frame serves every creative figure in turn
        if (e.target.id === "upload") {
          const files = [...e.target.files];
          e.target.value = "";
          if (this._uploadTarget && files.length) this._uploadFiles(this._uploadTarget, files);
        }
      });
      // The period and the box of the heatmap: Home Assistant's segmented control
      root.addEventListener("value-changed", (e) => {
        const el = e.target;
        if (el.tagName !== "HA-CONTROL-SELECT") return;
        const value = e.detail?.value ?? "";
        if (el.id === "range" && value && value !== this._range) {
          this._range = value;
          this._loadStats(value);
          this._render();
        }
        if (el.id === "heatbox") {
          this._heatBox = value === "*" ? "" : value;
          this._render();
        }
      });
      // Home Assistant's tabs: the pages of an area, the views of a box or a figure
      root.addEventListener("wa-tab-show", (e) => {
        const name = e.detail?.name;
        if (!name) return;
        if (e.target?.id === "subtabs" && name !== this._page) this._go(`${this._area}/${name}`);
        if (e.target?.id === "views" && name !== this._shownView) {
          this._go(`${this._area}/${this._page}?key=${encodeURIComponent(this._key)}&view=${name}`);
        }
      });
      // A picture that does not load leaves the placeholder behind it visible
      root.addEventListener("error", (e) => {
        if (e.target?.tagName === "IMG") e.target.classList.add("broken");
      }, true);
    }

    // Buttons, rows and switches: "verb" or "verb:argument"
    _act(act, el) {
      const [verb, arg = ""] = act.split(/:(.*)/s);
      const key = el?.dataset?.key;
      switch (verb) {
        case "refresh":
          this._ensure(true);
          return;
        case "integration":
          this._go(INTEGRATION_PATH);
          return;
        case "save":
          this._save();
          return;
        case "logcopy":
          this._copyLog();
          return;
        case "logsave":
          this._downloadLog();
          return;
        case "go":
          this._go(key);
          return;
        case "boxset":
          this._go(`boxes/overview?key=${encodeURIComponent(arg)}&view=settings`);
          return;
        case "battset":
          this._go(`boxes/overview?key=${encodeURIComponent(arg)}&view=battery`);
          return;
        case "openfig":
          this._go(`figures/list?key=${encodeURIComponent(key)}`);
          return;
        case "kind":
          this._kind = key;
          this._refreshList();
          return;
        case "ctl": {
          const [boxId, command, value] = arg.split(":");
          this._command(boxId, command, value);
          return;
        }
        case "repeat": {
          const [boxId, mode] = arg.split(":");
          this._setRepeat(boxId, mode === "off" ? null : mode);
          return;
        }
        case "tracks":
          this._tracks = arg;
          this._update();
          return;
        case "jump": {
          // The list closes; what the box says to the jump shows on its card
          const [boxId, index] = arg.split(":");
          this._tracks = null;
          this._update();
          this._command(boxId, "chapter", index);
          return;
        }
        case "voucher":
          this._redeemVoucher(arg);
          return;
        case "codeadd":
          this._redeemCode();
          return;
        case "tuneon": {
          const pick = this._tunePick[arg] || this._tunesFor(arg)[0]?.id;
          if (pick) this._setTune(arg, pick);
          return;
        }
        case "tuneoff":
          this._setTune(arg, null);
          return;
        case "dismiss":
          if (arg === "done") this._done = null;
          else delete this._uploads[arg];
          this._render();
          return;
        default:
          break;
      }
      if (/^s(add|edit|save|cancel|del|delok|delno|on)$/.test(verb)) this._scheduleAction(verb, arg);
      else this._chapterAction(verb, arg);
    }

    // ---- Building blocks, as Home Assistant draws them ----

    // The (i): Home Assistant's icon button with its tooltip; a tap or Enter shows it, as hovering does
    _help(text) {
      if (!text) return "";
      const id = `help${++this._hid}`;
      return `<ha-icon-button class="help" id="${id}" path="${MDI.info}" label="${esc(this._t.info)}"></ha-icon-button>` +
        `<ha-tooltip for="${id}" placement="top" trigger="hover click">${esc(text)}</ha-tooltip>`;
    }

    // A card of Home Assistant; its title with an (i) when the card has something to explain
    _section(title, body, { help = "", cls = "", actions = "" } = {}) {
      const head = title ? `<h1 class="card-header">${esc(title)}${this._help(help)}</h1>` : "";
      return `<ha-card class="${cls}">${head}<div class="card-content${title ? "" : " bare"}">${body}</div>` +
        `${actions ? `<div class="card-actions">${actions}</div>` : ""}</ha-card>`;
    }

    // One line of state, the why behind its (i), maybe an action
    _alertHelp(kind, text, help = "", action = "") {
      const end = action || help ? `<span slot="action" class="alertact">${action}${this._help(help)}</span>` : "";
      return `<ha-alert alert-type="${kind}">${esc(text)}${end}</ha-alert>`;
    }

    // An error: one line by its kind, what Home Assistant said behind the (i)
    _errHtml(e) {
      return this._alertHelp("error", e.text, e.detail ? `${this._t.errDetail}: ${e.detail}` : "");
    }

    // kind: "plain" (the default), "filled" (the main action of a group), "danger"
    _btn(act, label, ic, { look = "plain", disabled = false, data = "" } = {}) {
      const kind = look === "filled" ? "" : look === "danger" ? ' appearance="plain" variant="danger"' : ' appearance="plain"';
      return `<ha-button${kind} data-act="${esc(act)}"${data}${disabled ? " disabled" : ""}>` +
        `${ic ? `<ha-svg-icon slot="start" path="${MDI[ic]}"></ha-svg-icon>` : ""}${esc(label)}</ha-button>`;
    }

    _loadingHtml() {
      return `<div class="loading"><ha-spinner aria-label="${esc(this._t.loading)}"></ha-spinner></div>`;
    }

    // A row of a list that opens something: a button for the mouse and the keyboard
    _item(act, key, lead, title, sub = "", end = "") {
      return `<div class="item" role="button" tabindex="0" data-act="${esc(act)}" data-key="${esc(key)}">${lead}` +
        `<div class="text"><span class="headline">${esc(title)}</span>${sub ? `<span class="supporting">${sub}</span>` : ""}</div>` +
        `${end}${icon("chevronRight").replace("<ha-svg-icon", '<ha-svg-icon class="go"')}</div>`;
    }

    // An ha-form with Home Assistant's selectors; drawn after the sheet's HTML.
    // The data is part of the placeholder, so a change from outside redraws it.
    // aria: the name of a field whose label stands beside it (a settings row);
    // enter: the action Enter in the field starts
    _formSlot(id, schema, data, onChange, { aria = "", enter = "" } = {}) {
      const clean = Object.fromEntries(Object.entries(data).filter(([, v]) => v !== null && v !== undefined));
      this._forms[id] = { schema, data: clean, onChange, aria };
      return `<div class="haform" data-form="${esc(id)}"${enter ? ` data-enter="${esc(enter)}"` : ""} data-v="${esc(JSON.stringify(clean))}"></div>`;
    }

    // A setting: its name with its (i), the field at the end
    _row(scope, name, label, help, selector, num = false) {
      // A choice always holds one of its options: no × that empties it
      const field = { name, label: "", selector, num, required: !!selector.select };
      const time = !!selector.time;
      const slot = this._formSlot(`${scope}:${name}`, [field], { [name]: this._value(scope, name) },
        (v) => this._setDraft(scope, name, time ? clock(v[name]) : v[name] ?? null), { aria: label });
      const kind = selector.boolean ? "bool" : num ? "num" : "other";
      return `<ha-settings-row class="${kind}"${this._narrow ? " narrow" : ""} wrap-heading>` +
        `<span slot="heading" class="heading">${esc(label)}${this._help(help)}</span>${slot}</ha-settings-row>`;
    }

    // A row of facts in the shape of a setting, for what is shown only
    _infoRow(label, help, value) {
      return `<ha-settings-row${this._narrow ? " narrow" : ""} wrap-heading>` +
        `<span slot="heading" class="heading">${esc(label)}${this._help(help)}</span><span class="value">${esc(value)}</span></ha-settings-row>`;
    }

    // The input deep in Home Assistant's field gets the name the row shows beside it
    async _ariaName(form, name, tries = 10) {
      await form.updateComplete;
      const find = (root) => {
        for (const el of root.querySelectorAll("*")) {
          if (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.getAttribute("role") === "switch" || el.getAttribute("role") === "combobox") return el;
          const deep = el.shadowRoot && find(el.shadowRoot);
          if (deep) return deep;
        }
        return null;
      };
      const input = form.shadowRoot && find(form.shadowRoot);
      if (input) input.setAttribute("aria-label", name);
      else if (tries > 0) setTimeout(() => this._ariaName(form, name, tries - 1), 100);
    }

    _hydrate(root) {
      for (const slot of root.querySelectorAll("[data-form]")) {
        const spec = this._forms[slot.dataset.form];
        if (!spec) continue;
        const form = document.createElement("ha-form");
        form.hass = this._hass;
        form.narrow = !!this._narrow;
        form.schema = spec.schema;
        // Numbers go into the fields as text in the number format, and come back as numbers
        const nums = new Set();
        const walk = (schema) => {
          for (const f of schema) {
            if (f.num) nums.add(f.name);
            if (f.schema) walk(f.schema);
          }
        };
        walk(spec.schema);
        const shown = (d) => Object.fromEntries(Object.entries(d).map(([k, v]) => [k, nums.has(k) && typeof v === "number" ? fieldNumber(this._hass, v) : v]));
        const read = (d) => Object.fromEntries(Object.entries(d).map(([k, v]) => [k, nums.has(k) ? (v === "" || v == null ? null : numOrNull(v)) : v]));
        form.data = shown(spec.data);
        form.computeLabel = (s) => s.label ?? s.name;
        if (spec.aria) this._ariaName(form, spec.aria);
        form.addEventListener("value-changed", (e) => {
          e.stopPropagation();
          form.data = e.detail.value;
          spec.onChange(read(e.detail.value));
        });
        slot.append(form);
      }
      // Home Assistant's segmented control takes its options as a property
      for (const el of root.querySelectorAll("ha-control-select[data-options]")) {
        el.options = JSON.parse(el.dataset.options);
        el.value = el.dataset.value;
      }
    }

    // A redraw while a field has the focus would lose the input
    _typing() {
      const el = this.shadowRoot.activeElement;
      return !!el && el.tagName === "HA-FORM";
    }

    // ---- Drawing ----

    // The view of the box or figure open: the one in the address, if it has it
    get _boxView() {
      const b = this._boxById(this._key);
      const views = b ? this._boxViews(b) : [];
      return views.find(([v]) => v === this._view)?.[0] || views[0]?.[0] || null;
    }

    get _figView() {
      const f = this._figure(this._key);
      const views = f ? this._figViews(f) : [];
      return views.find(([v]) => v === this._view)?.[0] || views[0]?.[0] || null;
    }

    get _shownView() {
      return this._sub === "box" ? this._boxView : this._sub === "fig" ? this._figView : null;
    }

    _boxViews(b) {
      return BOX_VIEWS.filter(([v]) => (v === "settings" && b.settings) || (v === "night" && b.night) ||
        (v === "bedtimes" && b.bedtime) || (v === "battery" && b.battery_stats));
    }

    _figViews(f) {
      return FIG_VIEWS.filter(([v]) => v === "chapters" || v === "settings" ||
        (v === "tune" && (this._tuneOn(f.id) || this._tunesFor(f.id).length)) || (v === "add" && f.kind === "creative"));
    }

    _render() {
      if (!this._hass) return;
      const sub = this._sub;
      const item = sub === "box" ? this._boxById(this._key) : sub === "fig" ? this._figure(this._key) : null;
      const name = sub ? item?.name || item?.id || "" : "";
      const views = item ? (sub === "box" ? this._boxViews(item) : this._figViews(item)) : [];
      const key = [this._area, this._page, !!this._narrow, this._lang, sub, this._key, name, views.map(([v]) => v).join(), this._shownView].join("|");
      if (key !== this._frameKey) {
        this._frameKey = key;
        this._frame(sub, name, views);
      }
      this._update();
    }

    // Tabs of Home Assistant's own: the pages of an area, the views of a box or figure
    _tabGroup(id, items, active) {
      return `<ha-tab-group id="${id}" class="subtabs">${items.map(([k, label]) =>
        `<ha-tab-group-tab slot="nav" panel="${k}"${k === active ? " active" : ""}>${esc(this._t[label])}</ha-tab-group-tab>`).join("")}</ha-tab-group>`;
    }

    // The parts that stay while the page is open: Home Assistant's frame with the
    // areas as tabs (a back arrow and the name on a subpage), the pages of the area
    // or the views of the item, the sheet, the save button
    _frame(sub, name, views) {
      const t = this._t;
      const area = AREAS.find((a) => a[0] === this._area);
      const tabs = sub
        ? (views.length > 1 ? this._tabGroup("views", views, this._shownView) : "")
        : area[3].length > 1 ? this._tabGroup("subtabs", area[3], this._page) : "";
      this.shadowRoot.innerHTML = `
        <style>${STYLE}${PAGE_STYLE}</style>
        <hass-tabs-subpage id="frame">
          ${sub ? `<div slot="header" class="subname">${esc(name)}</div>` : ""}
          <div slot="toolbar-icon" class="actions"><span class="stamp" id="stamp"></span>
            ${iconButton("refresh", t.refresh, 'id="refresh" data-act="refresh"')}
            ${iconButton("cog", t.integration, 'id="integration" data-act="integration"')}</div>
          <div class="page${this._narrow ? " narrow" : ""}">${tabs}<div class="sheet" id="sheet"></div></div>
          <ha-button slot="fab" id="save" size="l" data-act="save" hidden>${icon("save").replace("<ha-svg-icon", '<ha-svg-icon slot="start"')}${esc(t.save)}</ha-button>
        </hass-tabs-subpage>
        <div id="overlay"></div>
        <input type="file" id="upload" accept="${AUDIO_TYPES}" multiple hidden>`;
      const frame = this.shadowRoot.getElementById("frame");
      frame.hass = this._hass;
      frame.narrow = !!this._narrow;
      frame.tabs = sub ? [] : AREAS.map(([id, ic, label]) => ({ path: `${PANEL_PATH}/${id}`, name: t[label], iconPath: MDI[ic] }));
      frame.mainPage = !sub;
      frame.backCallback = sub ? () => this._go(`${this._area}/${this._page}`) : undefined;
      frame.route = this._route || { prefix: PANEL_PATH, path: `/${this._area}/${this._page}` };
      this._sheetHtml = null;
      this._overlayHtml = null;
    }

    // The chapters of what is on a box, in Home Assistant's dialog above the overview: a
    // chapter chosen there plays. The dialog stays while its list is drawn anew
    _renderOverlay() {
      const host = this.shadowRoot.getElementById("overlay");
      if (!host) return;
      const t = this._t;
      const b = this._tracks && this._area === "boxes" && !this._sub ? this._boxById(this._tracks) : null;
      const p = b?.playback;
      let dialog = host.firstElementChild;
      // Gone with the figure, the box or the page it was opened on
      if (!p?.chapter_list?.length || b.online !== true) {
        this._tracks = null;
        if (dialog) dialog.open = false;
        return;
      }
      if (!dialog) {
        dialog = document.createElement("ha-dialog");
        this._overlayHtml = null;
        dialog.addEventListener("closed", () => {
          this._tracks = null;
          dialog.remove();
        });
        host.append(dialog);
      }
      dialog.headerTitle = t.tracksTitle;
      dialog.headerSubtitle = `${p.tonie_name || t.unknownFigure} · ${b.name || b.id}`;
      const html = `<ol class="tracks">${p.chapter_list.map((c, i) => {
        const now = i === p.chapter;
        return `<li role="button" tabindex="0" data-act="jump:${esc(b.id)}:${i}"${now ? ' class="current" aria-current="true"' : ""}>` +
          `<span class="rank">${i + 1}</span><span class="name">${esc(c.title || `${t.chapter} ${i + 1}`)}</span>` +
          `${Number.isFinite(c.seconds) ? `<span class="len">${esc(mmss(c.seconds))}</span>` : ""}</li>`;
      }).join("")}</ol>`;
      if (html !== this._overlayHtml) {
        this._overlayHtml = html;
        dialog.innerHTML = html;
      }
      dialog.open = true;
    }

    _update() {
      const root = this.shadowRoot;
      const sheet = root.getElementById("sheet");
      if (!sheet) return;
      if (!this._typing()) {
        this._forms = {};
        this._hid = 0;
        const html = this._sheet();
        if (html !== this._sheetHtml) {
          this._sheetHtml = html;
          sheet.innerHTML = html;
          this._hydrate(sheet);
          this._tick();
        }
      }
      this._renderOverlay();
      // The save button of the settings: only while something is changed
      const fab = root.getElementById("save");
      if (fab) {
        const show = this._dirty;
        fab.hidden = !show;
        fab.disabled = this._saving;
        root.getElementById("frame").hasFab = show;
      }
      const stamp = root.getElementById("stamp");
      if (stamp) {
        const at = this._stamps[this._dataKey];
        stamp.textContent = at
          ? fill(this._t.asOf, { t: at.toLocaleTimeString(this._lang, { hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23" }) })
          : "";
      }
      root.getElementById("refresh")?.classList.toggle("spin", this._loading.has(this._dataKey));
    }

    // Only the list under the filters is redrawn, so the search field keeps its focus
    _refreshList() {
      const list = this.shadowRoot.getElementById("figlist");
      if (!list || this._area !== "figures" || this._sub) return this._render();
      list.innerHTML = this._figureList();
      for (const chip of this.shadowRoot.querySelectorAll("ha-filter-chip[data-act=kind]")) chip.selected = chip.dataset.key === this._kind;
      this._forms = {};
      this._hid = 0;
      this._sheetHtml = this._sheet();
    }

    _sheet() {
      const t = this._t;
      let html = this._note ? this._errHtml(this._note) : "";
      if (this._done) {
        html += this._alertHelp(this._done.kind, this._done.text, "",
          `<ha-button slot="action" appearance="plain" data-act="dismiss:done">${esc(t.dismiss)}</ha-button>`);
      }
      const sub = this._sub;
      if (sub === "box") return html + this._boxPage();
      if (sub === "fig") return html + this._figurePage();
      switch (`${this._area}/${this._page}`) {
        case "figures/list": return html + this._figuresPage();
        case "figures/tunes": return html + this._tunesPage();
        case "listening/summary": return html + this._listening(false);
        case "listening/times": return html + this._listening(true);
        case "setup/overview": return html + this._setupPage();
        case "setup/household": return html + this._householdPage();
        case "setup/preferences": return html + this._preferencesPage();
        case "setup/log": return html + this._logPage();
        default: return html + this._boxesPage();
      }
    }

    // The overview's state that stands instead of a page: loading, failed, no account
    _overviewState() {
      const t = this._t;
      const o = this._overview;
      const err = this._errors.overview;
      if (!o) return err ? this._errHtml(err) : this._loadingHtml();
      if (!o.entries.length) return this._alertHelp("info", t.noEntry, t.noEntryHelp);
      if (!o.entries.some((e) => e.loaded)) return this._alertHelp("warning", t.notLoaded, t.notLoadedHelp);
      return "";
    }

    _num(n, d = 1) {
      return this._fmt(n, d);
    }

    _date(key, long = false) {
      const d = parseDay(key);
      if (Number.isNaN(d.getTime())) return "–";
      return d.toLocaleDateString(this._lang, long ? { weekday: "short", day: "numeric", month: "short", year: "numeric" } : { day: "numeric", month: "short" });
    }

    _language(code) {
      if (!code) return "";
      const base = String(code).split(/[-_]/)[0];
      try {
        return new Intl.DisplayNames([this._lang], { type: "language" }).of(base) || code;
      } catch {
        return code;
      }
    }

    // ---------------------------------------------------------------- boxes

    _boxesPage() {
      const t = this._t;
      const o = this._overview;
      const state = this._overviewState();
      if (state) return state;
      let html = this._errors.overview ? this._errHtml(this._errors.overview) : "";
      // Only a Toniebox 2 uses the live channel
      if (!o.push_connected && o.boxes.some((b) => b.generation === "toniebox_2")) html += this._alertHelp("warning", t.pushDown, t.pushDownHelp);
      if (!o.boxes.length) return html + this._section("", `<div class="muted">${esc(t.noBoxes)}</div>`);
      const households = new Set(o.boxes.map((b) => b.household).filter(Boolean));
      const many = households.size > 1;
      // A Toniebox 1 reports nothing live: it gets a small card of its own, after the Toniebox 2
      const live = o.boxes.filter((b) => b.generation === "toniebox_2");
      const rest = o.boxes.filter((b) => b.generation !== "toniebox_2");
      return html + `<div class="grid">${live.map((b) => this._box(b, many)).join("")}${rest.map((b) => this._miniBox(b, many)).join("")}</div>`;
    }

    // A Toniebox 1 as a small card: its settings in a sentence and when it was last
    // seen. The cloud knows no connection state of it; the dot comes from its presence
    // entity and is missing without one
    _miniBox(b, showHousehold) {
      const t = this._t;
      const seen = b.last_seen ? fill(t.lastSeen, { t: this._relative(b.last_seen) }) : "";
      const st = b.settings;
      const chips = (showHousehold && b.household ? this._chip(b.household) : "") +
        (st?.applied === false ? this._chip(t.settingsPending, "warn") : "");
      const summary = st ? this._settingsSummary(st, true) : "";
      const cog = st ? iconButton("cog", t.boxSettingsOf, `class="box-cog" data-act="boxset:${esc(b.id)}"`) : "";
      const lines = [summary, seen].filter(Boolean).map((x) => `<span class="supporting">${esc(x)}</span>`).join("");
      const src = safeUrl(b.image_url);
      const pic = src ? `<img class="box-pic small" src="${esc(src)}" alt="">` : "";
      return `<ha-card class="mini-box"><div class="mini-head">${pic}` +
        `<div class="mini-text"><div class="mini-title"><span class="box-name">${esc(b.name || b.id)}</span>${b.presence_entity ? this._dot(b) : ""}${chips}</div>${lines}</div>` +
        cog + `</div></ha-card>`;
    }

    // The settings in one sentence; a Toniebox 1 names all of its few
    _settingsSummary(st, all = false) {
      const t = this._t;
      const v = st.values || {};
      const parts = [];
      if (v.max_volume != null) parts.push(fill(t.sumVolume, { v: this._fmt(v.max_volume) }));
      if (all && v.max_headphone_volume != null) parts.push(fill(t.sumPhones, { v: this._fmt(v.max_headphone_volume) }));
      if (v.lightring_brightness != null) parts.push(fill(t.sumRing, { v: this._fmt(v.lightring_brightness) }));
      if (v.skipping_enabled) parts.push(t.sumSkip);
      if (v.led_level) parts.push(fill(t.sumLed, { v: t[`v_${v.led_level}`] || v.led_level }));
      if (all && v.accelerometer_enabled) parts.push(t.sumTilt);
      return parts.length ? cap(parts.join(" · ")) : t.noSettings;
    }

    // A box opened: its settings, night mode, bedtimes or battery
    _boxPage() {
      const t = this._t;
      if (!this._overview) return this._overviewState();
      const b = this._boxById(this._key);
      if (!b) return this._errHtml({ text: t.e_not_found, detail: "" });
      switch (this._boxView) {
        case "settings": return this._boxSettings(b);
        case "night": return this._nightView(b);
        case "bedtimes": return this._bedtimes(b);
        case "battery": return this._battery(b);
        default: return this._section("", `<div class="muted">${esc(t.noSettings)}</div>`);
      }
    }

    // The settings of a box by topic, a row each; one save button for all
    _boxSettings(b) {
      const t = this._t;
      const st = b.settings;
      const scope = `box:${b.id}`;
      const values = this._saved(scope);
      const live = b.generation === "toniebox_2";
      const pick = (options) => ({ select: { mode: "dropdown", options } });
      const sides = [["left", t.v_left], ["right", t.v_right]].map(([value, label]) => ({ value, label }));
      const percent = { text: { suffix: "%" } };
      const volumes = [25, 50, 75, 100].map((n) => ({ value: String(n), label: `${this._fmt(n)} %` }));
      const withCurrent = (list, current) => (current && !list.includes(current) ? [...list, current] : list);
      // A Toniebox 2 takes any percent, a classic box the four steps
      const fields = {
        name: [{ text: {} }],
        max_volume: live ? [percent, true] : [pick(volumes)],
        max_headphone_volume: live ? [percent, true] : [pick(volumes)],
        lightring_brightness: [percent, true],
        bedtime_lightring_brightness: [percent, true],
        bedtime_max_volume: [percent, true],
        bedtime_max_headphone_volume: [percent, true],
        skipping_enabled: [{ boolean: {} }],
        skipping_direction: [pick(sides)],
        scrubbing_enabled: [{ boolean: {} }],
        accelerometer_enabled: [{ boolean: {} }],
        tap_direction: [pick(sides)],
        led_level: [pick(["on", "dimmed", "off"].map((value) => ({ value, label: t[`v_${value}`] })))],
        age_mode: [pick(withCurrent(["1+", "3+"], values.age_mode).map((value) => ({ value, label: value })))],
        language: [pick(withCurrent(["de", "en", "en-us", "fr"], values.language).map((value) => ({ value, label: this._language(value) })))],
      };
      let html = "";
      if (st.applied === false) html += this._alertHelp("info", t.settingsPending, t.settingsHint);
      if (st.offline_mode) html += this._alertHelp("warning", t.offlineMode, t.offlineHelp);
      BOX_GROUPS.forEach(([group, names], i) => {
        const rows = names.filter((k) => k in values).map((k) => this._row(scope, k, t[`s_${k}`], t[`h_${k}`], ...fields[k]));
        // The firmware matters seldom; it is noted at the end of the first group
        if (i === 0 && b.firmware) rows.push(this._infoRow(t.firmware, t.h_firmware, b.firmware));
        if (rows.length) html += this._section(t[group], rows.join(""), { cls: "rows" });
      });
      if ("presence_entity" in values) {
        const filter = [{ domain: "device_tracker" }, { domain: "binary_sensor", device_class: "connectivity" }];
        html += this._section(t.grpPresence, this._row(scope, "presence_entity", t.s_presence_entity, t.h_presence_entity, { entity: { filter } }),
          { cls: "rows", help: t.presenceHint });
      }
      return html;
    }

    // The night mode of the light ring: a row per setting, saved with the others
    _nightView(b) {
      const t = this._t;
      const scope = `night:${b.id}`;
      const percent = { text: { suffix: "%" } };
      let html = "";
      if (b.night.mode?.enabled && b.night.phase) html += this._alertHelp("info", b.night.phase === "night" ? t.nightNow : t.dayNow, t.nightPhaseHelp);
      const rows = [
        this._row(scope, "enabled", t.n_enabled, t.h_n_enabled, { boolean: {} }),
        this._row(scope, "start", t.n_start, t.h_n_start, { time: { no_second: true } }),
        this._row(scope, "end", t.n_end, t.h_n_end, { time: { no_second: true } }),
        this._row(scope, "night", t.n_night, t.h_n_night, percent, true),
        this._row(scope, "day", t.n_day, t.h_n_day, percent, true),
      ];
      return html + this._section(t.nightMode, rows.join(""), { cls: "rows", help: t.nightHint });
    }

    // The weekday names in the language of Home Assistant; 1 January 2024 was a Monday
    _dayName(day, style = "short") {
      const i = WEEKDAYS.indexOf(day);
      return new Date(2024, 0, 1 + Math.max(0, i)).toLocaleDateString(this._lang, { weekday: style });
    }

    _days(days) {
      const set = WEEKDAYS.filter((d) => days.includes(d));
      if (set.length === 7) return this._t.everyDay;
      // A run of days in a row reads as "Mon – Fri"
      const first = WEEKDAYS.indexOf(set[0]);
      if (set.length > 2 && set.every((d, i) => WEEKDAYS.indexOf(d) === first + i)) {
        return `${this._dayName(set[0])} – ${this._dayName(set[set.length - 1])}`;
      }
      return set.map((d) => this._dayName(d)).join(", ");
    }

    // The bedtimes of a Toniebox 2 that rings alarms: the next alarm, the schedules
    // with a switch each, a row opens the form to change one, a button adds one
    _bedtimes(b) {
      const t = this._t;
      const bt = b.bedtime;
      const editing = this._sched?.box === b.id ? this._sched : null;
      let html = "";
      const next = bt.next_alarm;
      if (next) {
        const when = new Date(time(next.at)).toLocaleString(this._lang, { weekday: "short", hour: "2-digit", minute: "2-digit" });
        const state = next.armed ? t.alarmArmed : next.due ? t.alarmPending : t.alarmLater;
        html += `<ha-alert alert-type="${next.armed ? "success" : "info"}" class="alarm-next">${esc(`${fill(t.nextAlarm, { t: when })} · ${state}`)}</ha-alert>`;
      }
      if (!bt.schedules) return html + this._section(t.bedtimes, this._alertHelp("warning", t.schedulesUnknown, t.schedulesUnknownHelp), { help: t.alarmHint });
      let rows = bt.schedules.map((s) => {
        if (editing?.id === s.id) return this._scheduleForm(editing);
        const times = `${s.sleep_time || "–"} – ${s.wakeup_time || "–"}`;
        const alarm = s.alarm_enabled ? ` <span class="alarm-mark" role="img" aria-label="${esc(t.alarmOn)}" title="${esc(t.alarmOn)}">${icon("alarm")}</span>` : "";
        return `<div class="item"><ha-switch data-act="son:${esc(b.id)}:${esc(s.id)}"${s.enabled ? " checked" : ""}` +
          ` aria-label="${esc(`${t.scheduleOn}: ${s.name || t.scheduleUnnamed}`)}"${this._sched ? " disabled" : ""}></ha-switch>` +
          `<div class="main" role="button" tabindex="0" data-act="sedit:${esc(b.id)}:${esc(s.id)}" aria-label="${esc(`${t.edit}: ${s.name || t.scheduleUnnamed}`)}">` +
          `<div class="text"><span class="headline">${esc(s.name || t.scheduleUnnamed)}${alarm}</span>` +
          `<span class="supporting">${esc(`${this._days(s.days)} · ${times}`)}</span></div>${icon("pencil")}</div></div>`;
      }).join("");
      if (editing && editing.id === null) rows += this._scheduleForm(editing);
      if (!bt.schedules.length && !editing) rows = `<div class="item muted">${esc(t.noSchedules)}</div>`;
      const actions = editing ? "" : this._btn(`sadd:${b.id}`, t.addSchedule, "plus");
      return html + this._section(t.bedtimes, rows, { help: t.alarmHint, cls: "list", actions });
    }

    _scheduleForm(edit) {
      const t = this._t;
      const busy = edit.saving;
      const form = this._formSlot("schedule", this._scheduleSchema(), edit.data, (v) => { edit.data = { ...v }; });
      let html = `<div class="sched-form">${edit.id === null ? `<div class="tile-title">${esc(t.scheduleNew)}</div>` : ""}${form}`;
      if (edit.confirm) {
        html += `<ha-alert alert-type="warning">${esc(fill(t.confirmDelete, { name: edit.data.name || t.scheduleUnnamed }))}` +
          `<ha-button slot="action" appearance="plain" data-act="sdelno">${esc(t.cancel)}</ha-button>` +
          `<ha-button slot="action" variant="danger" data-act="sdelok">${esc(t.deleteSchedule)}</ha-button></ha-alert>`;
      } else {
        html += `<div class="bar-row">${this._btn("ssave", t.save, "check", { look: "filled", disabled: busy })}${this._btn("scancel", t.cancel, "close", { disabled: busy })}` +
          (edit.id !== null ? this._btn("sdel", t.deleteSchedule, "remove", { look: "danger", disabled: busy }) : "") + `</div>`;
      }
      return html + `</div>`;
    }

    _scheduleSchema() {
      const t = this._t;
      const days = WEEKDAYS.map((d) => ({ value: d, label: this._dayName(d, "long") }));
      return [
        { name: "name", label: t.f_name, required: true, selector: { text: {} } },
        { name: "days", label: t.f_days, required: true, selector: { select: { multiple: true, mode: "list", options: days } } },
        { name: "", type: "grid", schema: [
          { name: "sleep_time", label: t.f_sleep_time, required: true, selector: { time: { no_second: true } } },
          { name: "wakeup_time", label: t.f_wakeup_time, required: true, selector: { time: { no_second: true } } },
        ] },
        { name: "enabled", label: t.f_enabled, selector: { boolean: {} } },
        { name: "alarm_enabled", label: t.f_alarm_enabled, selector: { boolean: {} } },
        { name: "alarm_volume", label: t.f_alarm_volume, num: true, selector: { text: { suffix: "%" } } },
        { name: "alarm_morning_light", label: t.f_alarm_morning_light, selector: { boolean: {} } },
      ];
    }

    _scheduleAction(verb, arg) {
      const [boxId, id] = arg.split(/:(.*)/s);
      const box = this._boxById(boxId);
      const edit = this._sched;
      switch (verb) {
        case "sadd":
          if (!box || edit) return;
          this._sched = { box: boxId, id: null, saving: false, confirm: false,
            data: { name: "", days: WEEKDAYS.slice(0, 5), sleep_time: "19:00", wakeup_time: "06:30", enabled: true, alarm_enabled: true, alarm_volume: 50, alarm_morning_light: true } };
          break;
        case "sedit": {
          const s = box?.bedtime?.schedules?.find((x) => x.id === id);
          if (!s || edit) return;
          const { id: _id, ...data } = s;
          this._sched = { box: boxId, id: s.id, saving: false, confirm: false, data: { ...data, days: [...s.days] } };
          break;
        }
        case "scancel":
          if (edit?.saving) return;
          this._sched = null;
          break;
        case "ssave":
          this._saveSchedule();
          return;
        case "sdel":
          if (!edit || edit.saving || edit.id === null) return;
          edit.confirm = true;
          break;
        case "sdelno":
          if (edit) edit.confirm = false;
          break;
        case "sdelok":
          this._saveSchedule(true);
          return;
        case "son": {
          const s = box?.bedtime?.schedules?.find((x) => x.id === id);
          if (!s || edit) return;
          this._sendSchedule({ type: "storybox_plus/bedtime/save", box_id: boxId, schedule_id: s.id, enabled: !s.enabled });
          return;
        }
        default:
          return;
      }
      this._render();
    }

    async _saveSchedule(remove = false) {
      const edit = this._sched;
      if (!edit || edit.saving || !this._hass) return;
      const d = edit.data;
      let msg;
      if (remove) {
        msg = { type: "storybox_plus/bedtime/delete", box_id: edit.box, schedule_id: edit.id };
      } else {
        const volume = Number(d.alarm_volume ?? 100);
        msg = {
          type: "storybox_plus/bedtime/save", box_id: edit.box,
          name: String(d.name || "").trim(), days: Array.isArray(d.days) ? d.days : [],
          sleep_time: clock(d.sleep_time), wakeup_time: clock(d.wakeup_time),
          enabled: !!d.enabled, alarm_enabled: !!d.alarm_enabled,
          alarm_volume: Math.round(volume), alarm_morning_light: !!d.alarm_morning_light,
        };
        if (edit.id !== null) msg.schedule_id = edit.id;
        if (!msg.days.length || !msg.sleep_time || !msg.wakeup_time || !Number.isFinite(volume) || volume < 0 || volume > 100) {
          this._note = this._error({ code: "invalid_format", message: "" });
          this._render();
          return;
        }
      }
      edit.saving = true;
      this._note = null;
      this._render();
      const ok = await this._sendSchedule(msg);
      if (ok && this._sched === edit) this._sched = null;
      else {
        edit.saving = false;
        edit.confirm = false;
      }
      this._render();
    }

    // The integration answers with the box as it is afterwards
    async _sendSchedule(msg) {
      try {
        this._replaceBox(await this._hass.callWS(msg));
        this._render();
        return true;
      } catch (err) {
        this._note = this._error(err);
        this._render();
        return false;
      }
    }

    // Kept in Home Assistant, not on the box: the answer is the box as it is then
    async _setRepeat(boxId, mode) {
      if (!this._hass || this._ctlBusy) return;
      this._ctlError = null;
      try {
        this._replaceBox(await this._hass.callWS({ type: "storybox_plus/box/repeat", box_id: boxId, mode }));
      } catch (err) {
        this._ctlError = { id: boxId, err };
      }
      this._update();
    }

    async _command(boxId, command, value) {
      if (!this._hass || this._ctlBusy) return;
      this._ctlBusy = boxId;
      this._ctlError = null;
      this._render();
      const msg = { type: "storybox_plus/box/command", box_id: boxId, command };
      if (value !== undefined && value !== "") msg.value = Number(value);
      try {
        await this._hass.callWS(msg);
        // The next press goes on from the level just sent, not from the one the
        // box reported before: its answer comes through the push channel later
        if (command === "volume") {
          this._volSent = { box: boxId, level: msg.value, at: Date.now() };
          this._keepVolume();
        }
      } catch (err) {
        this._ctlError = { id: boxId, err };
      }
      this._ctlBusy = null;
      // The box reports the change through the push channel; the overview shows it soon after
      window.setTimeout(() => this._loadOverview(), 1500);
      this._render();
    }

    // A level sent a moment ago wins over an overview that does not have it yet;
    // once the box reports it, or after a few seconds, the box's word counts again
    _keepVolume() {
      const sent = this._volSent;
      if (!sent) return;
      const b = this._boxById(sent.box);
      if (!b) { this._volSent = null; return; }
      // A fresh overview with the level: the box has it
      if (this._overview !== sent.overview && b.volume === sent.level) { this._volSent = null; return; }
      if (Date.now() - sent.at > 4000) {
        // No word from the box: the next overview shows what it really has
        this._volSent = null;
        this._loadOverview();
        return;
      }
      b.volume = sent.level;
      sent.overview = this._overview;
      window.setTimeout(() => { if (this._volSent === sent) this._loadOverview(); }, 1500);
    }

    // The battery: level, what a charge lasts, and the charge history
    _battery(b) {
      const t = this._t;
      const s = b.battery_stats;
      const cur = s.current;
      const parts = [];
      if (Number.isFinite(b.battery_remaining_hours)) parts.push(fill(t.remaining, { h: hours(b.battery_remaining_hours) }));
      if (Number.isFinite(s.average_full_hours)) parts.push(fill(t.perFull, { h: this._num(s.average_full_hours) }));
      else if (Number.isFinite(cur?.per_full)) parts.push(fill(t.perFullProjected, { h: this._num(cur.per_full) }));
      if (s.count > 0) parts.push(fill(s.count === 1 ? t.charge1 : t.chargesN, { n: this._fmt(s.count) }));
      if (Number.isFinite(cur?.hours) && Number.isFinite(cur?.from)) parts.push(fill(t.nowSince, { t: hours(cur.hours), p: this._fmt(cur.from) }));
      let html = this._section(t.battery, `<div class="batt-big fact">${this._batteryLevel(b)}</div>` +
        `<div class="muted">${esc(cap(parts.length ? parts.join(" · ") : t.noCycles))}</div>`, { help: t.batteryHelp });
      const cycles = Array.isArray(s.cycles) ? s.cycles : [];
      if (cycles.length) {
        const max = Math.max(...cycles.map((c) => c.per_full).filter(Number.isFinite), 0);
        const rows = cycles.map((c) => {
          const width = max > 0 && Number.isFinite(c.per_full) ? ((100 * c.per_full) / max).toFixed(1) : 0;
          const level = Number.isFinite(c.from) && Number.isFinite(c.to) ? `${this._fmt(c.from)} % → ${this._fmt(c.to)} %` : "–";
          return `<tr><td>${esc(this._date(c.day))}</td><td>${esc(hours(c.hours))}</td><td>${esc(level)}</td>` +
            `<td><div class="pf"><div class="bar"><div style="width:${width}%"></div></div><span>${esc(hours(c.per_full))}</span></div></td></tr>`;
        }).join("");
        html += this._section(t.history, `<div class="scroll"><table class="cycles"><thead><tr>` +
          `<th>${esc(t.colDay)}</th><th>${esc(t.colOn)}</th><th>${esc(t.colLevel)}</th><th>${esc(t.colPerFull)}</th></tr></thead>` +
          `<tbody>${rows}</tbody></table></div>`);
      }
      return html;
    }

    // -------------------------------------------------------------- figures

    _libraryState() {
      const lib = this._library;
      const err = this._errors.library;
      if (!lib) return this._overviewState() || (err ? this._errHtml(err) : this._loadingHtml());
      return "";
    }

    _figuresPage() {
      const t = this._t;
      const state = this._libraryState();
      if (state) return state;
      const err = this._errors.library;
      const search = this._formSlot("search", [{ name: "query", label: t.search, selector: { text: { type: "search" } } }], { query: this._query },
        (v) => {
          this._query = v.query || "";
          this._refreshList();
        });
      const kinds = KINDS.map((k) => `<ha-filter-chip data-act="kind" data-key="${k}" label="${esc(t[`kind_${k}`])}"${this._kind === k ? " selected" : ""}></ha-filter-chip>`).join("");
      return (err ? this._errHtml(err) : "") +
        `<div class="filters">${search}<ha-chip-set class="kinds" role="group" aria-label="${esc(t.kindLabel)}">${kinds}</ha-chip-set></div>` +
        `<div id="figlist">${this._figureList()}</div>`;
    }

    _figureList() {
      const t = this._t;
      const lib = this._library;
      if (!lib.tonies.length) return this._section("", `<div class="muted">${esc(t.noFigures)}</div>`);
      const q = this._query.trim().toLowerCase();
      const hit = (f) => (this._kind === "all" || f.kind === this._kind) &&
        (!q || [f.name, f.series, ...f.chapters.map((c) => c.title)].some((s) => s && String(s).toLowerCase().includes(q)));
      const list = lib.tonies.filter(hit);
      const all = list.length === lib.tonies.length;
      const count = `<div class="muted small count">${esc(all
        ? (list.length === 1 ? t.figure1 : fill(t.figuresAll, { n: this._fmt(list.length) }))
        : fill(t.figuresOf, { n: this._fmt(list.length), m: this._fmt(lib.tonies.length) }))}</div>`;
      if (!list.length) return count + this._section("", `<div class="muted">${esc(t.noMatch)}</div>`);
      const boxes = new Map((this._overview?.boxes || []).map((b) => [b.id, b.name]));
      const households = new Map(lib.households.length > 1 ? lib.households.map((h) => [h.id, h.name]) : []);
      return count + `<ha-card class="list"><div class="card-content">${list.map((f) => this._figureRow(f, boxes, households)).join("")}</div></ha-card>`;
    }

    // What a figure is, in a line: series, language, kind, household
    _figureSub(f, households) {
      const t = this._t;
      return [f.series, this._language(f.language), f.kind !== "content" ? t[`kind1_${f.kind}`] : "", households.get(f.household_id)]
        .filter(Boolean).map(esc).join(" · ");
    }

    _figureBadges(f, boxes) {
      const t = this._t;
      return (f.on_box ? this._chip(fill(t.onBox, { box: boxes.get(f.on_box) || f.on_box }), "on") : "") +
        (f.transcoding ? this._chip(t.transcoding, "warn") : "") +
        (f.favourites?.active ? this._chip(fill(t.favChip, { n: this._fmt(f.favourites.chapters.length) }), "fav") : "") +
        (f.volume ? this._chip(fill(t.figVolumeChip, { v: this._fmt(f.volume) })) : "") +
        (this._tuneOn(f.id) ? this._chip(t.tune, "on") : "") +
        (f.live ? this._chip(t.liveChip) : "") +
        (f.locked ? `<span class="lock" role="img" aria-label="${esc(t.locked)}" title="${esc(t.locked)}">${icon("lock")}</span>` : "");
    }

    _figureRow(f, boxes, households) {
      const t = this._t;
      const sub = this._figureSub(f, households);
      const meta = [hm(f.seconds), fill(f.chapters.length === 1 ? t.chapter1 : t.chaptersN, { n: this._fmt(f.chapters.length) })].map(esc).join(" · ");
      return this._item("openfig", f.id, this._pic(f.image_url), f.name, [sub, meta].filter(Boolean).join("<br>"),
        `<span class="badges">${this._figureBadges(f, boxes)}</span>`);
    }

    // A figure opened: its chapters, settings, Tune or what can be added
    _figurePage() {
      const t = this._t;
      const state = this._libraryState();
      if (state) return state;
      const f = this._figure(this._key);
      if (!f) return this._errHtml({ text: t.e_not_found, detail: "" });
      switch (this._figView) {
        case "settings": return this._figureSettings(f);
        case "tune": return this._tuneView(f);
        case "add": return this._addView(f);
        default: return this._chaptersView(f);
      }
    }

    // The figure in short above its chapters: picture, what it is, its state
    _figureHead(f) {
      const t = this._t;
      const lib = this._library;
      const boxes = new Map((this._overview?.boxes || []).map((b) => [b.id, b.name]));
      const households = new Map(lib.households.length > 1 ? lib.households.map((h) => [h.id, h.name]) : []);
      const sub = this._figureSub(f, households);
      const meta = [hm(f.seconds), fill(f.chapters.length === 1 ? t.chapter1 : t.chaptersN, { n: this._fmt(f.chapters.length) })];
      if (f.kind === "creative") {
        meta.push(fill(t.free, { t: hm(f.seconds_remaining) }));
        if (Number.isFinite(f.chapters_remaining)) meta.push(fill(t.chaptersFree, { n: this._fmt(f.chapters_remaining) }));
      }
      return `<ha-card><div class="card-content bare head-fig">${this._pic(f.image_url)}<div class="text">` +
        `${sub ? `<span>${sub}</span>` : ""}<span class="supporting">${esc(meta.join(" · "))}</span></div>` +
        `<span class="badges">${this._figureBadges(f, boxes)}</span></div></ha-card>`;
    }

    _chaptersView(f) {
      const t = this._t;
      let html = this._figureHead(f) + this._progressHtml(f);
      if (f.kind !== "creative") {
        // The chapters of a bought figure with their favourite stars
        const fav = f.favourites;
        return html + this._section(t.vChapters, this._chapterList(f.chapters, false, { id: f.id, set: new Set(fav?.chapters || []) }), { help: t.favHint });
      }
      if (f.transcoding_errors?.length) {
        const reasons = [...new Set(f.transcoding_errors)].map((r) => t[`reason_${r}`] || r).join(", ");
        html += this._alertHelp("error", fill(t.convErrors, { r: reasons }), t.convErrorsHelp);
      }
      // Rearranging happens on a copy and goes to the cloud in one go when saved
      const edit = this._edit?.id === f.id ? this._edit : null;
      if (!edit) {
        const busy = !!this._uploads[f.id] && !this._uploads[f.id].error;
        const actions = f.chapters.length ? this._btn(`edit:${f.id}`, t.edit, "pencil", { disabled: busy }) : "";
        return html + this._section(t.vChapters, this._chapterList(f.chapters), { actions, help: t.chaptersHelp });
      }
      const busy = edit.saving;
      let body = "";
      if (edit.chapters.length > 1) {
        body += `<div class="bar-row">${this._btn("sorttitle", t.sortTitle, "sort", { disabled: busy })}${this._btn("shuffle", t.shuffle, "shuffle", { disabled: busy })}</div>`;
      }
      // Removing all chapters asks twice: once whether, once whether the files are kept elsewhere
      if (edit.clearStep === 1 || edit.clearStep === 2) {
        const [text, yes] = edit.clearStep === 1 ? [fill(t.clearAsk1, { n: this._fmt(edit.chapters.length) }), t.clearYes1] : [t.clearAsk2, t.clearYes2];
        body += `<div class="clear-ask"><ha-alert alert-type="${edit.clearStep === 1 ? "warning" : "error"}">${esc(text)}</ha-alert>` +
          // Keeping them is the obvious choice, first and filled; removing comes second
          `<div class="bar-row">${this._btn("clearno", t.clearNo, "check", { look: "filled" })}${this._btn("clearyes", yes, "remove", { look: "danger" })}</div></div>`;
      }
      // One chapter at a time gets a new name, in a form above the list
      if (Number.isInteger(edit.renaming) && edit.chapters[edit.renaming]) {
        body += `<div class="form-row">${this._formSlot("chname", [{ name: "title", label: t.chapterName, required: true, selector: { text: {} } }],
          { title: edit.renameTitle ?? "" }, (v) => { edit.renameTitle = v.title || ""; }, { enter: "chrenameok" })}` +
          `${this._btn("chrenameok", t.apply, "check", { look: "filled" })}${this._btn("chrenamecancel", t.cancel, "close")}</div>`;
      }
      body += this._chapterList(edit.chapters, true);
      const actions = (edit.chapters.length ? this._btn("clearall", t.clearAll, "remove", { look: "danger", disabled: busy || !!edit.clearStep }) : "") +
        this._btn("chcancel", t.cancel, "close", { disabled: busy }) +
        this._btn("chsave", t.save, "check", { look: "filled", disabled: busy || !!edit.clearStep });
      return html + this._section(t.vChapters, body, { actions, help: t.editHint });
    }

    // With `fav` ({ id, set }) every chapter gets a star that marks it as a favourite
    _chapterList(chapters, editing = false, fav = null) {
      const t = this._t;
      if (!chapters.length) return `<div class="muted">${esc(t.noChapters)}</div>`;
      const last = chapters.length - 1;
      return `<ol class="chapters${editing ? " editing" : ""}">${chapters.map((c, i) => {
        const on = !!fav && fav.set.has(i);
        const title = c.title || `${t.chapter} ${i + 1}`;
        const tools = editing
          ? `<span class="ch-tools">` +
            iconButton("pencil", `${t.renameChapter}: ${title}`, `data-act="chrename:${i}"`) +
            iconButton("up", `${t.moveUp}: ${title}`, `data-act="up:${i}"${i === 0 ? " disabled" : ""}`) +
            iconButton("down", `${t.moveDown}: ${title}`, `data-act="down:${i}"${i === last ? " disabled" : ""}`) +
            iconButton("remove", `${t.remove}: ${title}`, `class="danger" data-act="remove:${i}"`) + `</span>`
          : fav
            ? iconButton(on ? "star" : "starOff", `${t.favToggle}: ${title}`, `class="star${on ? " on" : ""}" data-act="fav:${esc(fav.id)}:${i}" aria-pressed="${on}"`)
            : "";
        return `<li><span class="no">${i + 1}</span><span class="ch-title">${esc(title)}</span>` +
          `${c.transcoding ? this._chip(t.transcoding, "warn") : ""}<span class="len">${esc(mmss(c.seconds))}</span>${tools}</li>`;
      }).join("")}</ol>`;
    }

    // What a figure has to set: a creative one its name, live mode and shuffling on
    // swap, every one its volume; a bought one its lock and its favourites
    _figureSettings(f) {
      const t = this._t;
      const scope = `fig:${f.id}`;
      const values = this._saved(scope);
      const levels = [{ value: "box", label: t.figVolumeBox }, ...Array.from({ length: 13 }, (_, i) => ({ value: String(i + 1), label: `${this._fmt(i + 1)} / ${this._fmt(13)}` }))];
      const rows = [];
      if ("name" in values) rows.push(this._row(scope, "name", t.c_name, t.h_c_name, { text: {} }));
      if ("live" in values) rows.push(this._row(scope, "live", t.c_live, t.h_c_live, { boolean: {} }));
      rows.push(this._row(scope, "volume", t.figVolume, t.figVolumeHint, { select: { mode: "dropdown", options: levels } }));
      if ("locked" in values) rows.push(this._row(scope, "locked", t.lockSwitch, t.lockHint, { boolean: {} }));
      if ("favourites" in values) rows.push(this._row(scope, "favourites", t.favSwitch, t.favSwitchHint, { boolean: {} }));
      if ("shuffle_on_swap" in values) rows.push(this._row(scope, "shuffle_on_swap", t.shuffleSwap, t.shuffleSwapHint, { boolean: {} }));
      return this._section(t.vSettings, rows.join(""), { cls: "rows" });
    }

    _tuneOn(id) {
      return (this._library?.tunes || []).find((x) => x.assigned.includes(id)) || null;
    }

    _tunesFor(id) {
      return (this._library?.tunes || []).filter((x) => x.suitable.includes(id) && !x.assigned.includes(id));
    }

    // A bought Tune on the figure, or the Tunes that fit it to lay one on
    _tuneView(f) {
      const t = this._t;
      const on = this._tuneOn(f.id);
      const busy = this._tuneBusy === f.id;
      const help = f.kind === "creative" ? t.tuneHintCreative : t.tuneHint;
      if (on) {
        return this._section(t.tune, `<div>${esc(fill(t.tuneOn, { t: on.title }))}</div>`,
          { help, actions: this._btn(`tuneoff:${f.id}`, t.tuneRemove, "close", { disabled: busy }) });
      }
      const fits = this._tunesFor(f.id);
      const options = fits.map((x) => ({ value: x.id, label: x.remaining != null ? `${x.title} (${fill(t.tuneLeft, { n: this._fmt(x.remaining) })})` : x.title }));
      const form = this._formSlot(`tune:${f.id}`, [{ name: "tune", label: t.tunePick, required: true, selector: { select: { mode: "dropdown", options } } }],
        { tune: this._tunePick[f.id] || fits[0]?.id }, (v) => { this._tunePick[f.id] = v.tune; });
      return this._section(t.tune, form, { help, actions: this._btn(`tuneon:${f.id}`, t.tuneAssign, "check", { look: "filled", disabled: busy }) });
    }

    async _setTune(id, tuneId) {
      if (!this._hass || this._tuneBusy) return;
      this._tuneBusy = id;
      this._note = null;
      this._render();
      try {
        const answer = await this._hass.callWS({ type: "storybox_plus/figure/tune", tonie_id: id, tune_id: tuneId });
        this._library.tunes = answer.tunes;
        // A creative figure plays other chapters now; a bought one keeps its own as they were
        if (answer.figure?.kind === "creative") this._replaceTonie(answer.figure);
      } catch (err) {
        this._note = this._error(err);
      }
      this._tuneBusy = null;
      this._render();
    }

    // What a running upload, or a chapter fetched from a link, is doing right now
    _progressHtml(f) {
      const t = this._t;
      const up = this._uploads[f.id];
      if (!up) return "";
      if (up.error) {
        return this._alertHelp("error", up.error.text, up.error.detail ? `${t.errDetail}: ${up.error.detail}` : "",
          `<ha-button slot="action" appearance="plain" data-act="dismiss:${esc(f.id)}">${esc(t.dismiss)}</ha-button>`);
      }
      let text;
      if (!up.link) text = fill(t.uploading, { name: up.name, n: this._fmt(up.done + 1), m: this._fmt(up.total) });
      else if (up.stage === "upload") text = fill(t.linkUpload, { name: up.name });
      else if (up.stage === "convert") text = fill(t.linkConvert, { name: up.name });
      else if (up.stage === "download") text = fill(up.pct == null ? t.linkFetch : t.linkFetchPct, { name: up.name, p: this._fmt(up.pct) });
      else text = t.linkProbe;
      return `<ha-alert alert-type="info">${esc(text)}</ha-alert>`;
    }

    // Chapters added to a creative figure: files, a YouTube link, a text Piper speaks
    _addView(f) {
      const t = this._t;
      const lib = this._library;
      const busy = !!this._uploads[f.id] && !this._uploads[f.id].error;
      let html = this._progressHtml(f);
      html += this._section(t.upload, `<div class="muted">${esc(t.uploadLine)}</div>`,
        { help: t.uploadHint, actions: this._btn(`upload:${f.id}`, t.uploadFiles, "upload", { look: "filled", disabled: busy }) });
      // Links need the Media Fetcher app, a text a Piper voice
      if (lib.fetcher === false) html += this._section(t.fromLink, this._alertHelp("info", t.fetcherMissing, t.fetcherHelp), { help: t.linkHint });
      else {
        const link = this._link[f.id] || "";
        html += this._section(t.fromLink, this._formSlot(`link:${f.id}`, [{ name: "url", label: t.linkPlaceholder, required: true, selector: { text: { type: "url" } } }],
          { url: link }, (v) => { this._link[f.id] = v.url || ""; }, { enter: `linkadd:${f.id}` }),
        { help: t.linkHint, actions: this._btn(`linkadd:${f.id}`, t.add, "check", { look: "filled", disabled: busy }) });
      }
      if (!lib.speech) html += this._section(t.fromText, this._alertHelp("info", t.speechMissing, t.speechHelp), { help: t.textHint });
      else {
        const sp = this._speak[f.id] || {};
        const body = sp.busy
          ? `<ha-alert alert-type="info">${esc(t.textBusy)}</ha-alert>`
          : this._formSlot(`speak:${f.id}`, [
            { name: "title", label: t.textTitle, selector: { text: {} } },
            { name: "text", label: t.textBody, required: true, selector: { text: { multiline: true } } },
          ], { title: sp.title || "", text: sp.text || "" }, (v) => { this._speak[f.id] = { ...sp, title: v.title || "", text: v.text || "" }; });
        html += this._section(t.fromText, body, { help: t.textHint, actions: this._btn(`speakadd:${f.id}`, t.add, "check", { look: "filled", disabled: !!sp.busy }) });
      }
      return html;
    }

    // Buttons of the figures: "verb:argument"
    _chapterAction(verb, arg) {
      const edit = this._edit;
      switch (verb) {
        case "edit": {
          const f = this._figure(arg);
          if (f) this._edit = { id: f.id, chapters: f.chapters.map((c) => ({ ...c })), saving: false };
          break;
        }
        case "chcancel":
          if (edit?.saving) return;
          this._edit = null;
          break;
        case "chsave":
          this._saveChapters();
          return;
        case "up":
        case "down": {
          if (!edit || edit.saving) return;
          const i = Number(arg);
          const j = verb === "up" ? i - 1 : i + 1;
          if (i < 0 || j < 0 || i >= edit.chapters.length || j >= edit.chapters.length) return;
          [edit.chapters[i], edit.chapters[j]] = [edit.chapters[j], edit.chapters[i]];
          break;
        }
        case "chrename": {
          if (!edit || edit.saving) return;
          const i = Number(arg);
          if (!edit.chapters[i]) return;
          edit.renaming = i;
          edit.renameTitle = edit.chapters[i].title || "";
          break;
        }
        case "chrenameok": {
          if (!edit || !Number.isInteger(edit.renaming)) return;
          const title = String(edit.renameTitle || "").trim();
          if (title) edit.chapters[edit.renaming] = { ...edit.chapters[edit.renaming], title };
          edit.renaming = null;
          break;
        }
        case "chrenamecancel":
          if (edit) edit.renaming = null;
          break;
        case "clearall":
          if (!edit || edit.saving || !edit.chapters.length) return;
          edit.clearStep = 1;
          break;
        case "clearyes":
          if (!edit || edit.saving || !edit.clearStep) return;
          if (edit.clearStep === 1) edit.clearStep = 2;
          else {
            edit.clearStep = 0;
            edit.chapters = [];
          }
          break;
        case "clearno":
          if (edit) edit.clearStep = 0;
          break;
        case "sorttitle":
          if (!edit || edit.saving) return;
          edit.chapters.sort((a, b) => String(a.title).localeCompare(String(b.title), this._lang, { numeric: true, sensitivity: "base" }));
          break;
        case "shuffle": {
          if (!edit || edit.saving || edit.chapters.length < 2) return;
          // Fisher-Yates; a shuffle that came out unchanged is shuffled again
          const before = edit.chapters.map((c) => c.id).join();
          do {
            for (let i = edit.chapters.length - 1; i > 0; i--) {
              const j = Math.floor(Math.random() * (i + 1));
              [edit.chapters[i], edit.chapters[j]] = [edit.chapters[j], edit.chapters[i]];
            }
          } while (edit.chapters.map((c) => c.id).join() === before);
          break;
        }
        case "remove":
          if (!edit || edit.saving) return;
          edit.chapters.splice(Number(arg), 1);
          break;
        case "upload":
          if (this._uploads[arg] && !this._uploads[arg].error) return;
          delete this._uploads[arg];
          this._uploadTarget = arg;
          this.shadowRoot.getElementById("upload")?.click();
          return;
        case "linkadd":
          this._fetchLink(arg);
          return;
        case "speakadd":
          this._addFromText(arg);
          return;
        case "fav": {
          const [id, index] = arg.split(/:(\d+)$/);
          const f = this._figure(id);
          if (!f) return;
          const set = new Set(f.favourites?.chapters || []);
          const i = Number(index);
          if (set.has(i)) set.delete(i); else set.add(i);
          // The first star switches the favourites on; later stars keep the switch as it is
          this._setFavourites(id, [...set], f.favourites ? f.favourites.active : true);
          return;
        }
        default:
          return;
      }
      this._render();
    }

    async _saveChapters() {
      const edit = this._edit;
      if (!edit || edit.saving || !this._hass) return;
      edit.saving = true;
      this._note = null;
      this._render();
      // The chapters go only when they changed, because every change makes the cloud convert
      const before = this._figure(edit.id);
      try {
        const ids = edit.chapters.map((c) => c.id);
        // Only the names that changed go along
        const oldTitles = Object.fromEntries((before?.chapters || []).map((c) => [c.id, c.title]));
        const titles = Object.fromEntries(edit.chapters.filter((c) => c.title && c.title !== oldTitles[c.id]).map((c) => [c.id, c.title]));
        if (!before || ids.join() !== before.chapters.map((c) => c.id).join() || Object.keys(titles).length) {
          const msg = { type: "storybox_plus/chapters/arrange", tonie_id: edit.id, chapters: ids };
          if (Object.keys(titles).length) msg.titles = titles;
          this._replaceTonie(await this._hass.callWS(msg));
        }
        if (this._edit === edit) this._edit = null;
      } catch (err) {
        edit.saving = false;
        this._note = this._error(err);
      }
      this._render();
    }

    // The files go to Home Assistant first (its own upload endpoint keeps them until
    // taken), then the integration moves each into the cloud and appends the chapter
    async _uploadFiles(id, files) {
      if (!this._hass) return;
      const up = { total: files.length, done: 0, name: files[0].name, error: null };
      this._uploads[id] = up;
      this._render();
      for (const file of files) {
        up.name = file.name;
        this._render();
        try {
          const form = new FormData();
          form.append("file", file);
          const resp = await this._hass.fetchWithAuth("/api/file_upload", { method: "POST", body: form });
          if (!resp.ok) throw { code: resp.status === 413 ? "too_large" : "upload_failed", message: `HTTP ${resp.status}` };
          const { file_id } = await resp.json();
          const title = file.name.replace(/\.[^.]+$/, "");
          this._replaceTonie(await this._hass.callWS({ type: "storybox_plus/chapters/add", tonie_id: id, file_id, title }));
          up.done += 1;
        } catch (err) {
          up.error = this._error(err);
          break;
        }
      }
      if (!up.error && this._uploads[id] === up) delete this._uploads[id];
      this._render();
    }

    // The link goes to the integration, which fetches the audio through the Media
    // Fetcher app and appends the chapter; it reports the stages until done or failed
    async _fetchLink(id) {
      const url = (this._link[id] || "").trim();
      if (!url || !this._hass || (this._uploads[id] && !this._uploads[id].error)) return;
      const up = { total: 1, done: 0, name: "", error: null, link: true, stage: "probe", pct: null, unsub: null };
      this._uploads[id] = up;
      this._link[id] = "";
      this._render();
      const end = () => {
        if (up.unsub) up.unsub();
        up.unsub = null;
      };
      try {
        up.unsub = await this._hass.connection.subscribeMessage((ev) => {
          if (ev.stage === "done") {
            this._replaceTonie(ev.figure);
            end();
            if (this._uploads[id] === up) delete this._uploads[id];
            this._done = { kind: "success", text: fill(this._t.linkAdded, { name: up.name }) };
          } else if (ev.stage === "error") {
            up.error = this._error({ code: ev.code, message: ev.message });
            end();
          } else {
            up.stage = ev.stage;
            if (ev.title) up.name = ev.title;
            up.pct = ev.total ? Math.floor((ev.done / ev.total) * 100) : null;
          }
          this._render();
        }, { type: "storybox_plus/chapters/add_link", tonie_id: id, url }, { resubscribe: false });
      } catch (err) {
        up.error = this._error(err);
        this._render();
      }
    }

    // Piper speaks in Home Assistant; the integration uploads the recording as a chapter
    async _addFromText(id) {
      const sp = this._speak[id] || {};
      const text = String(sp.text || "").trim();
      if (!text || sp.busy || !this._hass) return;
      this._speak[id] = { ...sp, busy: true };
      this._note = null;
      this._render();
      const msg = { type: "storybox_plus/chapters/add_text", tonie_id: id, text };
      if (String(sp.title || "").trim()) msg.title = sp.title.trim();
      try {
        this._replaceTonie(await this._hass.callWS(msg));
        delete this._speak[id];
        this._done = { kind: "success", text: this._t.textAdded };
      } catch (err) {
        this._speak[id] = { ...sp, busy: false };
        this._note = this._error(err);
      }
      this._render();
    }

    // The favourites of a bought figure go to the integration at once; the answer is kept
    async _setFavourites(id, chapters, active) {
      const f = this._figure(id);
      if (!f || !this._hass) return;
      this._note = null;
      try {
        f.favourites = (await this._hass.callWS({ type: "storybox_plus/favourites/set", tonie_id: id, chapters, active })).favourites;
      } catch (err) {
        this._note = this._error(err);
      }
      this._render();
    }

    // While the cloud converts a creative figure, it is read again now and then
    async _refreshConverting() {
      if (!this._hass || !this._library || this._loading.has("convert")) return;
      const converting = this._library.tonies.filter((f) => f.kind === "creative" && f.transcoding);
      if (!converting.length) return;
      this._loading.add("convert");
      try {
        for (const f of converting) this._replaceTonie(await this._hass.callWS({ type: "storybox_plus/figure/refresh", tonie_id: f.id }));
      } catch {
        // The next poll of the integration catches up
      }
      this._loading.delete("convert");
      this._render();
    }

    // ---------------------------------------------------------------- tunes

    // The bought Tunes, a voucher to redeem, content from a code
    _tunesPage() {
      const t = this._t;
      const state = this._libraryState();
      if (state) return state;
      const lib = this._library;
      const names = new Map(lib.tonies.map((f) => [f.id, f.name]));
      const tunes = lib.tunes || [];
      const rows = tunes.length
        ? tunes.map((x) => {
          const on = x.assigned.map((id) => names.get(id) || id).join(", ");
          const sub = [x.remaining != null ? fill(t.tuneLeft, { n: this._fmt(x.remaining) }) : "", on ? fill(t.tuneOnFigure, { f: on }) : ""].filter(Boolean).join(" · ");
          return `<div class="item">${this._pic(x.image_url)}<div class="text"><span class="headline">${esc(x.title)}</span>` +
            `${sub ? `<span class="supporting">${esc(sub)}</span>` : ""}</div>${on ? this._chip(t.tuneInUse, "on") : ""}</div>`;
        }).join("")
        : `<div class="item muted">${esc(t.noTunes)}</div>`;
      let html = this._section(t.tunesTitle, rows, { cls: "list", help: t.tunesHelp });
      // A voucher counts for an account
      const entries = this._loadedEntries();
      for (const e of entries) {
        const v = this._voucher[e.entry_id] || {};
        let body = this._formSlot(`voucher:${e.entry_id}`, [{ name: "code", label: t.voucherCode, required: true, selector: { text: {} } }],
          { code: v.code || "" }, (d) => { this._voucher[e.entry_id] = { ...(this._voucher[e.entry_id] || {}), code: d.code || "" }; }, { enter: `voucher:${e.entry_id}` });
        if (v.done != null) body += `<ha-alert alert-type="success">${esc(v.done ? fill(t.voucherDone, { n: this._fmt(v.done) }) : t.voucherNone)}</ha-alert>`;
        html += this._section(entries.length > 1 ? `${t.prefVoucher} · ${e.title}` : t.prefVoucher, body,
          { help: t.voucherHint, actions: this._btn(`voucher:${e.entry_id}`, t.voucherRedeem, "check", { look: "filled", disabled: !!v.busy }) });
      }
      // Ready-made content from a code goes onto a creative figure
      const creative = lib.tonies.filter((f) => f.kind === "creative");
      if (creative.length) {
        const c = this._code;
        const tonie = creative.some((f) => f.id === c.tonie) ? c.tonie : creative[0].id;
        const form = this._formSlot("code", [
          { name: "tonie", label: t.codeFigure, required: true, selector: { select: { mode: "dropdown", options: creative.map((f) => ({ value: f.id, label: f.name })) } } },
          { name: "token", label: t.codePlaceholder, required: true, selector: { text: {} } },
        ], { tonie, token: c.token }, (d) => { this._code = { ...this._code, tonie: d.tonie, token: d.token || "" }; });
        html += this._section(t.fromCode, form, { help: t.codeHint, actions: this._btn("codeadd", t.add, "check", { look: "filled", disabled: c.busy }) });
      }
      return html;
    }

    async _redeemVoucher(entryId) {
      const v = (this._voucher[entryId] ||= {});
      const code = String(v.code || "").trim();
      if (!code || v.busy || !this._hass) return;
      v.busy = true;
      v.done = null;
      this._note = null;
      this._render();
      try {
        const answer = await this._hass.callWS({ type: "storybox_plus/voucher/redeem", entry_id: entryId, code });
        v.done = answer.count;
        v.code = "";
        if (this._library) this._library.tunes = answer.tunes;
      } catch (err) {
        this._note = this._error(err);
      }
      v.busy = false;
      this._render();
    }

    async _redeemCode() {
      const c = this._code;
      const creative = (this._library?.tonies || []).filter((f) => f.kind === "creative");
      const tonie = creative.some((f) => f.id === c.tonie) ? c.tonie : creative[0]?.id;
      const token = String(c.token || "").trim();
      if (!tonie || !token || c.busy || !this._hass) return;
      this._code = { ...c, tonie, busy: true };
      this._note = null;
      this._render();
      try {
        this._replaceTonie(await this._hass.callWS({ type: "storybox_plus/figure/redeem_token", tonie_id: tonie, token }));
        this._code = { tonie, token: "", busy: false };
        this._done = { kind: "success", text: fill(this._t.codeAdded, { f: this._figure(tonie)?.name || "" }) };
      } catch (err) {
        this._code = { ...this._code, busy: false };
        this._note = this._error(err);
      }
      this._render();
    }

    // ------------------------------------------------------------ listening

    _listening(times) {
      const t = this._t;
      const range = this._range;
      const s = this._stats[range];
      const err = this._errors[`stats:${range}`];
      const options = RANGES.map(([k]) => ({ value: k, label: t[`range_${k}`] }));
      let html = `<ha-control-select id="range" class="range" label="${esc(t.rangeLabel)}" data-options="${esc(JSON.stringify(options))}" data-value="${esc(range)}"></ha-control-select>`;
      if (!s) return html + (err ? this._errHtml(err) : this._loadingHtml());
      if (err) html += this._errHtml(err);
      if (!s.enabled) {
        html += this._alertHelp("info", t.disabled, t.disabledHelp,
          `<ha-button slot="action" appearance="plain" data-act="go" data-key="setup/preferences">${esc(t.pgPreferences)}</ha-button>`);
      }
      // How long a Toniebox 1 was in the network: beside the listening time, never in it
      const active = s.active_per_box?.length
        ? this._section(t.activeTime, `<table class="kv">${s.active_per_box.map((b) =>
          `<tr><th>${esc(b.name || b.box_id)}</th><td>${esc(hm(b.seconds))} h</td></tr>`).join("")}</table>`, { help: t.activeHelp })
        : "";
      const empty = !s.total_seconds && !s.top.length && !s.top_placed?.length;
      if (times) {
        if (empty) return html + this._section("", `<div class="muted">${esc(t.noStats)}</div>`);
        return html + this._dayChart(s) + this._heatmap(s);
      }
      const label = s.days ? fill(t.lastDays, { n: this._fmt(s.days) }) : s.first_day ? fill(t.since, { d: this._date(s.first_day, true) }) : t.sinceSetup;
      // Where the numbers come from, and so what they cannot contain: behind the total's (i)
      html += this._section(t.total, `<div class="total"><span class="big">${esc(hm(s.total_seconds))}</span><span class="unit">h</span></div>` +
        `<div class="muted">${esc(label)}</div>` + this._comparison(s), { help: t.noteLocal });
      if (empty) return html + (active || this._section("", `<div class="muted">${esc(t.noStats)}</div>`));
      const bar = (v, max) => `<div class="bar" role="img" aria-label="${esc(`${this._fmt((100 * v) / max)} %`)}"><div style="width:${((100 * v) / max).toFixed(1)}%"></div></div>`;
      if (s.top.length) {
        const max = Math.max(...s.top.map((x) => x.seconds), 1);
        html += this._section(t.top, `<ol class="top">${s.top.map((x, i) =>
          `<li><span class="rank">${i + 1}</span>${this._pic(x.image_url, " small")}<div class="text"><span class="headline">${esc(x.name || t.unknownFigure)}</span>` +
          `${bar(x.seconds, max)}</div><span class="len">${esc(hm(x.seconds))}</span></li>`).join("")}</ol>`);
      }
      if (s.top_placed?.length) {
        const max = Math.max(...s.top_placed.map((x) => x.times), 1);
        html += this._section(t.topPlaced, `<ol class="top placed">${s.top_placed.map((x, i) =>
          `<li><span class="rank">${i + 1}</span>${this._pic(x.image_url, " small")}<div class="text"><span class="headline">${esc(x.name || t.unknownFigure)}</span>` +
          `${bar(x.times, max)}</div><span class="len">${esc(fill(t.placedTimes, { n: this._fmt(x.times) }))}</span></li>`).join("")}</ol>`);
      }
      if (s.top_chapters?.length) {
        const max = Math.max(...s.top_chapters.map((x) => x.seconds), 1);
        html += this._section(t.topChapters, `<ol class="top">${s.top_chapters.map((x, i) =>
          `<li><span class="rank">${i + 1}</span>${this._pic(x.image_url, " small")}<div class="text"><span class="headline">${esc(x.title || `${t.chapter} ${x.chapter + 1}`)}</span>` +
          `<span class="supporting">${esc(x.name || t.unknownFigure)} · ${esc(t.chapter)} ${x.chapter + 1}</span>` +
          `${bar(x.seconds, max)}</div><span class="len">${esc(hm(x.seconds))}</span></li>`).join("")}</ol>`);
      }
      if (s.per_box.length) {
        html += this._section(t.perBox, `<table class="kv">${s.per_box.map((b) =>
          `<tr><th>${esc(b.name || b.box_id)}</th><td>${esc(hm(b.seconds))} h</td></tr>`).join("")}</table>`);
      }
      return html + active;
    }

    // The change against the window of the same length before, while that one was counted
    _comparison(s) {
      if (!s.days || !Number.isFinite(s.previous_total_seconds) || s.previous_total_seconds <= 0) return "";
      const change = Math.round(((s.total_seconds - s.previous_total_seconds) / s.previous_total_seconds) * 100);
      const p = `${change > 0 ? "+" : change < 0 ? "−" : "±"}${this._fmt(Math.abs(change))} %`;
      const kind = change > 0 ? "ok" : change < 0 ? "warn" : "";
      return `<div class="compare">${this._chip(fill(this._t.vsBefore, { p, n: this._fmt(s.days) }), kind)}</div>`;
    }

    // Weekdays as rows, hours as columns; the shade is the share of the busiest cell,
    // each cell says its time in words. With several boxes, one or all of them
    _heatmap(s) {
      const t = this._t;
      const boxes = Array.isArray(s.heatmap_boxes) ? s.heatmap_boxes : [];
      const pick = boxes.find((b) => b.box_id === this._heatBox);
      const grid = pick ? pick.grid : s.heatmap;
      if (!Array.isArray(grid) || !grid.flat().some((v) => v > 0)) return "";
      const max = Math.max(...grid.flat(), 1);
      const days = WEEKDAYS.map((d) => this._dayName(d));
      let rows = "";
      grid.forEach((hrs, w) => {
        rows += `<div class="hm-day" aria-hidden="true">${esc(days[w])}</div>` + hrs.map((v, h) => {
          const label = `${days[w]} ${pad(h)}:00 · ${hm(v)} h`;
          return `<div class="hm-cell" role="img" style="--a:${(v / max).toFixed(3)}" aria-label="${esc(label)}" title="${esc(label)}"></div>`;
        }).join("");
      });
      const scale = `<div></div>` + Array.from({ length: 24 }, (_, h) => `<div class="hm-hour" aria-hidden="true">${h % 6 === 0 ? pad(h) : ""}</div>`).join("");
      const options = [{ value: "*", label: t.allBoxes }, ...boxes.map((b) => ({ value: b.box_id, label: b.name || b.box_id }))];
      const choose = boxes.length > 1
        ? `<ha-control-select id="heatbox" class="range heat-boxes" label="${esc(t.heatBoxLabel)}" data-options="${esc(JSON.stringify(options))}" data-value="${esc(pick ? pick.box_id : "*")}"></ha-control-select>`
        : "";
      return this._section(t.whenListened, `${choose}<div class="heatmap">${rows}${scale}</div>`, { help: t.whenHint });
    }

    // One bar per day of the window, per week when there are many; empty days stay empty
    _dayChart(s) {
      const t = this._t;
      const seconds = new Map(s.per_day.map((d) => [d.day, d.seconds]));
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      let start;
      if (s.days) {
        start = new Date(today);
        start.setDate(start.getDate() - (s.days - 1));
      } else {
        const first = s.first_day || s.per_day[0]?.day;
        if (!first) return "";
        start = parseDay(first);
      }
      if (Number.isNaN(start.getTime()) || start > today) return "";
      const days = [];
      for (const d = new Date(start); d <= today && days.length < 4000; d.setDate(d.getDate() + 1)) days.push(dayKey(d));
      const weekly = days.length > WEEKS_FROM;
      let bars;
      if (weekly) {
        const weeks = new Map();
        for (const k of days) {
          const d = parseDay(k);
          d.setDate(d.getDate() - ((d.getDay() + 6) % 7));
          const w = dayKey(d);
          weeks.set(w, (weeks.get(w) || 0) + (seconds.get(k) || 0));
        }
        bars = [...weeks].map(([key, v]) => ({ key, v }));
      } else bars = days.map((key) => ({ key, v: seconds.get(key) || 0 }));
      const W = 800, H = 200, L = 44, R = 8, T = 10, B = 26;
      const top = Math.max(...bars.map((b) => b.v), 1);
      const step = [900, 1800, 3600, 7200, 10800, 18000, 36000, 72000, 180000, 360000, 720000].find((v) => top / v <= 4) || 720000;
      const yMax = Math.ceil(top / step) * step;
      const py = (v) => T + (1 - v / yMax) * (H - T - B);
      const slot = (W - L - R) / bars.length;
      const bw = Math.max(1, slot * 0.72);
      let grid = "";
      for (let v = 0; v <= yMax; v += step) {
        grid += `<line x1="${L}" x2="${W - R}" y1="${py(v).toFixed(1)}" y2="${py(v).toFixed(1)}" class="grid"/>` +
          `<text x="${L - 6}" y="${(py(v) + 4).toFixed(1)}" text-anchor="end">${esc(hm(v))}</text>`;
      }
      const marks = [0, Math.floor((bars.length - 1) / 2), bars.length - 1];
      const labels = [...new Set(marks)].map((i, n) =>
        `<text x="${(L + slot * (i + 0.5)).toFixed(1)}" y="${H - 8}" text-anchor="${["start", "middle", "end"][n]}">${esc(this._date(bars[i].key))}</text>`).join("");
      const rects = bars.map((b, i) => {
        const x = L + slot * i;
        const y = py(b.v);
        const tip = `${weekly ? fill(t.weekOf, { d: this._date(b.key, true) }) : this._date(b.key, true)}: ${hm(b.v)} h`;
        return `<rect class="hit" x="${x.toFixed(1)}" y="${T}" width="${slot.toFixed(2)}" height="${H - T - B}"><title>${esc(tip)}</title></rect>` +
          (b.v > 0 ? `<rect class="fill" x="${(x + (slot - bw) / 2).toFixed(2)}" y="${y.toFixed(1)}" width="${bw.toFixed(2)}" height="${(H - B - y).toFixed(1)}" rx="1"><title>${esc(tip)}</title></rect>` : "");
      }).join("");
      const busiest = bars.reduce((a, b) => (b.v > a.v ? b : a), bars[0]);
      const summary = fill(weekly ? t.chartWeeks : t.chartDays, {
        n: this._fmt(bars.length), total: hm(bars.reduce((a, b) => a + b.v, 0)),
        top: weekly ? fill(t.weekOf, { d: this._date(busiest.key, true) }) : this._date(busiest.key, true), v: hm(busiest.v),
      });
      return this._section(weekly ? t.perWeek : t.perDay, `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(summary)}">${grid}${labels}${rects}</svg>`);
    }

    // ---------------------------------------------------------------- setup

    // The steps of the setup with their state, leading to the first open one; the version below
    _setupPage() {
      const t = this._t;
      const o = this._overview;
      if (!o) return this._overviewState();
      const loaded = o.entries.filter((e) => e.loaded);
      const homes = this._households();
      const prefs = this._loadedEntries();
      const onOff = (v) => (v ? t.sOn : t.sOff);
      const prefLine = prefs.length
        ? [["analytics", t.prefAnalyticsShort], ["auto_lock", t.prefAutoLockShort], ["mark_read", t.prefMarkReadShort]]
          .map(([k, label]) => `${label} ${onOff(prefs[0].preferences[k])}`).join(" · ")
        : t.sOpen;
      const steps = [
        [INTEGRATION_PATH, t.stepAccount, loaded.length > 0,
          loaded.length ? loaded.map((e) => e.title).join(", ") : o.entries.length ? t.notLoaded : t.noEntry],
        ["setup/household", t.stepHousehold, homes.length > 0 && homes.every((h) => String(h.name || "").trim()),
          homes.length ? homes.map((h) => h.name).join(", ") : t.sOpen],
        ["setup/preferences", t.stepPreferences, prefs.length > 0, prefLine],
      ];
      const next = steps.find((x) => !x[2]);
      const items = steps.map(([path, title, done, sub], i) => this._item("go", path,
        `<span class="step${done ? " done" : ""}" role="img" aria-label="${esc(done ? t.stepDone : t.stepOpen)}">${done ? icon("check") : `<b>${i + 1}</b>`}</span>`,
        title, esc(sub))).join("");
      const actions = next ? this._btn("go", t.next, "", { look: "filled", data: ` data-key="${esc(next[0])}"` }) : "";
      let html = this._section(t.setupTitle, items, { cls: "list", help: t.setupHelp, actions });
      // What makes more possible, not needed for the rest
      const lib = this._library;
      const known = (v) => (lib ? !!v : null);
      const extras = [
        [t.stepFetcher, known(lib?.fetcher), t.h_fetcher],
        [t.stepPiper, known(lib?.speech), t.h_piper],
      ].map(([title, done, help]) => `<div class="item"><span class="step${done ? " done" : ""}" role="img" aria-label="${esc(done ? t.stepDone : t.stepOpen)}">` +
        `${icon(done ? "check" : "plus")}</span><div class="text"><span class="headline">${esc(title)}</span>` +
        `<span class="supporting">${esc(done == null ? "…" : done ? t.sInstalled : t.sOptional)}</span></div>${this._help(help)}</div>`).join("");
      html += this._section(t.extrasTitle, extras, { cls: "list" });
      const a = o.about;
      if (a?.version) html += `<div class="about">${esc(fill(a.commit ? t.aboutCommit : t.about, a))}</div>`;
      return html;
    }

    // The name of each household, and its members as the cloud shows them
    _householdPage() {
      const t = this._t;
      const state = this._overviewState();
      if (state) return state;
      const homes = this._households();
      if (!homes.length) return this._section("", `<div class="muted">${esc(t.noHouseholds)}</div>`);
      return homes.map((h) => {
        const scope = `home:${h.id}`;
        const title = homes.length > 1 ? h.name || h.id : t.prefHousehold;
        return this._section(title, this._row(scope, "name", t.householdName, t.h_householdName, { text: {} }), { cls: "rows" }) + this._members(h);
      }).join("");
    }

    // Who belongs to a household: shown only, managed in the app
    _members(h) {
      const t = this._t;
      if (!Array.isArray(h.members)) return this._alertHelp("info", t.membersUnknown, t.membersHint);
      const order = { owner: 0, full: 1, limited: 2 };
      const list = [...h.members].sort((a, b) => (order[a.role] ?? 3) - (order[b.role] ?? 3) || String(a.name).localeCompare(String(b.name)));
      const rows = list.map((m) => {
        const full = [m.first_name, m.last_name].filter(Boolean).join(" ");
        const title = full || m.name;
        const sub = [full && m.name !== full && m.name !== m.first_name ? m.name : "", m.email && m.email !== title ? m.email : ""].filter(Boolean).join(" · ");
        const initial = String(title || "?").trim().charAt(0).toUpperCase();
        return `<div class="item member"><span class="member-avatar" aria-hidden="true">${esc(initial)}</span>` +
          `<div class="text"><span class="headline">${esc(title)}</span>${sub ? `<span class="supporting">${esc(sub)}</span>` : ""}</div>` +
          `<span class="badges">${m.self ? this._chip(t.memberYou, "on") : ""}${this._chip(t[`role_${m.role}`] || t.role_unknown, m.role === "owner" ? "ok" : "")}</span></div>`;
      }).join("");
      return this._section(fill(t.membersCount, { n: this._fmt(list.length) }), rows, { cls: "list", help: t.membersHint });
    }

    // The integration's log: its level, kept across restarts, and the latest lines
    _logPage() {
      const t = this._t;
      const log = this._log;
      if (!log) return this._errors.log ? this._errHtml(this._errors.log) : this._loadingHtml();
      const options = LOG_LEVELS.map((l) => ({ value: l, label: t[`logL_${l}`] }));
      let level = this._row("log:all", "level", t.logLevel, t.logLevelHint, { select: { mode: "dropdown", options } }) +
        this._row("log:all", "days", t.logDays, t.logDaysHint, { text: { suffix: t.logDaysUnit } }, true);
      if (LOG_LEVELS.indexOf(log.effective) >= 0 && LOG_LEVELS.indexOf(log.effective) < LOG_LEVELS.indexOf(log.level)) {
        level += this._alert(fill(t.logEffective, { l: t[`logL_${log.effective}`] }), "info");
      }
      let html = this._section(t.logLevel, level, { cls: "rows" });
      const lines = log.lines || [];
      const body = lines.length
        ? `<div class="log">${lines.map((l) => `<div class="log-line ${esc(l.level)}"><span class="log-time">${esc(this._logTime(l.time))}</span>` +
          `<span class="log-level">${esc(l.level.toUpperCase())}</span><span class="log-source">${esc(l.source)}</span>` +
          `<span class="log-msg">${esc(l.message)}</span></div>`).join("")}</div>`
        : `<div class="muted">${esc(t.logEmpty)}</div>`;
      const actions = lines.length
        ? this._btn("logcopy", t.logCopy, "copy") + (log.days ? this._btn("logsave", t.logDownload, "download") : "")
        : "";
      html += this._section(t.logLines, body, { help: log.days ? t.logLinesHint : t.logLinesMemoryHint, actions });
      return html;
    }

    _logTime(iso) {
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) return iso;
      const ms = String(d.getMilliseconds()).padStart(3, "0");
      return `${d.toLocaleDateString(this._lang, { day: "2-digit", month: "2-digit" })} ${d.toLocaleTimeString(this._lang, { hour12: false })}.${ms}`;
    }

    _logText(lines) {
      return lines.map((l) => `${l.time} ${l.level.toUpperCase()} [${l.source}] ${l.message}`).join("\n");
    }

    // Every line kept on disk, oldest first, as a text file
    async _downloadLog() {
      try {
        const all = await this._hass.callWS({ type: "storybox_plus/log" });
        const blob = new Blob([`${this._logText([...all.lines].reverse())}\n`], { type: "text/plain" });
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `storybox_plus-${new Date().toISOString().slice(0, 10)}.log`;
        a.click();
        window.setTimeout(() => URL.revokeObjectURL(a.href), 1000);
      } catch (err) {
        this._note = this._error(err);
        this._render();
      }
    }

    async _copyLog() {
      const lines = this._log?.lines || [];
      const text = this._logText(lines);
      try {
        await navigator.clipboard.writeText(text);
        this._done = { kind: "success", text: this._t.logCopied };
      } catch (err) {
        this._note = this._error(err);
      }
      this._render();
    }

    // The Piper voice for text chapters: the voices of the page's language, or Piper's own
    _voiceRow(scope, e) {
      const t = this._t;
      const engine = this._overview?.speech_engine;
      if (!engine) return this._infoRow(t.prefVoice, t.prefVoiceHint, t.prefVoiceNone);
      if (!this._voices) {
        this._loadVoices(engine);
        return this._infoRow(t.prefVoice, t.prefVoiceHint, t.loading);
      }
      const options = [{ value: DEFAULT_VOICE, label: t.prefVoiceDefault }, ...this._voices];
      const current = this._saved(scope)?.voice;
      if (current && current !== DEFAULT_VOICE && !options.some((o) => o.value === current)) options.push({ value: current, label: current.split("|")[1] });
      return this._row(scope, "voice", t.prefVoice, t.prefVoiceHint, { select: { mode: "dropdown", options } });
    }

    async _loadVoices(engine) {
      if (this._voicesLoading) return;
      this._voicesLoading = true;
      try {
        const info = await this._hass.callWS({ type: "tts/engine/get", engine_id: engine });
        const base = String(this._hass.locale?.language || this._hass.language || "en").split(/[-_]/)[0].toLowerCase();
        const langs = (info.provider?.supported_languages || []).filter((l) => l.split(/[-_]/)[0].toLowerCase() === base);
        const voices = [];
        for (const language of langs) {
          const answer = await this._hass.callWS({ type: "tts/engine/voices", engine_id: engine, language });
          for (const v of answer.voices || []) voices.push({ value: `${language}|${v.voice_id}`, label: langs.length > 1 ? `${v.name} · ${language}` : v.name });
        }
        this._voices = voices;
      } catch (err) {
        this._voices = [];
      }
      this._voicesLoading = false;
      this._render();
    }

    // The settings of each account by topic, and the version of the cloud
    _preferencesPage() {
      const t = this._t;
      const state = this._overviewState();
      if (state) return state;
      const entries = this._loadedEntries();
      let html = "";
      for (const e of entries) {
        const scope = `pref:${e.entry_id}`;
        const named = (title) => (entries.length > 1 ? `${title} · ${e.title}` : title);
        const keep = ANALYTICS_DAYS.map((d) => ({ value: d, label: t[`prefKeep_${d}`] }));
        html += this._section(named(t.prefListening),
          this._row(scope, "analytics", t.prefAnalytics, t.prefAnalyticsHint, { boolean: {} }) +
          this._row(scope, "analytics_days", t.prefKeep, t.prefKeepHint, { select: { mode: "dropdown", options: keep } }), { cls: "rows" });
        html += this._section(named(t.prefFigures), this._row(scope, "auto_lock", t.prefAutoLock, t.prefAutoLockHint, { boolean: {} }), { cls: "rows" });
        html += this._section(named(t.prefNotices), this._row(scope, "mark_read", t.prefMarkRead, t.prefMarkReadHint, { boolean: {} }), { cls: "rows" });
        html += this._section(named(t.prefChapters),
          this._voiceRow(scope, e) +
          this._row(scope, "fetch_max_mb", t.prefFetchMax, t.prefFetchMaxHint, { text: { suffix: "MB" } }, true), { cls: "rows" });
        // Only the release counts, not the commit behind it
        const c = e.cloud || {};
        let cloud;
        if (!c.version) cloud = this._alertHelp("info", t.cloudUnknown, t.cloudHelp);
        else if (c.matches) cloud = this._alertHelp("success", `${fill(t.cloudVersion, { v: c.version })} · ${t.cloudTested}`, t.cloudHelp);
        else cloud = this._alertHelp("warning", `${fill(t.cloudVersion, { v: c.version })} · ${fill(t.cloudUntested, { t: c.tested })}`, fill(t.cloudDiffers, { v: c.release, t: c.tested }));
        html += this._section(named(t.prefCloud), cloud);
      }
      return html;
    }
  }

  customElements.define("storybox-plus-panel", StoryboxPlusPanel);
}
