// Storybox Plus panel: the page in the sidebar where administrators see their
// boxes with the live state, the figures of the household with their chapters
// and the listening statistics. Everything comes from the integration over the
// WebSocket API; the page looks like Home Assistant's own.
const VERSION = "0.1.0";
// The boxes are asked again this often while their tab is open (ms)
const REFRESH = 10000;
// A chart with more days than this groups them by week
const WEEKS_FROM = 120;

if (!customElements.get("storybox-plus-panel")) {
  const MDI = {
    menu: "M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z",
    boxes: "M12,12A3,3 0 0,0 9,15A3,3 0 0,0 12,18A3,3 0 0,0 15,15A3,3 0 0,0 12,12M12,20A5,5 0 0,1 7,15A5,5 0 0,1 12,10A5,5 0 0,1 17,15A5,5 0 0,1 12,20M12,4A2,2 0 0,1 14,6A2,2 0 0,1 12,8C10.89,8 10,7.1 10,6C10,4.89 10.89,4 12,4M17,2H7C5.89,2 5,2.89 5,4V20A2,2 0 0,0 7,22H17A2,2 0 0,0 19,20V4C19,2.89 18.1,2 17,2Z",
    figures: "M12,3V13.55C11.41,13.21 10.73,13 10,13A4,4 0 0,0 6,17A4,4 0 0,0 10,21A4,4 0 0,0 14,17V7H18V3H12Z",
    listening: "M22,21H2V3H4V19H6V10H10V19H12V6H16V19H18V14H22V21Z",
    refresh: "M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z",
    search: "M9.5,3A6.5,6.5 0 0,1 16,9.5C16,11.11 15.41,12.59 14.44,13.73L14.71,14H15.5L20.5,19L19,20.5L14,15.5V14.71L13.73,14.44C12.59,15.41 11.11,16 9.5,16A6.5,6.5 0 0,1 3,9.5A6.5,6.5 0 0,1 9.5,3M9.5,5C7,5 5,7 5,9.5C5,12 7,14 9.5,14C12,14 14,12 14,9.5C14,7 12,5 9.5,5Z",
    lock: "M12,17A2,2 0 0,0 14,15C14,13.89 13.1,13 12,13A2,2 0 0,0 10,15A2,2 0 0,0 12,17M18,8A2,2 0 0,1 20,10V20A2,2 0 0,1 18,22H6A2,2 0 0,1 4,20V10C4,8.89 4.9,8 6,8H7V6A5,5 0 0,1 12,1A5,5 0 0,1 17,6V8H18M12,3A3,3 0 0,0 9,6V8H15V6A3,3 0 0,0 12,3Z",
    chevron: "M7.41,8.58L12,13.17L16.59,8.58L18,10L12,15.41L6,9.41L7.41,8.58Z",
    play: "M8,5.14V19.14L19,12.14L8,5.14Z",
    pause: "M14,19H18V5H14M6,19H10V5H6V19Z",
    flash: "M7,2V13H10V22L17,10H13L17,2H7Z",
    volume: "M5,9V15H9L14,20V4L9,9M18.5,12C18.5,10.23 17.5,8.71 16,7.97V16C17.5,15.29 18.5,13.76 18.5,12Z",
    sleep: "M23,12H17V10L20.39,6H17V4H23V6L19.62,10H23V12M15,16H9V14L12.39,10H9V8H15V10L11.62,14H15V16M7,20H1V18L4.39,14H1V12H7V14L3.62,18H7V20Z",
    info: "M11,9H13V7H11M12,20C7.59,20 4,16.41 4,12C4,7.59 7.59,4 12,4C16.41,4 20,7.59 20,12C20,16.41 16.41,20 12,20M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M11,17H13V11H11V17Z",
    alert: "M13,13H11V7H13M13,17H11V15H13M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z",
    pencil: "M20.71,7.04C21.1,6.65 21.1,6 20.71,5.63L18.37,3.29C18,2.9 17.35,2.9 16.96,3.29L15.12,5.12L18.87,8.87M3,17.25V21H6.75L17.81,9.93L14.06,6.18L3,17.25Z",
    check: "M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z",
    close: "M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z",
    upload: "M9,16V10H5L12,3L19,10H15V16H9M5,20V18H19V20H5Z",
    up: "M13,20H11V8L5.5,13.5L4.08,12.08L12,4.16L19.92,12.08L18.5,13.5L13,8V20Z",
    down: "M11,4H13V16L18.5,10.5L19.92,11.92L12,19.84L4.08,11.92L5.5,10.5L11,16V4Z",
    remove: "M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z",
    link: "M10.59,13.41C11,13.8 11,14.44 10.59,14.83C10.2,15.22 9.56,15.22 9.17,14.83C7.22,12.88 7.22,9.71 9.17,7.76V7.76L12.71,4.22C14.66,2.27 17.83,2.27 19.78,4.22C21.73,6.17 21.73,9.34 19.78,11.29L18.29,12.78C18.3,11.96 18.17,11.14 17.89,10.36L18.36,9.88C19.54,8.71 19.54,6.81 18.36,5.64C17.19,4.46 15.29,4.46 14.12,5.64L10.59,9.17C9.41,10.34 9.41,12.24 10.59,13.41M13.41,9.17C13.8,8.78 14.44,8.78 14.83,9.17C16.78,11.12 16.78,14.29 14.83,16.24V16.24L11.29,19.78C9.34,21.73 6.17,21.73 4.22,19.78C2.27,17.83 2.27,14.66 4.22,12.71L5.71,11.22C5.7,12.04 5.83,12.86 6.11,13.65L5.64,14.12C4.46,15.29 4.46,17.19 5.64,18.36C6.81,19.54 8.71,19.54 9.88,18.36L13.41,14.83C14.59,13.66 14.59,11.76 13.41,10.59C13,10.2 13,9.56 13.41,9.17Z",
  };
  // How often a creative figure is read again while the cloud converts its chapters (ms)
  const CONVERT_REFRESH = 15000;
  // Audio the cloud converts; the list only helps the file picker, the cloud decides
  const AUDIO_TYPES = "audio/*,.mp3,.m4a,.m4b,.aac,.ogg,.oga,.opus,.wav,.flac,.wma";

  // Tab id (also the URL hash), icon, text
  const TABS = [
    ["boxes", "boxes", "tabBoxes"],
    ["figures", "figures", "tabFigures"],
    ["listening", "listening", "tabListening"],
  ];
  const KINDS = ["all", "content", "creative", "disc"];
  // Range chip, days asked from the backend (null: since the setup)
  const RANGES = [["7", 7], ["30", 30], ["365", 365], ["all", null]];

  const TEXTS = {
    en: {
      tabBoxes: "Boxes", tabFigures: "Figures", tabListening: "Listening",
      menu: "Menu", refresh: "Refresh", retry: "Try again", loading: "Loading …",
      failed: "The data could not be read",
      noEntry: "No account is set up. Add one under Settings → Devices & services.",
      notLoaded: "No account is loaded at the moment. Home Assistant tries again by itself.",
      pushDown: "Live channel not connected – states may be stale",
      noBoxes: "No box in this account yet.", toniebox2: "Toniebox 2", classic: "Toniebox",
      online: "Online", offline: "Offline", unknown: "Unknown", charging: "charging",
      sleepUntil: "Sleep timer until {t}", sleepOn: "Sleep timer active", firmware: "Firmware",
      classicNote: "The classic box reports no live data.", lastSeen: "Last seen {t}", never: "never",
      battery: "Battery", perFull: "about {h} h per full charge", perFullProjected: "about {h} h per full charge, projected",
      charge1: "1 charge", chargesN: "{n} charges", nowSince: "now {t} since {p} %", noCycles: "no discharge recorded yet",
      history: "Charge history", colDay: "Day", colOn: "Run time", colLevel: "Level", colPerFull: "Per full charge",
      playing: "Playing", paused: "Paused", placed: "Figure placed", nothing: "Nothing on the box",
      chapter: "Chapter", unknownFigure: "Unknown figure", search: "Search figures and chapters …",
      kind_all: "All", kind_content: "Tonies", kind_creative: "Creative-Tonies", kind_disc: "Discs",
      kind1_creative: "Creative-Tonie", kind1_disc: "Disc",
      figure1: "1 figure", figuresAll: "{n} figures", figuresOf: "{n} of {m} figures",
      noFigures: "No figure in the household yet.", noMatch: "No figure matches.",
      chapter1: "1 chapter", chaptersN: "{n} chapters", noChapters: "No chapters yet.",
      onBox: "on {box}", locked: "Locked", transcoding: "converting", free: "Free: {t} h",
      edit: "Edit", save: "Save", cancel: "Cancel", upload: "Upload", dismiss: "Dismiss",
      moveUp: "Move up", moveDown: "Move down", remove: "Remove",
      editHint: "The changes are sent together when you save. The cloud then converts the figure anew, and a box downloads it again.",
      uploading: "Uploading {name} ({n} of {m}) …", uploadFailed: "Upload failed: {e}", saveFailed: "Saving failed: {e}",
      fromLink: "From YouTube", add: "Add", linkPlaceholder: "Link to a YouTube video",
      linkHint: "The audio of the video becomes a chapter, named after the video. It is fetched through Home Assistant.",
      linkProbe: "Reading the video …", linkFetch: "Fetching {name} …", linkFetchPct: "Fetching {name} ({p} %) …",
      linkConvert: "Converting {name} …", linkUpload: "Uploading {name} to the cloud …", linkFailed: "Adding from YouTube failed: {e}",
      fetcherMissing: "Needs the Media Fetcher app: install it in Home Assistant under Settings → Apps.",
      convErrors: "The last conversion dropped chapters: {r}",
      reason_wrongFormat: "unsupported format", reason_tooLong: "more than 90 minutes in total", reason_unknownError: "unknown error",
      range_7: "7 days", range_30: "30 days", range_365: "365 days", range_all: "All",
      lastDays: "last {n} days", since: "since {d}", sinceSetup: "since the setup",
      total: "Listening time", top: "Most played", perDay: "Per day", perWeek: "Per week", perBox: "Per box",
      weekOf: "Week of {d}",
      noteLocalTitle: "Counted locally",
      noteLocal: "Home Assistant counts the listening time itself, from what a Toniebox 2 reports live. It does not come from the manufacturer's cloud and so cannot be complete: it starts with the setup, the classic Toniebox is missing, and so is anything played while Home Assistant was not running.",
      disabled: "Counting is switched off in the integration's options.", noStats: "Nothing was counted yet.",
    },
    de: {
      tabBoxes: "Boxen", tabFigures: "Figuren", tabListening: "Hörzeit",
      menu: "Menü", refresh: "Aktualisieren", retry: "Erneut versuchen", loading: "Lädt …",
      failed: "Die Daten ließen sich nicht lesen",
      noEntry: "Kein Konto eingerichtet. Unter Einstellungen → Geräte & Dienste hinzufügen.",
      notLoaded: "Gerade ist kein Konto geladen. Home Assistant versucht es selbst erneut.",
      pushDown: "Live-Kanal nicht verbunden – Zustände können veraltet sein",
      noBoxes: "Noch keine Box in diesem Konto.", toniebox2: "Toniebox 2", classic: "Toniebox",
      online: "Online", offline: "Offline", unknown: "Unbekannt", charging: "lädt",
      sleepUntil: "Schlaf-Timer bis {t}", sleepOn: "Schlaf-Timer aktiv", firmware: "Firmware",
      classicNote: "Die klassische Box meldet keine Live-Daten.", lastSeen: "Zuletzt gesehen {t}", never: "nie",
      battery: "Akku", perFull: "etwa {h} h pro Ladung", perFullProjected: "voraussichtlich etwa {h} h pro Ladung",
      charge1: "1 Ladung", chargesN: "{n} Ladungen", nowSince: "jetzt {t} seit {p} %", noCycles: "noch kein Entladezyklus erfasst",
      history: "Ladungsverlauf", colDay: "Tag", colOn: "Laufzeit", colLevel: "Ladestand", colPerFull: "Pro Ladung",
      playing: "Spielt", paused: "Pausiert", placed: "Figur aufgestellt", nothing: "Nichts auf der Box",
      chapter: "Kapitel", unknownFigure: "Unbekannte Figur", search: "Figuren und Kapitel suchen …",
      kind_all: "Alle", kind_content: "Tonies", kind_creative: "Kreativ-Tonies", kind_disc: "Discs",
      kind1_creative: "Kreativ-Tonie", kind1_disc: "Disc",
      figure1: "1 Figur", figuresAll: "{n} Figuren", figuresOf: "{n} von {m} Figuren",
      noFigures: "Noch keine Figur im Haushalt.", noMatch: "Keine Figur passt.",
      chapter1: "1 Kapitel", chaptersN: "{n} Kapitel", noChapters: "Noch keine Kapitel.",
      onBox: "auf {box}", locked: "Gesperrt", transcoding: "wird umgewandelt", free: "Frei: {t} h",
      edit: "Bearbeiten", save: "Speichern", cancel: "Abbrechen", upload: "Hochladen", dismiss: "Schließen",
      moveUp: "Nach oben", moveDown: "Nach unten", remove: "Entfernen",
      editHint: "Die Änderungen gehen beim Speichern gesammelt in die Cloud. Sie wandelt die Figur danach neu um, und eine Box lädt sie neu.",
      uploading: "Lädt {name} hoch ({n} von {m}) …", uploadFailed: "Hochladen fehlgeschlagen: {e}", saveFailed: "Speichern fehlgeschlagen: {e}",
      fromLink: "Von YouTube", add: "Hinzufügen", linkPlaceholder: "Link zu einem YouTube-Video",
      linkHint: "Der Ton des Videos wird ein Kapitel, benannt nach dem Video. Er wird über Home Assistant geholt.",
      linkProbe: "Liest das Video …", linkFetch: "Holt {name} …", linkFetchPct: "Holt {name} ({p} %) …",
      linkConvert: "Wandelt {name} um …", linkUpload: "Lädt {name} in die Cloud hoch …", linkFailed: "Hinzufügen von YouTube fehlgeschlagen: {e}",
      fetcherMissing: "Dafür wird die App „Media Fetcher“ gebraucht: in Home Assistant unter Einstellungen → Apps installieren.",
      convErrors: "Die letzte Umwandlung hat Kapitel verworfen: {r}",
      reason_wrongFormat: "nicht unterstütztes Format", reason_tooLong: "insgesamt mehr als 90 Minuten", reason_unknownError: "unbekannter Fehler",
      range_7: "7 Tage", range_30: "30 Tage", range_365: "365 Tage", range_all: "Alles",
      lastDays: "letzte {n} Tage", since: "seit {d}", sinceSetup: "seit der Einrichtung",
      total: "Hörzeit", top: "Meistgehört", perDay: "Pro Tag", perWeek: "Pro Woche", perBox: "Pro Box",
      weekOf: "Woche vom {d}",
      noteLocalTitle: "Lokal mitgezählt",
      noteLocal: "Home Assistant zählt die Hörzeit selbst mit, aus dem, was eine Toniebox 2 live meldet. Sie stammt nicht aus der Hersteller-Cloud und ist deshalb nicht vollständig: Sie beginnt mit der Einrichtung, die klassische Toniebox fehlt, und Zeiten, in denen Home Assistant nicht lief, fehlen ebenso.",
      disabled: "Das Zählen ist in den Optionen der Integration ausgeschaltet.", noStats: "Noch nichts gezählt.",
    },
  };

  const esc = (v) =>
    String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const icon = (name) => `<svg class="mdi" viewBox="0 0 24 24" aria-hidden="true"><path d="${MDI[name]}"/></svg>`;
  const fill = (text, values) => text.replace(/\{(\w+)\}/g, (_, k) => values[k] ?? "");
  const time = (iso) => (iso ? Date.parse(iso) : NaN);
  // Only web addresses go into an <img>
  const safeUrl = (u) => (typeof u === "string" && /^https?:\/\//i.test(u) ? u : null);
  const pad = (n) => String(n).padStart(2, "0");
  // h:mm for lengths and listening time, m:ss for positions and chapters
  const hm = (s) => {
    if (!Number.isFinite(s) || s < 0) return "–";
    const m = Math.round(s / 60);
    return `${Math.floor(m / 60)}:${pad(m % 60)}`;
  };
  const mmss = (s) => {
    if (!Number.isFinite(s) || s < 0) return "–:––";
    const v = Math.floor(s);
    return `${Math.floor(v / 60)}:${pad(v % 60)}`;
  };
  // Battery hours from the backend, as "h:mm h"; nothing is made of a missing value
  const hours = (h) => (Number.isFinite(h) ? `${hm(h * 3600)} h` : "–");
  const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
  // Local calendar days as "YYYY-MM-DD", like the backend's per_day keys
  const dayKey = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  const parseDay = (key) => {
    const [y, m, d] = String(key).split("-").map(Number);
    return new Date(y, (m || 1) - 1, d || 1);
  };
  const tabFromHash = () => {
    const id = (window.location.hash || "").slice(1);
    return TABS.some(([t]) => t === id) ? id : "boxes";
  };

  class StoryboxPlusPanel extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._tab = tabFromHash();
      this._overview = null;
      this._library = null;
      this._stats = {};
      this._errors = {};
      this._busy = new Set();
      this._query = "";
      this._kind = "all";
      this._open = new Set();
      this._range = "30";
      this._frameKey = null;
      // The chapters of one creative figure being rearranged: { id, chapters, saving, error }
      this._edit = null;
      // Uploads per creative figure: { total, done, name, error }
      this._uploads = {};
      // The open link field of a creative figure: { id, url }
      this._link = null;
      this._uploadTarget = null;
      this._bindOnce();
    }

    set hass(hass) {
      const first = !this._hass;
      this._hass = hass;
      if (first) {
        this._ensure();
        this._syncTimers();
      }
      if (first || this._menuShown !== this._showMenu) this._render();
    }

    set narrow(narrow) {
      this._narrow = narrow;
      this._render();
    }

    set route(route) {
      this._route = route;
    }

    set panel(panel) {
      this._panelInfo = panel;
    }

    connectedCallback() {
      this._onHash = () => {
        const tab = tabFromHash();
        if (tab !== this._tab) this._go(tab);
      };
      this._onVisible = () => {
        this._syncTimers();
        if (document.visibilityState === "visible") this._ensure();
      };
      window.addEventListener("hashchange", this._onHash);
      document.addEventListener("visibilitychange", this._onVisible);
      this._syncTimers();
      if (this._hass) this._ensure();
    }

    disconnectedCallback() {
      window.removeEventListener("hashchange", this._onHash);
      document.removeEventListener("visibilitychange", this._onVisible);
      this._syncTimers();
    }

    get _lang() {
      return this._hass?.locale?.language || this._hass?.language || "en";
    }

    get _t() {
      return this._lang.toLowerCase().startsWith("de") ? TEXTS.de : TEXTS.en;
    }

    get _showMenu() {
      return !!this._narrow || this._hass?.dockedSidebar === "always_hidden";
    }

    // Loads what the open tab shows; the figures also need the boxes' names
    _ensure() {
      if (!this._hass || document.visibilityState === "hidden") return;
      if (this._tab === "boxes") this._loadOverview();
      else if (this._tab === "figures") {
        this._loadLibrary();
        if (!this._overview) this._loadOverview();
      } else this._loadStats(this._range);
    }

    // The boxes are polled and their progress ticks only while their tab shows; the
    // figures are watched for a conversion only while theirs does
    _syncTimers() {
      const visible = this.isConnected && document.visibilityState === "visible";
      const live = visible && this._tab === "boxes";
      if (live && !this._poll) {
        this._poll = window.setInterval(() => this._loadOverview(), REFRESH);
        this._ticker = window.setInterval(() => this._tick(), 1000);
      } else if (!live && this._poll) {
        window.clearInterval(this._poll);
        window.clearInterval(this._ticker);
        this._poll = this._ticker = null;
      }
      const figures = visible && this._tab === "figures";
      if (figures && !this._convPoll) {
        this._convPoll = window.setInterval(() => this._refreshConverting(), CONVERT_REFRESH);
      } else if (!figures && this._convPoll) {
        window.clearInterval(this._convPoll);
        this._convPoll = null;
      }
    }

    async _fetch(key, msg, keep) {
      if (!this._hass || this._busy.has(key)) return;
      this._busy.add(key);
      try {
        keep(await this._hass.callWS(msg));
        delete this._errors[key];
      } catch (err) {
        this._errors[key] = err?.message || String(err);
      }
      this._busy.delete(key);
      this._render();
    }

    _loadOverview() {
      return this._fetch("overview", { type: "storybox_plus/overview" }, (d) => { this._overview = d; });
    }

    _loadLibrary() {
      return this._fetch("library", { type: "storybox_plus/library" }, (d) => { this._library = d; });
    }

    _loadStats(range) {
      const days = RANGES.find(([k]) => k === range)?.[1] ?? null;
      return this._fetch(`stats:${range}`, { type: "storybox_plus/analytics", days, limit: 10 }, (d) => { this._stats[range] = d; });
    }

    // The tab lives in the URL hash, so a reload keeps it
    _go(tab) {
      if (!TABS.some(([t]) => t === tab)) tab = "boxes";
      if (window.location.hash !== `#${tab}`) window.history.replaceState(window.history.state, "", `#${tab}`);
      this._tab = tab;
      this._render();
      this._ensure();
      this._syncTimers();
    }

    // One listener each on the shadow root: the content under it is redrawn
    _bindOnce() {
      const root = this.shadowRoot;
      root.addEventListener("click", (e) => {
        const el = e.target;
        const tab = el.closest?.("a[data-tab]");
        if (tab) {
          e.preventDefault();
          this._go(tab.dataset.tab);
          return;
        }
        const act = el.closest?.("[data-act]")?.dataset.act;
        if (act === "menu") this.dispatchEvent(new CustomEvent("hass-toggle-menu", { bubbles: true, composed: true }));
        if (act === "refresh" || act === "retry") this._ensure();
        if (act) this._chapterAction(act);
        const range = el.closest?.("[data-range]");
        if (range) {
          this._range = range.dataset.range;
          this._render();
          this._loadStats(this._range);
        }
        const kind = el.closest?.("[data-kind]");
        if (kind) {
          this._kind = kind.dataset.kind;
          for (const c of root.querySelectorAll("[data-kind]")) c.classList.toggle("on", c.dataset.kind === this._kind);
          this._refreshList();
        }
        // A fold (a figure's chapters, a box's charge history) opens and closes on its head
        const head = el.closest?.("[data-fold]");
        if (head) {
          const id = head.dataset.fold;
          const open = !this._open.has(id);
          if (open) this._open.add(id); else this._open.delete(id);
          head.parentElement.classList.toggle("open", open);
          head.setAttribute("aria-expanded", String(open));
          this._sheetHtml = this._content();
        }
      });
      root.addEventListener("input", (e) => {
        if (e.target.id === "link-url" && this._link) this._link.url = e.target.value;
        if (e.target.id !== "search") return;
        this._query = e.target.value;
        this._refreshList();
      });
      root.addEventListener("submit", (e) => {
        if (e.target.id !== "link-form") return;
        e.preventDefault();
        this._fetchLink();
      });
      // The hidden file field of the frame serves every creative figure in turn
      root.addEventListener("change", (e) => {
        if (e.target.id !== "upload") return;
        const files = [...e.target.files];
        e.target.value = "";
        if (this._uploadTarget && files.length) this._uploadFiles(this._uploadTarget, files);
      });
      // A picture that does not load leaves the placeholder behind it visible
      root.addEventListener("error", (e) => {
        if (e.target?.tagName === "IMG") e.target.classList.add("broken");
      }, true);
    }

    // Only the list under the filters is redrawn, so the search field keeps its focus
    _refreshList() {
      const list = this.shadowRoot.getElementById("figlist");
      if (!list) return this._render();
      list.innerHTML = this._figureList();
      this._sheetHtml = this._content();
    }

    _render() {
      if (!this._hass) return;
      const key = [this._tab, !!this._narrow, this._showMenu, this._lang].join("|");
      if (key !== this._frameKey) {
        this._frameKey = key;
        this._menuShown = this._showMenu;
        this._frame();
      }
      const sheet = this.shadowRoot.getElementById("sheet");
      const html = this._content();
      if (sheet && html !== this._sheetHtml) {
        this._sheetHtml = html;
        sheet.innerHTML = html;
        this._tick();
      }
    }

    // The parts that stay while the page is open: toolbar and tabs
    _frame() {
      const t = this._t;
      const tabs = TABS.map(([id, ic, label]) =>
        `<a class="tab${this._tab === id ? " active" : ""}" data-tab="${id}" href="#${id}">` +
        `${this._narrow ? icon(ic) : ""}<span>${esc(t[label])}</span></a>`).join("");
      const menu = this._showMenu
        ? `<button class="icon-button menu-button" data-act="menu" title="${esc(t.menu)}">${icon("menu")}</button>`
        : "";
      this.shadowRoot.innerHTML = `<style>${STYLE}</style><div class="app${this._narrow ? " narrow" : ""}">` +
        `<div class="toolbar">${menu}<div class="main-title">Storybox Plus</div>${this._narrow ? "" : `<nav class="tabs">${tabs}</nav>`}` +
        `<div class="tools"><button class="icon-button" data-act="refresh" title="${esc(t.refresh)}">${icon("refresh")}</button></div></div>` +
        `<div class="content"><div class="sheet" id="sheet"></div></div>${this._narrow ? `<nav class="bottom-tabs">${tabs}</nav>` : ""}` +
        `<input type="file" id="upload" accept="${AUDIO_TYPES}" multiple hidden></div>`;
      this._sheetHtml = null;
    }

    _content() {
      switch (this._tab) {
        case "figures": return this._figures();
        case "listening": return this._listening();
        default: return this._boxes();
      }
    }

    // Formatting in the language of Home Assistant
    _date(key, long = false) {
      const d = parseDay(key);
      if (Number.isNaN(d.getTime())) return "–";
      return d.toLocaleDateString(this._lang, long
        ? { weekday: "short", day: "numeric", month: "short", year: "numeric" }
        : { day: "numeric", month: "short" });
    }

    _num(n) {
      return Number.isFinite(n) ? n.toLocaleString(this._lang, { maximumFractionDigits: 1 }) : "–";
    }

    _relative(iso) {
      const ms = time(iso);
      if (!Number.isFinite(ms)) return this._t.never;
      const diff = (ms - Date.now()) / 1000;
      const abs = Math.abs(diff);
      const [unit, div] = abs < 60 ? ["second", 1] : abs < 3600 ? ["minute", 60] : abs < 86400 ? ["hour", 3600] : ["day", 86400];
      return new Intl.RelativeTimeFormat(this._lang, { numeric: "auto" }).format(Math.round(diff / div), unit);
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

    _card(title, body, extra = "") {
      return `<div class="card${extra}">${title ? `<h2>${title}</h2>` : ""}<div class="card-content">${body}</div></div>`;
    }

    _chip(text, kind = "") {
      return `<span class="chip ${kind}">${esc(text)}</span>`;
    }

    _alert(text, kind = "") {
      return `<div class="alert ${kind}">${esc(text)}</div>`;
    }

    _fail(message) {
      return `<div class="alert err">${esc(this._t.failed)}: ${esc(message)} ` +
        `<button class="text-button" data-act="retry">${esc(this._t.retry)}</button></div>`;
    }

    _loading() {
      return `<div class="muted">${esc(this._t.loading)}</div>`;
    }

    _pic(url, extra = "") {
      const src = safeUrl(url);
      return `<div class="pic${extra}">${icon("figures")}${src ? `<img src="${esc(src)}" alt="" loading="lazy">` : ""}</div>`;
    }

    // ---------------------------------------------------------------- boxes

    _boxes() {
      const t = this._t;
      const o = this._overview;
      const err = this._errors.overview;
      if (!o) return err ? this._fail(err) : this._loading();
      let html = err ? this._fail(err) : "";
      if (!o.entries.length) return html + this._alert(t.noEntry);
      if (!o.entries.some((e) => e.loaded)) return html + this._alert(t.notLoaded);
      // Only a Toniebox 2 uses the live channel
      if (!o.push_connected && o.boxes.some((b) => b.generation === "toniebox_2")) html += this._alert(t.pushDown, "warn");
      if (!o.boxes.length) return html + this._card("", `<div class="muted">${esc(t.noBoxes)}</div>`);
      const households = new Set(o.boxes.map((b) => b.household).filter(Boolean));
      return html + `<div class="grid">${o.boxes.map((b) => this._box(b, households.size > 1)).join("")}</div>`;
    }

    _box(b, showHousehold) {
      const t = this._t;
      const live = b.generation === "toniebox_2";
      const [state, label] = b.online === true ? ["ok", t.online] : b.online === false ? ["err", t.offline] : ["", t.unknown];
      const chips = this._chip(live ? t.toniebox2 : t.classic) + (showHousehold && b.household ? this._chip(b.household) : "");
      const title = `<span class="box-name">${esc(b.name || b.id)}</span><span class="chips">${chips}</span>` +
        `<span class="status"><span class="dot ${state}"></span>${esc(label)}</span>`;
      const facts = [];
      if (Number.isFinite(b.volume)) facts.push(`<span class="fact">${icon("volume")}${b.volume} / ${b.volume_max ?? 13}</span>`);
      const sleep = this._sleep(b.sleep_timer);
      if (sleep) facts.push(`<span class="fact">${icon("sleep")}${esc(sleep)}</span>`);
      let body = facts.length ? `<div class="facts">${facts.join("")}</div>` : "";
      if (live) body += this._playback(b.playback);
      else body += `<div class="muted">${esc(t.classicNote)}</div>`;
      const notes = [];
      if ((!live || b.online !== true) && b.last_seen) notes.push(fill(t.lastSeen, { t: this._relative(b.last_seen) }));
      if (b.firmware) notes.push(`${t.firmware} ${b.firmware}`);
      if (notes.length) body += `<div class="muted small">${esc(notes.join(" · "))}</div>`;
      // The battery hangs under the card as a tile of its own
      const tile = live && b.battery_stats ? this._battery(b) : "";
      return tile ? `<div class="box">${this._card(title, body)}${tile}</div>` : this._card(title, body);
    }

    // The timer counts as set unless its state says otherwise
    _sleep(timer) {
      if (!timer?.state || /^(off|inactive|disabled|stopped|finished|none|idle)$/i.test(timer.state)) return null;
      const until = time(timer.until);
      if (!Number.isFinite(until)) return this._t.sleepOn;
      return fill(this._t.sleepUntil, { t: new Date(until).toLocaleTimeString(this._lang, { hour: "2-digit", minute: "2-digit" }) });
    }

    // The battery tile: the level, how long a charge lasts and, behind a fold, the
    // completed discharges. The numbers are the backend's; here they are only formatted.
    _battery(b) {
      const t = this._t;
      const s = b.battery_stats;
      // Nothing is known while the box is switched off
      let level = "–";
      if (Number.isFinite(b.battery)) {
        const low = b.battery < 20 && !b.charging;
        level = `<span class="batt${low ? " low" : ""}"><i style="height:${Math.max(0, Math.min(100, b.battery))}%"></i></span>` +
          `${b.battery} %${b.charging ? `<span class="charge">${icon("flash")}${esc(t.charging)}</span>` : ""}`;
      }
      const cur = s.current;
      const parts = [];
      if (Number.isFinite(s.average_full_hours)) parts.push(fill(t.perFull, { h: this._num(s.average_full_hours) }));
      else if (Number.isFinite(cur?.per_full)) parts.push(fill(t.perFullProjected, { h: this._num(cur.per_full) }));
      if (s.count > 0) parts.push(fill(s.count === 1 ? t.charge1 : t.chargesN, { n: s.count }));
      if (Number.isFinite(cur?.hours) && Number.isFinite(cur?.from)) parts.push(fill(t.nowSince, { t: hours(cur.hours), p: cur.from }));
      let html = `<div class="tile-head"><span class="tile-title">${esc(t.battery)}</span><span class="fact">${level}</span></div>` +
        `<div class="muted small">${esc(cap(parts.length ? parts.join(" · ") : t.noCycles))}</div>`;
      const cycles = Array.isArray(s.cycles) ? s.cycles : [];
      if (cycles.length) {
        const max = Math.max(...cycles.map((c) => c.per_full).filter(Number.isFinite), 0);
        const key = `batt:${b.id}`;
        const open = this._open.has(key);
        const rows = cycles.map((c) => {
          const width = max > 0 && Number.isFinite(c.per_full) ? ((100 * c.per_full) / max).toFixed(1) : 0;
          const level = Number.isFinite(c.from) && Number.isFinite(c.to) ? `${c.from} % → ${c.to} %` : "–";
          return `<tr><td>${esc(this._date(c.day))}</td><td>${esc(hours(c.hours))}</td><td>${esc(level)}</td>` +
            `<td><div class="pf"><div class="bar"><div style="width:${width}%"></div></div><span>${esc(hours(c.per_full))}</span></div></td></tr>`;
        }).join("");
        html += `<div class="fold${open ? " open" : ""}"><button class="fig-head" data-fold="${esc(key)}" aria-expanded="${open}">` +
          `<span class="headline">${esc(t.history)}</span>${icon("chevron")}</button><div class="detail"><table class="cycles"><thead><tr>` +
          `<th>${esc(t.colDay)}</th><th>${esc(t.colOn)}</th><th>${esc(t.colLevel)}</th><th>${esc(t.colPerFull)}</th></tr></thead>` +
          `<tbody>${rows}</tbody></table></div></div>`;
      }
      return `<div class="tile">${html}</div>`;
    }

    _playback(p) {
      const t = this._t;
      if (!p) return `<div class="play">${this._pic(null)}<div class="text"><span class="headline muted">${esc(t.nothing)}</span></div></div>`;
      const [state, kind, ic] = p.playing ? [t.playing, "ok", "play"] : p.paused ? [t.paused, "warn", "pause"] : [t.placed, "", ""];
      let chapter = "";
      if (p.chapter != null) {
        chapter = `${esc(t.chapter)} ${p.chapter + 1}${Number.isFinite(p.chapters) ? ` / ${p.chapters}` : ""}` +
          (p.chapter_title ? ` · ${esc(p.chapter_title)}` : "");
      } else if (Number.isFinite(p.chapters)) chapter = esc(fill(p.chapters === 1 ? t.chapter1 : t.chaptersN, { n: p.chapters }));
      let html = `<div class="play">${this._pic(p.image_url)}<div class="text"><span class="headline">${esc(p.tonie_name || t.unknownFigure)}</span>` +
        `${chapter ? `<span class="supporting">${chapter}</span>` : ""}` +
        `<span class="supporting state ${kind}">${ic ? icon(ic) : ""}${esc(state)}</span></div></div>`;
      // The bar is filled by _tick(): while playing, the position moves on locally
      if (Number.isFinite(p.duration) && p.duration > 0) {
        const at = time(p.received_at);
        html += `<div class="progress" data-pos="${Number(p.position) || 0}" data-dur="${p.duration}" data-at="${Number.isFinite(at) ? at : ""}"${p.playing ? " data-playing" : ""}>` +
          `<div class="bar"><div></div></div><div class="times"><span class="pos"></span><span>${esc(mmss(p.duration))}</span></div></div>`;
      }
      return html;
    }

    _tick() {
      const now = Date.now();
      for (const el of this.shadowRoot.querySelectorAll(".progress")) {
        const dur = Number(el.dataset.dur);
        const at = Number(el.dataset.at);
        let pos = Number(el.dataset.pos) || 0;
        if (el.hasAttribute("data-playing") && Number.isFinite(at) && at > 0) pos += (now - at) / 1000;
        pos = Math.max(0, Math.min(dur, pos));
        el.querySelector(".bar div").style.width = `${dur ? ((100 * pos) / dur).toFixed(2) : 0}%`;
        el.querySelector(".pos").textContent = mmss(pos);
      }
    }

    // -------------------------------------------------------------- figures

    _figures() {
      const t = this._t;
      const lib = this._library;
      const err = this._errors.library;
      if (!lib) return err ? this._fail(err) : this._loading();
      const kinds = KINDS.map((k) =>
        `<button class="chip pick${this._kind === k ? " on" : ""}" data-kind="${k}">${esc(t[`kind_${k}`])}</button>`).join("");
      return (err ? this._fail(err) : "") +
        `<div class="filters"><label class="search">${icon("search")}<input id="search" type="search" placeholder="${esc(t.search)}" value="${esc(this._query)}" autocomplete="off"></label>` +
        `<div class="chips">${kinds}</div></div><div id="figlist">${this._figureList()}</div>`;
    }

    _figureList() {
      const t = this._t;
      const lib = this._library;
      if (!lib.tonies.length) return this._card("", `<div class="muted">${esc(t.noFigures)}</div>`);
      const q = this._query.trim().toLowerCase();
      const hit = (f) => (this._kind === "all" || f.kind === this._kind) &&
        (!q || [f.name, f.series, ...f.chapters.map((c) => c.title)].some((s) => s && String(s).toLowerCase().includes(q)));
      const list = lib.tonies.filter(hit);
      const all = list.length === lib.tonies.length;
      const count = `<div class="muted small count">${esc(all
        ? (list.length === 1 ? t.figure1 : fill(t.figuresAll, { n: list.length }))
        : fill(t.figuresOf, { n: list.length, m: lib.tonies.length }))}</div>`;
      if (!list.length) return count + this._card("", `<div class="muted">${esc(t.noMatch)}</div>`);
      const boxes = new Map((this._overview?.boxes || []).map((b) => [b.id, b.name]));
      const households = new Map(lib.households.length > 1 ? lib.households.map((h) => [h.id, h.name]) : []);
      return count + this._card("", list.map((f) => this._figure(f, boxes, households)).join(""), " list");
    }

    _figure(f, boxes, households) {
      const t = this._t;
      const open = this._open.has(f.id);
      const chapters = f.chapters;
      const sub = [f.series, this._language(f.language), f.kind !== "content" ? t[`kind1_${f.kind}`] : "", households.get(f.household_id)]
        .filter(Boolean).map(esc).join(" · ");
      const meta = [hm(f.seconds), fill(chapters.length === 1 ? t.chapter1 : t.chaptersN, { n: chapters.length })].map(esc).join(" · ");
      const badges =
        (f.on_box ? this._chip(fill(t.onBox, { box: boxes.get(f.on_box) || f.on_box }), "on") : "") +
        (f.transcoding ? this._chip(t.transcoding, "warn") : "") +
        (f.locked ? `<span class="lock" title="${esc(t.locked)}">${icon("lock")}</span>` : "");
      let detail = "";
      if (f.kind === "creative") {
        const free = [fill(t.free, { t: hm(f.seconds_remaining) })];
        if (Number.isFinite(f.chapters_remaining)) free.push(fill(f.chapters_remaining === 1 ? t.chapter1 : t.chaptersN, { n: f.chapters_remaining }));
        detail += `<div class="muted small">${esc(free.join(" · "))}</div>`;
      }
      // Only a creative figure takes chapters; the detail is drawn open when it is edited
      detail += f.kind === "creative" ? this._creativeDetail(f) : this._chapterList(chapters);
      return `<div class="figure${open ? " open" : ""}"><button class="fig-head" data-fold="${esc(f.id)}" aria-expanded="${open}">` +
        `${this._pic(f.image_url)}<div class="text"><span class="headline">${esc(f.name)}</span>` +
        `${sub ? `<span class="supporting">${sub}</span>` : ""}<span class="supporting">${meta}</span></div>` +
        `<span class="badges">${badges}</span>${icon("chevron")}</button><div class="detail">${detail}</div></div>`;
    }

    _chapterList(chapters, editing = false) {
      const t = this._t;
      if (!chapters.length) return `<div class="muted small">${esc(t.noChapters)}</div>`;
      const last = chapters.length - 1;
      return `<ol class="chapters${editing ? " editing" : ""}">${chapters.map((c, i) => {
        const tools = editing
          ? `<span class="ch-tools">` +
            `<button class="icon-button" data-act="up:${i}" title="${esc(t.moveUp)}"${i === 0 ? " disabled" : ""}>${icon("up")}</button>` +
            `<button class="icon-button" data-act="down:${i}" title="${esc(t.moveDown)}"${i === last ? " disabled" : ""}>${icon("down")}</button>` +
            `<button class="icon-button danger" data-act="remove:${i}" title="${esc(t.remove)}">${icon("remove")}</button></span>`
          : "";
        return `<li><span class="no">${i + 1}</span><span class="ch-title">${esc(c.title || `${t.chapter} ${i + 1}`)}</span>` +
          `${c.transcoding ? this._chip(t.transcoding, "warn") : ""}<span class="len">${esc(mmss(c.seconds))}</span>${tools}</li>`;
      }).join("")}</ol>`;
    }

    // The chapters of a creative figure with the tools to upload, rearrange and remove them.
    // Rearranging happens on a copy and goes to the cloud in one go when saved.
    _creativeDetail(f) {
      const t = this._t;
      const edit = this._edit?.id === f.id ? this._edit : null;
      const up = this._uploads[f.id];
      let html = "";
      if (f.transcoding_errors?.length) {
        const reasons = [...new Set(f.transcoding_errors)].map((r) => t[`reason_${r}`] || r).join(", ");
        html += `<div class="alert err inline">${icon("alert")}<span>${esc(fill(t.convErrors, { r: reasons }))}</span></div>`;
      }
      if (edit) {
        const busy = edit.saving;
        html += `<div class="ch-bar">` +
          `<button class="btn primary" data-act="save" ${busy ? "disabled" : ""}>${icon("check")}${esc(t.save)}</button>` +
          `<button class="btn" data-act="cancel" ${busy ? "disabled" : ""}>${icon("close")}${esc(t.cancel)}</button>` +
          `<span class="muted small hint">${esc(t.editHint)}</span></div>`;
        if (edit.error) html += `<div class="alert err inline">${icon("alert")}<span>${esc(fill(t.saveFailed, { e: edit.error }))}</span></div>`;
        return html + this._chapterList(edit.chapters, true);
      }
      const busy = !!up && !up.error;
      const link = !busy && this._link?.id === f.id ? this._link : null;
      // Links need the Media Fetcher app; without it the button stays grey and says so on hover
      const app = this._library?.fetcher !== false;
      const linkBtn = `<button class="btn" data-act="link:${esc(f.id)}" ${busy || link || !app ? "disabled" : ""}>${icon("link")}${esc(t.fromLink)}</button>`;
      html += `<div class="ch-bar">` +
        `<button class="btn" data-act="upload:${esc(f.id)}" ${busy ? "disabled" : ""}>${icon("upload")}${esc(t.upload)}</button>` +
        (app ? linkBtn : `<span class="tip" title="${esc(t.fetcherMissing)}">${linkBtn}</span>`) +
        `<button class="btn" data-act="edit:${esc(f.id)}" ${busy || !f.chapters.length ? "disabled" : ""}>${icon("pencil")}${esc(t.edit)}</button></div>`;
      if (link) {
        html += `<form class="link-form" id="link-form">` +
          `<label class="search">${icon("link")}<input id="link-url" type="url" placeholder="${esc(t.linkPlaceholder)}" value="${esc(link.url)}" autocomplete="off" spellcheck="false" required></label>` +
          `<button class="btn primary" type="submit">${icon("check")}${esc(t.add)}</button>` +
          `<button class="btn" type="button" data-act="linkcancel">${icon("close")}${esc(t.cancel)}</button>` +
          `<span class="muted small hint">${esc(t.linkHint)}</span></form>`;
      }
      if (up) {
        html += up.error
          ? `<div class="alert err inline">${icon("alert")}<span>${esc(fill(up.link ? t.linkFailed : t.uploadFailed, { e: up.error }))}</span>` +
            `<button class="text-button" data-act="dismiss:${esc(f.id)}">${esc(t.dismiss)}</button></div>`
          : `<div class="muted small busy">${esc(this._progressText(up))}</div>`;
      }
      return html + this._chapterList(f.chapters);
    }

    // What a running upload, or a chapter fetched from a link, is doing right now
    _progressText(up) {
      const t = this._t;
      if (!up.link) return fill(t.uploading, { name: up.name, n: up.done + 1, m: up.total });
      if (up.stage === "upload") return fill(t.linkUpload, { name: up.name });
      if (up.stage === "convert") return fill(t.linkConvert, { name: up.name });
      if (up.stage === "download") return fill(up.pct == null ? t.linkFetch : t.linkFetchPct, { name: up.name, p: up.pct });
      return t.linkProbe;
    }

    // Buttons of the figures: "verb:argument"
    _chapterAction(act) {
      const [verb, arg] = act.split(/:(.*)/s);
      const edit = this._edit;
      const tonie = (id) => this._library?.tonies.find((x) => x.id === id);
      switch (verb) {
        case "edit": {
          const f = tonie(arg);
          if (f) this._edit = { id: f.id, chapters: f.chapters.map((c) => ({ ...c })), saving: false, error: null };
          break;
        }
        case "cancel":
          if (edit?.saving) return;
          this._edit = null;
          break;
        case "save":
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
        case "link":
          if (this._uploads[arg] && !this._uploads[arg].error) return;
          delete this._uploads[arg];
          this._link = { id: arg, url: "" };
          this._refreshList();
          this.shadowRoot.getElementById("link-url")?.focus();
          return;
        case "linkcancel":
          this._link = null;
          break;
        case "dismiss":
          delete this._uploads[arg];
          break;
        default:
          return;
      }
      this._refreshList();
    }

    // A figure as the cloud answered it replaces the one in the library
    _replaceTonie(tonie) {
      if (!tonie?.id || !this._library) return;
      const i = this._library.tonies.findIndex((x) => x.id === tonie.id);
      if (i >= 0) this._library.tonies[i] = tonie;
      else this._library.tonies.push(tonie);
    }

    async _saveChapters() {
      const edit = this._edit;
      if (!edit || edit.saving || !this._hass) return;
      edit.saving = true;
      edit.error = null;
      this._refreshList();
      try {
        const tonie = await this._hass.callWS({ type: "storybox_plus/chapters/arrange", tonie_id: edit.id, chapters: edit.chapters.map((c) => c.id) });
        this._replaceTonie(tonie);
        if (this._edit === edit) this._edit = null;
      } catch (err) {
        edit.saving = false;
        edit.error = err?.message || String(err);
      }
      this._refreshList();
    }

    // The files go to Home Assistant first (its own upload endpoint keeps them until
    // taken), then the integration moves each into the cloud and appends the chapter
    async _uploadFiles(id, files) {
      if (!this._hass) return;
      const up = { total: files.length, done: 0, name: files[0].name, error: null };
      this._uploads[id] = up;
      this._refreshList();
      for (const file of files) {
        up.name = file.name;
        this._refreshList();
        try {
          const form = new FormData();
          form.append("file", file);
          const resp = await this._hass.fetchWithAuth("/api/file_upload", { method: "POST", body: form });
          if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
          const { file_id } = await resp.json();
          const title = file.name.replace(/\.[^.]+$/, "");
          const tonie = await this._hass.callWS({ type: "storybox_plus/chapters/add", tonie_id: id, file_id, title });
          this._replaceTonie(tonie);
          up.done += 1;
        } catch (err) {
          up.error = err?.message || String(err);
          break;
        }
      }
      if (!up.error && this._uploads[id] === up) delete this._uploads[id];
      this._refreshList();
    }

    // The link goes to the integration, which fetches the audio through yt-dlp and
    // appends the chapter; it reports the stages as events until done or failed
    async _fetchLink() {
      const link = this._link;
      const url = (link?.url || "").trim();
      if (!link || !url || !this._hass) return;
      const id = link.id;
      const up = { total: 1, done: 0, name: "", error: null, link: true, stage: "probe", pct: null, unsub: null };
      this._uploads[id] = up;
      this._link = null;
      this._refreshList();
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
          } else if (ev.stage === "error") {
            up.error = ev.message || ev.code;
            end();
          } else {
            up.stage = ev.stage;
            if (ev.title) up.name = ev.title;
            up.pct = ev.total ? Math.floor((ev.done / ev.total) * 100) : null;
          }
          this._refreshList();
        }, { type: "storybox_plus/chapters/add_link", tonie_id: id, url }, { resubscribe: false });
      } catch (err) {
        up.error = err?.message || String(err);
        this._refreshList();
      }
    }

    // While the cloud converts a creative figure, it is read again now and then
    async _refreshConverting() {
      if (!this._hass || !this._library || this._busy.has("convert")) return;
      const converting = this._library.tonies.filter((f) => f.kind === "creative" && f.transcoding);
      if (!converting.length) return;
      this._busy.add("convert");
      try {
        for (const f of converting) {
          this._replaceTonie(await this._hass.callWS({ type: "storybox_plus/figure/refresh", tonie_id: f.id }));
        }
      } catch {
        // The next poll of the integration catches up
      }
      this._busy.delete("convert");
      this._refreshList();
    }

    // ------------------------------------------------------------ listening

    _listening() {
      const t = this._t;
      const range = this._range;
      const s = this._stats[range];
      const err = this._errors[`stats:${range}`];
      const chips = RANGES.map(([k]) =>
        `<button class="chip pick${range === k ? " on" : ""}" data-range="${k}">${esc(t[`range_${k}`])}</button>`).join("");
      // Where the numbers come from, and so what they cannot contain: above everything else
      const note = `<div class="alert notice">${icon("info")}<div><div class="notice-title">${esc(t.noteLocalTitle)}</div>${esc(t.noteLocal)}</div></div>`;
      let html = note + `<div class="filters"><div class="chips">${chips}</div></div>`;
      if (!s) return html + (err ? this._fail(err) : this._loading());
      if (err) html += this._fail(err);
      if (!s.enabled) html += this._alert(t.disabled);
      const label = s.days ? fill(t.lastDays, { n: s.days }) : s.first_day ? fill(t.since, { d: this._date(s.first_day, true) }) : t.sinceSetup;
      html += this._card("", `<div class="total"><span class="big">${esc(hm(s.total_seconds))}</span><span class="unit">h</span></div>` +
        `<div class="muted">${esc(t.total)} · ${esc(label)}</div>`);
      if (!s.total_seconds && !s.top.length) return html + this._card("", `<div class="muted">${esc(t.noStats)}</div>`);
      const max = Math.max(...s.top.map((x) => x.seconds), 1);
      if (s.top.length) {
        html += this._card(esc(t.top), `<ol class="top">${s.top.map((x, i) =>
          `<li><span class="rank">${i + 1}</span>${this._pic(x.image_url, " small")}<div class="text"><span class="headline">${esc(x.name || t.unknownFigure)}</span>` +
          `<div class="bar"><div style="width:${((100 * x.seconds) / max).toFixed(1)}%"></div></div></div><span class="len">${esc(hm(x.seconds))}</span></li>`).join("")}</ol>`);
      }
      html += this._dayChart(s);
      if (s.per_box.length) {
        html += this._card(esc(t.perBox), `<table class="kv">${s.per_box.map((b) =>
          `<tr><th>${esc(b.name || b.box_id)}</th><td>${esc(hm(b.seconds))} h</td></tr>`).join("")}</table>`);
      }
      return html;
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
      return this._card(esc(weekly ? t.perWeek : t.perDay), `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img">${grid}${labels}${rects}</svg>`);
    }
  }

  // Home Assistant's look: toolbar and tabs of the settings pages, cards, list
  // items; the colours of the active theme
  const STYLE = `
  /* The page takes the window */
  :host { display: block; height: 100vh; height: 100dvh; background: var(--primary-background-color); color: var(--primary-text-color);
    font-family: var(--ha-font-family-body, Roboto, Noto, sans-serif); font-size: 14px; line-height: 1.5;
    -webkit-font-smoothing: antialiased; }
  * { box-sizing: border-box; }
  .app { display: flex; flex-direction: column; height: 100%; }
  .toolbar { display: flex; align-items: center; flex: none; height: var(--header-height, 56px); padding: 0 12px;
    background: var(--sidebar-background-color); color: var(--sidebar-text-color, var(--primary-text-color));
    border-bottom: 1px solid var(--divider-color); }
  .menu-button { color: var(--sidebar-icon-color, var(--secondary-text-color)); margin-right: 12px; }
  .main-title { font-size: 20px; font-weight: 400; line-height: 32px; margin-left: 12px; white-space: nowrap; }
  .menu-button + .main-title { margin-left: 0; }
  .tabs { display: flex; height: 100%; margin-left: 24px; overflow-x: auto; scrollbar-width: none; }
  .tab { display: flex; align-items: center; justify-content: center; height: 100%; padding: 0 20px; position: relative;
    color: var(--sidebar-text-color, var(--primary-text-color)); text-decoration: none; font-weight: 500; white-space: nowrap; opacity: 0.8; }
  .tab.active { color: var(--primary-color); opacity: 1; }
  .tabs .tab.active::after { content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 2px; background: var(--primary-color); }
  .tools { display: flex; align-items: center; gap: 4px; margin-left: auto; padding-left: 8px; }
  .bottom-tabs { display: flex; flex: none; justify-content: space-around; background: var(--sidebar-background-color);
    border-top: 1px solid var(--divider-color); padding-bottom: env(safe-area-inset-bottom); }
  .bottom-tabs .tab { flex: 1 1 0; flex-direction: column; gap: 2px; height: 56px; padding: 6px 2px 4px; font-size: 11px; min-width: 0; }
  .bottom-tabs .tab span { overflow: hidden; text-overflow: ellipsis; max-width: 100%; }
  .bottom-tabs .tab .mdi { padding: 2px 12px; border-radius: 14px; box-sizing: content-box; }
  .bottom-tabs .tab.active .mdi { background: color-mix(in srgb, var(--primary-color) 15%, transparent); }
  .content { flex: 1 1 auto; min-height: 0; overflow-y: auto; }
  .sheet { max-width: 1040px; margin: 0 auto; padding: 16px; }
  .narrow .sheet { padding: 8px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 0 16px; }
  .narrow .grid { grid-template-columns: 1fr; }
  .card { background: var(--card-background-color); color: var(--primary-text-color);
    border-radius: var(--ha-card-border-radius, 12px); border: var(--ha-card-border-width, 1px) solid var(--ha-card-border-color, var(--divider-color));
    box-shadow: var(--ha-card-box-shadow, none); margin-bottom: 16px; overflow: hidden; }
  .narrow .card { margin-bottom: 8px; }
  .card h2 { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 0; padding: 16px 16px 8px; font-size: 20px; font-weight: 400; line-height: 28px; }
  .card-content { padding: 0 16px 16px; }
  .card:not(:has(h2)) .card-content { padding-top: 16px; }
  .card.list .card-content { padding: 0; }
  /* A box with a battery: the card and, attached under it, the battery tile */
  .box { margin-bottom: 16px; border-radius: var(--ha-card-border-radius, 12px); box-shadow: var(--ha-card-box-shadow, none); }
  .narrow .box { margin-bottom: 8px; }
  .box .card { margin-bottom: 0; border-bottom-left-radius: 0; border-bottom-right-radius: 0; border-bottom-width: 0; box-shadow: none; }
  .tile { padding: 12px 16px 14px; background: color-mix(in srgb, var(--primary-text-color) 4%, var(--card-background-color));
    border: var(--ha-card-border-width, 1px) solid var(--ha-card-border-color, var(--divider-color)); border-top: 1px solid var(--divider-color);
    border-radius: 0 0 var(--ha-card-border-radius, 12px) var(--ha-card-border-radius, 12px); }
  .tile-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 4px; }
  .tile-title { font-weight: 500; }
  .tile .small { margin-top: 0; }
  .icon-button { display: inline-flex; align-items: center; justify-content: center; width: 40px; height: 40px; padding: 0; border: 0;
    border-radius: 50%; background: none; color: inherit; cursor: pointer; }
  .tab:hover, .icon-button:hover, .fig-head:hover { background: color-mix(in srgb, var(--primary-text-color) 6%, transparent); }
  .text-button { border: 0; background: none; color: var(--primary-color); font: inherit; font-weight: 500; cursor: pointer; padding: 0 4px; }
  .mdi { width: 24px; height: 24px; fill: currentColor; display: block; flex: none; }
  .chips { display: inline-flex; gap: 6px; flex-wrap: wrap; align-items: center; }
  .chip { display: inline-flex; align-items: center; padding: 0 8px; border-radius: 10px; font-size: 12px; line-height: 20px; font-weight: 500;
    background: color-mix(in srgb, var(--primary-text-color) 8%, transparent); color: var(--secondary-text-color); white-space: nowrap; }
  .chip.ok { background: color-mix(in srgb, var(--success-color, #43a047) 16%, transparent); color: var(--success-color, #43a047); }
  .chip.err { background: color-mix(in srgb, var(--error-color, #db4437) 16%, transparent); color: var(--error-color, #db4437); }
  .chip.warn { background: color-mix(in srgb, var(--warning-color, #ffa600) 18%, transparent); color: var(--warning-color, #ffa600); }
  .chip.on { background: color-mix(in srgb, var(--primary-color) 16%, transparent); color: var(--primary-color); }
  .chip.pick { border: 0; font: inherit; font-size: 13px; line-height: 32px; padding: 0 14px; border-radius: 16px; cursor: pointer; }
  .chip.pick:hover:not(.on) { background: color-mix(in srgb, var(--primary-text-color) 14%, transparent); }
  .status { display: inline-flex; align-items: center; gap: 6px; margin-left: auto; font-size: 14px; color: var(--secondary-text-color); }
  .dot { width: 10px; height: 10px; border-radius: 50%; flex: none; background: var(--secondary-text-color); opacity: 0.6; }
  .dot.ok { background: var(--success-color, #43a047); opacity: 1; }
  .dot.err { background: var(--error-color, #db4437); opacity: 1; }
  .facts { display: flex; flex-wrap: wrap; gap: 6px 20px; margin-bottom: 12px; }
  .fact { display: inline-flex; align-items: center; gap: 6px; font-variant-numeric: tabular-nums; }
  .fact .mdi { width: 20px; height: 20px; color: var(--secondary-text-color); }
  .charge { display: inline-flex; align-items: center; color: var(--success-color, #43a047); font-size: 12px; }
  .charge .mdi, .state .mdi { width: 16px; height: 16px; color: inherit; }
  .batt { position: relative; width: 11px; height: 18px; border: 1.5px solid var(--secondary-text-color); border-radius: 2px; }
  .batt::before { content: ""; position: absolute; top: -4px; left: 2px; right: 2px; height: 2px; background: var(--secondary-text-color); border-radius: 1px; }
  .batt i { position: absolute; left: 1px; right: 1px; bottom: 1px; background: var(--success-color, #43a047); border-radius: 1px; }
  .batt.low i { background: var(--error-color, #db4437); }
  .play { display: flex; align-items: center; gap: 12px; }
  .pic { position: relative; flex: none; width: 56px; height: 56px; border-radius: 8px; overflow: hidden;
    background: color-mix(in srgb, var(--primary-text-color) 6%, transparent); color: var(--secondary-text-color); }
  .pic .mdi { position: absolute; left: 50%; top: 50%; width: 28px; height: 28px; transform: translate(-50%, -50%); opacity: 0.6; }
  .pic img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; background: var(--card-background-color); }
  .pic img.broken { display: none; }
  .pic.small { width: 40px; height: 40px; border-radius: 6px; }
  .pic.small .mdi { width: 20px; height: 20px; }
  .text { display: flex; flex: 1; flex-direction: column; min-width: 0; }
  .headline { line-height: 20px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .narrow .play .headline, .narrow .fig-head .headline { white-space: normal; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
  .supporting { font-size: 12px; line-height: 16px; color: var(--secondary-text-color); margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .state { display: inline-flex; align-items: center; gap: 4px; }
  .state.ok { color: var(--success-color, #43a047); }
  .state.warn { color: var(--warning-color, #ffa600); }
  .progress { margin-top: 10px; }
  .bar { position: relative; height: 6px; border-radius: 3px; background: color-mix(in srgb, var(--primary-text-color) 10%, transparent); overflow: hidden; }
  .bar div { height: 100%; border-radius: 3px; background: var(--primary-color); transition: width 0.5s linear; }
  .times { display: flex; justify-content: space-between; margin-top: 4px; font-size: 12px; }
  .times, .no, .rank, .len { color: var(--secondary-text-color); font-variant-numeric: tabular-nums; }
  .muted { color: var(--secondary-text-color); }
  .small { font-size: 12px; line-height: 16px; margin-top: 8px; }
  .alert { display: block; padding: 12px 16px; margin-bottom: 16px; border-radius: 8px; line-height: 20px;
    background: color-mix(in srgb, var(--info-color, #039be5) 12%, transparent); }
  .alert.warn { background: color-mix(in srgb, var(--warning-color, #ffa600) 16%, transparent); }
  .alert.err { background: color-mix(in srgb, var(--error-color, #db4437) 14%, transparent); }
  .alert.notice { display: flex; gap: 12px; align-items: flex-start; }
  .alert.notice .mdi { flex: none; width: 24px; height: 24px; fill: var(--info-color, #039be5); }
  .notice-title { font-weight: 500; }
  .filters { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center; margin-bottom: 12px; }
  .search { display: flex; align-items: center; gap: 8px; flex: 1 1 240px; height: 40px; padding: 0 12px; border-radius: 20px;
    background: var(--card-background-color); border: 1px solid var(--divider-color); color: var(--secondary-text-color); }
  .search:focus-within { border-color: var(--primary-color); }
  .search input { flex: 1; min-width: 0; border: 0; outline: 0; background: none; font: inherit; color: var(--primary-text-color); }
  .count { margin: 0 0 8px 4px; }
  .figure + .figure { border-top: 1px solid var(--divider-color); }
  .fig-head { display: flex; align-items: center; gap: 12px; width: 100%; padding: 10px 16px; border: 0; background: none; color: inherit;
    font: inherit; text-align: left; cursor: pointer; }
  .badges { display: inline-flex; align-items: center; gap: 6px; flex: none; }
  .narrow .badges { flex-wrap: wrap; justify-content: flex-end; max-width: 40%; }
  .lock { display: inline-flex; color: var(--secondary-text-color); }
  .lock .mdi { width: 18px; height: 18px; }
  .fig-head > .mdi:last-child { color: var(--secondary-text-color); transition: transform 0.2s; }
  .open > .fig-head > .mdi:last-child { transform: rotate(180deg); }
  .detail { display: none; padding: 0 16px 12px 84px; }
  .narrow .detail { padding-left: 16px; }
  .open > .detail { display: block; }
  .detail .small { margin: 0 0 6px; }
  /* The charge history in the battery tile: a fold with a small table and a bar per cycle */
  .fold .fig-head { justify-content: space-between; gap: 8px; width: calc(100% + 8px); margin: 4px -4px 0; padding: 4px; border-radius: 8px; }
  .fold .detail { padding: 2px 0 4px; }
  table.cycles th, table.cycles td { padding: 4px 10px 4px 0; text-align: left; white-space: nowrap; font-variant-numeric: tabular-nums; }
  table.cycles th { font-weight: 400; font-size: 12px; color: var(--secondary-text-color); }
  table.cycles th:last-child, table.cycles td:last-child { width: 100%; padding-right: 0; }
  table.cycles tbody tr + tr td { border-top: 1px solid var(--divider-color); }
  .pf { display: flex; align-items: center; gap: 8px; }
  .pf .bar { flex: 1 1 32px; height: 5px; }
  .pf span { min-width: 44px; text-align: right; color: var(--secondary-text-color); }
  .chapters { list-style: none; margin: 0; padding: 0; }
  .chapters li { display: flex; align-items: center; gap: 10px; padding: 5px 0; line-height: 20px; }
  .chapters li + li { border-top: 1px solid var(--divider-color); }
  .chapters .no { flex: none; min-width: 24px; text-align: right; }
  .ch-title { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .len { flex: none; }
  /* The tools of a creative figure: upload and edit, or save and cancel while editing */
  .ch-bar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 2px 0 8px; }
  .ch-bar .hint, .link-form .hint { flex: 1 1 240px; margin: 0; }
  .link-form { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 2px 0 8px; }
  .link-form .search { height: 36px; border-radius: 18px; }
  .tip { display: inline-flex; }
  .btn { display: inline-flex; align-items: center; gap: 6px; height: 36px; padding: 0 16px 0 12px; border-radius: 18px;
    border: 1px solid var(--divider-color); background: none; color: var(--primary-color); font: inherit; font-weight: 500; cursor: pointer; }
  .btn .mdi { width: 20px; height: 20px; }
  .btn:hover:not(:disabled) { background: color-mix(in srgb, var(--primary-color) 8%, transparent); }
  .btn.primary { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: transparent; }
  .btn.primary:hover:not(:disabled) { background: color-mix(in srgb, var(--primary-color) 88%, #000); }
  .btn:disabled, .icon-button:disabled { opacity: 0.4; cursor: default; }
  .icon-button:disabled:hover { background: none; }
  .chapters.editing li { padding: 2px 0; }
  .ch-tools { display: inline-flex; flex: none; gap: 0; margin-right: -8px; }
  .ch-tools .icon-button { width: 36px; height: 36px; color: var(--secondary-text-color); }
  .ch-tools .icon-button .mdi { width: 20px; height: 20px; }
  .ch-tools .danger:hover:not(:disabled) { color: var(--error-color, #db4437); }
  .alert.inline { display: flex; align-items: center; gap: 8px; padding: 8px 12px; margin: 0 0 8px; font-size: 13px; }
  .alert.inline .mdi { flex: none; width: 20px; height: 20px; }
  .alert.err.inline .mdi { fill: var(--error-color, #db4437); }
  .alert.inline span { flex: 1; }
  .busy { margin: 0 0 8px; }
  .total { display: flex; align-items: baseline; gap: 6px; }
  .total .big { font-size: 44px; line-height: 52px; font-weight: 300; font-variant-numeric: tabular-nums; }
  .total .unit { font-size: 18px; color: var(--secondary-text-color); }
  .top { list-style: none; margin: 0; padding: 0; }
  .top li { display: flex; align-items: center; gap: 12px; padding: 6px 0; }
  .top li + li { border-top: 1px solid var(--divider-color); }
  .rank { flex: none; width: 20px; text-align: right; }
  .top .bar { margin-top: 6px; height: 5px; }
  .top .len { min-width: 44px; text-align: right; }
  table { border-collapse: collapse; width: 100%; }
  table.kv th { text-align: left; font-weight: 400; padding: 8px 16px 8px 0; }
  table.kv td { padding: 8px 0; text-align: right; color: var(--secondary-text-color); font-variant-numeric: tabular-nums; white-space: nowrap; }
  table.kv tr + tr th, table.kv tr + tr td { border-top: 1px solid var(--divider-color); }
  .chart { width: 100%; height: auto; display: block; }
  .chart .grid { stroke: var(--divider-color); stroke-width: 1; vector-effect: non-scaling-stroke; }
  .chart text { fill: var(--secondary-text-color); font-size: 12px; }
  .chart .fill { fill: var(--primary-color); pointer-events: none; }
  .chart .hit { fill: transparent; }
  .chart .hit:hover { fill: color-mix(in srgb, var(--primary-text-color) 6%, transparent); }
  `;

  customElements.define("storybox-plus-panel", StoryboxPlusPanel);
  console.info(`%c STORYBOX-PLUS-PANEL %c ${VERSION} `, "color:#fff;background:#e53935;font-weight:700", "");
}
