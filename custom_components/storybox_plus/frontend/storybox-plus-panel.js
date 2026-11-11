// Storybox Plus panel: the page in the sidebar where administrators see their
// boxes with the live state, the figures of the household with their chapters
// and the listening statistics. Everything comes from the integration over the
// WebSocket API; the page is built from Home Assistant's own elements (top app
// bar, cards, buttons, alerts, switches, forms) and shows the version the
// integration reports at its bottom.
// The boxes are asked again this often while their tab is open (ms)
const REFRESH = 10000;
// A chart with more days than this groups them by week
const WEEKS_FROM = 120;

if (!customElements.get("storybox-plus-panel")) {
  const MDI = {
    boxes: "M12,12A3,3 0 0,0 9,15A3,3 0 0,0 12,18A3,3 0 0,0 15,15A3,3 0 0,0 12,12M12,20A5,5 0 0,1 7,15A5,5 0 0,1 12,10A5,5 0 0,1 17,15A5,5 0 0,1 12,20M12,4A2,2 0 0,1 14,6A2,2 0 0,1 12,8C10.89,8 10,7.1 10,6C10,4.89 10.89,4 12,4M17,2H7C5.89,2 5,2.89 5,4V20A2,2 0 0,0 7,22H17A2,2 0 0,0 19,20V4C19,2.89 18.1,2 17,2Z",
    figures: "M12,3V13.55C11.41,13.21 10.73,13 10,13A4,4 0 0,0 6,17A4,4 0 0,0 10,21A4,4 0 0,0 14,17V7H18V3H12Z",
    listening: "M22,21H2V3H4V19H6V10H10V19H12V6H16V19H18V14H22V21Z",
    cog: "M12,8A4,4 0 0,1 16,12A4,4 0 0,1 12,16A4,4 0 0,1 8,12A4,4 0 0,1 12,8M12,10A2,2 0 0,0 10,12A2,2 0 0,0 12,14A2,2 0 0,0 14,12A2,2 0 0,0 12,10M10,22C9.75,22 9.54,21.82 9.5,21.58L9.13,18.93C8.5,18.68 7.96,18.34 7.44,17.94L4.95,18.95C4.73,19.03 4.46,18.95 4.34,18.73L2.34,15.27C2.21,15.05 2.27,14.78 2.46,14.63L4.57,12.97L4.5,12L4.57,11L2.46,9.37C2.27,9.22 2.21,8.95 2.34,8.73L4.34,5.27C4.46,5.05 4.73,4.96 4.95,5.05L7.44,6.05C7.96,5.66 8.5,5.32 9.13,5.07L9.5,2.42C9.54,2.18 9.75,2 10,2H14C14.25,2 14.46,2.18 14.5,2.42L14.87,5.07C15.5,5.32 16.04,5.66 16.56,6.05L19.05,5.05C19.27,4.96 19.54,5.05 19.66,5.27L21.66,8.73C21.79,8.95 21.73,9.22 21.54,9.37L19.43,11L19.5,12L19.43,13L21.54,14.63C21.73,14.78 21.79,15.05 21.66,15.27L19.66,18.73C19.54,18.95 19.27,19.04 19.05,18.95L16.56,17.95C16.04,18.34 15.5,18.68 14.87,18.93L14.5,21.58C14.46,21.82 14.25,22 14,22H10M11.25,4L10.88,6.61C9.68,6.86 8.62,7.5 7.85,8.39L5.44,7.35L4.69,8.65L6.8,10.2C6.4,11.37 6.4,12.64 6.8,13.8L4.68,15.36L5.43,16.66L7.86,15.62C8.63,16.5 9.68,17.14 10.87,17.38L11.24,20H12.76L13.13,17.39C14.32,17.14 15.37,16.5 16.14,15.62L18.57,16.66L19.32,15.36L17.2,13.81C17.6,12.64 17.6,11.37 17.2,10.2L19.31,8.65L18.56,7.35L16.15,8.39C15.38,7.5 14.32,6.86 13.12,6.62L12.75,4H11.25Z",
    refresh: "M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z",
    lock: "M12,17A2,2 0 0,0 14,15C14,13.89 13.1,13 12,13A2,2 0 0,0 10,15A2,2 0 0,0 12,17M18,8A2,2 0 0,1 20,10V20A2,2 0 0,1 18,22H6A2,2 0 0,1 4,20V10C4,8.89 4.9,8 6,8H7V6A5,5 0 0,1 12,1A5,5 0 0,1 17,6V8H18M12,3A3,3 0 0,0 9,6V8H15V6A3,3 0 0,0 12,3Z",
    chevron: "M7.41,8.58L12,13.17L16.59,8.58L18,10L12,15.41L6,9.41L7.41,8.58Z",
    play: "M8,5.14V19.14L19,12.14L8,5.14Z",
    pause: "M14,19H18V5H14M6,19H10V5H6V19Z",
    flash: "M7,2V13H10V22L17,10H13L17,2H7Z",
    volume: "M5,9V15H9L14,20V4L9,9M18.5,12C18.5,10.23 17.5,8.71 16,7.97V16C17.5,15.29 18.5,13.76 18.5,12Z",
    sleep: "M23,12H17V10L20.39,6H17V4H23V6L19.62,10H23V12M15,16H9V14L12.39,10H9V8H15V10L11.62,14H15V16M7,20H1V18L4.39,14H1V12H7V14L3.62,18H7V20Z",
    pencil: "M20.71,7.04C21.1,6.65 21.1,6 20.71,5.63L18.37,3.29C18,2.9 17.35,2.9 16.96,3.29L15.12,5.12L18.87,8.87M3,17.25V21H6.75L17.81,9.93L14.06,6.18L3,17.25Z",
    check: "M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z",
    close: "M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z",
    upload: "M9,16V10H5L12,3L19,10H15V16H9M5,20V18H19V20H5Z",
    up: "M13,20H11V8L5.5,13.5L4.08,12.08L12,4.16L19.92,12.08L18.5,13.5L13,8V20Z",
    down: "M11,4H13V16L18.5,10.5L19.92,11.92L12,19.84L4.08,11.92L5.5,10.5L11,16V4Z",
    remove: "M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z",
    star: "M12,17.27L18.18,21L16.54,13.97L22,9.24L14.81,8.62L12,2L9.19,8.62L2,9.24L7.45,13.97L5.82,21L12,17.27Z",
    starOff: "M12,15.39L8.24,17.66L9.23,13.38L5.91,10.5L10.29,10.13L12,6.09L13.71,10.13L18.09,10.5L14.77,13.38L15.76,17.66M22,9.24L14.81,8.63L12,2L9.19,8.63L2,9.24L7.45,13.97L5.82,21L12,17.27L18.18,21L16.54,13.97L22,9.24Z",
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
      refresh: "Refresh", settings: "Settings", asOf: "As of {t}", retry: "Try again", loading: "Loading …",
      about: "Storybox Plus {version}", aboutCommit: "Storybox Plus {version} · commit {commit}",
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
      chapter: "Chapter", unknownFigure: "Unknown figure", search: "Search figures and chapters",
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
      favChip: "{n} favourites", favToggle: "Favourite chapter", favSwitch: "Steer the Toniebox 2 by the favourites",
      favHint: "The Toniebox 2 skips every other chapter and pauses after the last favourite; play pressed then lets the figure play on until it is taken off. The start of a skipped chapter can be heard for a moment.",
      favFailed: "Saving the favourites failed: {e}",
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
      refresh: "Aktualisieren", settings: "Einstellungen", asOf: "Stand {t}", retry: "Erneut versuchen", loading: "Lädt …",
      about: "Storybox Plus {version}", aboutCommit: "Storybox Plus {version} · Commit {commit}",
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
      chapter: "Kapitel", unknownFigure: "Unbekannte Figur", search: "Figuren und Kapitel suchen",
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
      favChip: "{n} Lieblingskapitel", favToggle: "Lieblingskapitel", favSwitch: "Toniebox 2 nach den Lieblingskapiteln steuern",
      favHint: "Die Toniebox 2 überspringt alle anderen Kapitel und hält nach dem letzten Lieblingskapitel an; wird dann Play gedrückt, spielt die Figur weiter, bis sie abgenommen wird. Der Anfang eines übersprungenen Kapitels kann kurz zu hören sein.",
      favFailed: "Lieblingskapitel speichern fehlgeschlagen: {e}",
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
  const icon = (name) => `<ha-svg-icon path="${MDI[name]}"></ha-svg-icon>`;
  const iconButton = (name, label, attrs = "") =>
    `<ha-icon-button path="${MDI[name]}" label="${esc(label)}"${attrs ? ` ${attrs}` : ""}></ha-icon-button>`;
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
      // When each kind of data last came from the integration, for the stamp in the header
      this._stamps = {};
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
      // A refused change of favourites: { id, message }
      this._favError = null;
      this._uploadTarget = null;
      this._bindOnce();
    }

    set hass(hass) {
      const first = !this._hass;
      this._hass = hass;
      if (first) {
        this._ensure();
        this._syncTimers();
        this._render();
        this._loadBrand();
      }
      for (const el of this.shadowRoot.querySelectorAll("ha-menu-button, ha-form")) el.hass = hass;
    }

    // The integration's icon from its brand folder, as Home Assistant serves it to
    // the frontend: an image link needs the brands access token
    async _loadBrand() {
      try {
        const { token } = await this._hass.callWS({ type: "brands/access_token" });
        this._brandSrc = `/api/brands/integration/storybox_plus/icon.png?token=${encodeURIComponent(token)}`;
        const img = this.shadowRoot.getElementById("brand");
        if (img) img.src = this._brandSrc;
      } catch {
        // Without the icon the name still says which page this is
      }
    }

    set narrow(narrow) {
      if (this._narrow === narrow) return;
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

    // Loads what the open tab shows; every tab needs the overview once, for the
    // version at the bottom and, on the figures, the boxes' names
    _ensure() {
      if (!this._hass || document.visibilityState === "hidden") return;
      if (this._tab === "boxes") this._loadOverview();
      else {
        if (this._tab === "figures") this._loadLibrary();
        else this._loadStats(this._range);
        if (!this._overview) this._loadOverview();
      }
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
      this._header();
      try {
        keep(await this._hass.callWS(msg));
        this._stamps[key] = new Date();
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

    // The data the open tab shows, by the key of _fetch: the stamp and the spinning
    // refresh button in the header are about these
    get _dataKey() {
      if (this._tab === "figures") return "library";
      if (this._tab === "listening") return `stats:${this._range}`;
      return "overview";
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
        const range = el.closest?.("[data-range]");
        if (range) {
          this._range = range.dataset.range;
          this._render();
          this._loadStats(this._range);
          return;
        }
        const kind = el.closest?.("[data-kind]");
        if (kind) {
          this._kind = kind.dataset.kind;
          for (const c of root.querySelectorAll("[data-kind]")) {
            c.classList.toggle("on", c.dataset.kind === this._kind);
            c.setAttribute("aria-pressed", String(c.dataset.kind === this._kind));
          }
          this._refreshList();
          return;
        }
        // A fold (a figure's chapters, a box's charge history) opens and closes on its head
        const head = el.closest?.("[data-fold]");
        if (head && !el.closest?.("[data-act]")) {
          const id = head.dataset.fold;
          const open = !this._open.has(id);
          if (open) this._open.add(id); else this._open.delete(id);
          head.parentElement.classList.toggle("open", open);
          head.setAttribute("aria-expanded", String(open));
          this._sheetHtml = this._content();
          return;
        }
        const target = el.closest?.("[data-act]");
        // A switch tells its new state with "change"
        if (!target || target.tagName === "HA-SWITCH" || target.hasAttribute("disabled")) return;
        const act = target.dataset.act;
        if (act === "refresh" || act === "retry") this._ensure();
        else if (act === "settings") this._settings();
        else this._chapterAction(act);
      });
      // The fold heads are rows, as in Home Assistant's lists: Enter and Space open them
      root.addEventListener("keydown", (e) => {
        // Enter in the link field adds the link, as the button does
        if (e.key === "Enter" && e.target.closest?.('ha-form[data-form="link"]')) {
          e.preventDefault();
          this._fetchLink();
          return;
        }
        const head = e.target.closest?.("[data-fold]");
        if (!head || e.target !== head || (e.key !== "Enter" && e.key !== " ")) return;
        e.preventDefault();
        head.click();
      });
      root.addEventListener("change", (e) => {
        const sw = e.target.closest?.("ha-switch[data-act]");
        if (sw) this._chapterAction(sw.dataset.act);
      });
      // The search and the link are forms of Home Assistant; they tell their value
      root.addEventListener("value-changed", (e) => {
        const form = e.target.closest?.("ha-form[data-form]");
        if (!form) return;
        const value = e.detail?.value || {};
        if (form.dataset.form === "link" && this._link) this._link.url = value.url || "";
        if (form.dataset.form !== "search") return;
        this._query = value.query || "";
        this._refreshList();
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

    // Home Assistant's page of the integration, opened inside the app as its own links do
    _settings() {
      window.history.pushState(null, "", "/config/integrations/integration/storybox_plus");
      window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } }));
    }

    // The stamp says when the open tab's data came; the refresh button spins while they load
    _header() {
      const root = this.shadowRoot;
      const stamp = root.getElementById("stamp");
      if (!stamp) return;
      const at = this._stamps[this._dataKey];
      stamp.textContent = at
        ? fill(this._t.asOf, { t: at.toLocaleTimeString(this._lang, { hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23" }) })
        : "";
      root.getElementById("refresh")?.classList.toggle("spin", this._busy.has(this._dataKey));
    }

    // Only the list under the filters is redrawn, so the search field keeps its focus
    _refreshList() {
      const list = this.shadowRoot.getElementById("figlist");
      if (!list) return this._render();
      list.innerHTML = this._figureList();
      this._hydrate(list);
      this._sheetHtml = this._content();
    }

    _render() {
      if (!this._hass) return;
      const key = [this._tab, !!this._narrow, this._lang].join("|");
      if (key !== this._frameKey) {
        this._frameKey = key;
        this._frame();
      }
      const sheet = this.shadowRoot.getElementById("sheet");
      const html = this._content();
      if (sheet && html !== this._sheetHtml) {
        this._sheetHtml = html;
        sheet.innerHTML = html;
        this._hydrate(sheet);
        this._tick();
      }
      this._header();
    }

    // Home Assistant's forms take their schema, data and labels as properties
    _hydrate(host) {
      const t = this._t;
      const forms = {
        search: [[{ name: "query", selector: { text: { type: "search" } } }], { query: this._query }, t.search],
        link: [[{ name: "url", required: true, selector: { text: { type: "url" } } }], { url: this._link?.url || "" }, t.linkPlaceholder],
      };
      for (const form of host.querySelectorAll("ha-form[data-form]")) {
        const [schema, data, label] = forms[form.dataset.form];
        form.hass = this._hass;
        form.schema = schema;
        form.data = data;
        form.computeLabel = () => label;
      }
    }

    // The parts that stay while the page is open: one header row with the
    // integration's icon, its name and the tabs right after it (the tabs at the
    // bottom on a phone), as on Home Assistant's own pages
    _frame() {
      const t = this._t;
      const tabs = TABS.map(([id, ic, label]) =>
        `<a class="tab${this._tab === id ? " active" : ""}" data-tab="${id}" href="#${id}">` +
        `${this._narrow ? icon(ic) : ""}<span>${esc(t[label])}</span></a>`).join("");
      this.shadowRoot.innerHTML = `
        <style>${STYLE}</style>
        <ha-top-app-bar-fixed>
          <ha-menu-button slot="navigationIcon"></ha-menu-button>
          <div slot="title" class="head"><img class="brand" id="brand" alt="" width="24" height="24"${this._brandSrc ? ` src="${esc(this._brandSrc)}"` : ""}><span class="name">Storybox Plus</span>${this._narrow ? "" : `<nav class="tabs">${tabs}</nav>`}</div>
          <span class="stamp" id="stamp" slot="actionItems"></span>
          ${iconButton("refresh", t.refresh, 'slot="actionItems" id="refresh" data-act="refresh"')}
          ${iconButton("cog", t.settings, 'slot="actionItems" data-act="settings"')}
          <div class="app${this._narrow ? " narrow" : ""}">
            <div class="content"><div class="sheet" id="sheet"></div></div>
            ${this._narrow ? `<nav class="bottom-tabs">${tabs}</nav>` : ""}
          </div>
        </ha-top-app-bar-fixed>
        <input type="file" id="upload" accept="${AUDIO_TYPES}" multiple hidden>`;
      const menu = this.shadowRoot.querySelector("ha-menu-button");
      menu.hass = this._hass;
      menu.narrow = this._narrow;
      this._sheetHtml = null;
    }

    // The version of the integration, at the bottom of every tab
    _about() {
      const a = this._overview?.about;
      if (!a?.version) return "";
      return `<div class="about">${esc(fill(a.commit ? this._t.aboutCommit : this._t.about, a))}</div>`;
    }

    _content() {
      switch (this._tab) {
        case "figures": return this._figures() + this._about();
        case "listening": return this._listening() + this._about();
        default: return this._boxes() + this._about();
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

    // A card of Home Assistant; the title is HTML (a box's name with its chips and status)
    _card(title, body, extra = "", footer = "") {
      return `<ha-card class="${extra.trim()}">${title ? `<h1 class="card-header">${title}</h1>` : ""}` +
        `<div class="card-content${title ? "" : " bare"}">${body}</div>${footer}</ha-card>`;
    }

    _chip(text, kind = "") {
      return `<span class="chip ${kind}">${esc(text)}</span>`;
    }

    // kind: "info", "warning", "error", "success"
    _alert(text, kind = "info", title = "", action = "") {
      return `<ha-alert alert-type="${kind}"${title ? ` title="${esc(title)}"` : ""}>${esc(text)}${action}</ha-alert>`;
    }

    _fail(message) {
      return this._alert(`${this._t.failed}: ${message}`, "error", "",
        `<ha-button slot="action" appearance="plain" data-act="retry">${esc(this._t.retry)}</ha-button>`);
    }

    // look: "plain" (the default), "filled" (the main action of a group)
    _btn(act, label, ic, { look = "plain", disabled = false, attrs = "" } = {}) {
      return `<ha-button${look === "filled" ? "" : ' appearance="plain"'} data-act="${esc(act)}"${disabled ? " disabled" : ""}${attrs ? ` ${attrs}` : ""}>` +
        `${ic ? `<ha-svg-icon slot="start" path="${MDI[ic]}"></ha-svg-icon>` : ""}${esc(label)}</ha-button>`;
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
      if (!o.push_connected && o.boxes.some((b) => b.generation === "toniebox_2")) html += this._alert(t.pushDown, "warning");
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
      // The battery is a section of its own at the bottom of the card
      const tile = live && b.battery_stats ? this._battery(b) : "";
      return this._card(title, body, "", tile);
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
        html += `<div class="fold${open ? " open" : ""}"><div class="fig-head" role="button" tabindex="0" data-fold="${esc(key)}" aria-expanded="${open}">` +
          `<span class="headline">${esc(t.history)}</span>${icon("chevron")}</div><div class="detail"><table class="cycles"><thead><tr>` +
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
        `<button class="chip pick${this._kind === k ? " on" : ""}" data-kind="${k}" aria-pressed="${this._kind === k}">${esc(t[`kind_${k}`])}</button>`).join("");
      return (err ? this._fail(err) : "") +
        `<div class="filters"><ha-form class="search" data-form="search"></ha-form>` +
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
        (f.favourites?.active ? this._chip(fill(t.favChip, { n: f.favourites.chapters.length }), "fav") : "") +
        (f.locked ? `<span class="lock" title="${esc(t.locked)}">${icon("lock")}</span>` : "");
      let detail = "";
      if (f.kind === "creative") {
        const free = [fill(t.free, { t: hm(f.seconds_remaining) })];
        if (Number.isFinite(f.chapters_remaining)) free.push(fill(f.chapters_remaining === 1 ? t.chapter1 : t.chaptersN, { n: f.chapters_remaining }));
        detail += `<div class="muted small">${esc(free.join(" · "))}</div>`;
      }
      // Only a creative figure takes chapters; a bought one takes favourites
      detail += f.kind === "creative" ? this._creativeDetail(f) : this._boughtDetail(f, chapters);
      return `<div class="figure${open ? " open" : ""}"><div class="fig-head" role="button" tabindex="0" data-fold="${esc(f.id)}" aria-expanded="${open}">` +
        `${this._pic(f.image_url)}<div class="text"><span class="headline">${esc(f.name)}</span>` +
        `${sub ? `<span class="supporting">${sub}</span>` : ""}<span class="supporting">${meta}</span></div>` +
        `<span class="badges">${badges}</span>${icon("chevron")}</div><div class="detail">${detail}</div></div>`;
    }

    // With `fav` ({ id, set }) every chapter gets a star that marks it as a favourite
    _chapterList(chapters, editing = false, fav = null) {
      const t = this._t;
      if (!chapters.length) return `<div class="muted small">${esc(t.noChapters)}</div>`;
      const last = chapters.length - 1;
      return `<ol class="chapters${editing ? " editing" : ""}">${chapters.map((c, i) => {
        const on = !!fav && fav.set.has(i);
        const tools = editing
          ? `<span class="ch-tools">` +
            iconButton("up", t.moveUp, `data-act="up:${i}"${i === 0 ? " disabled" : ""}`) +
            iconButton("down", t.moveDown, `data-act="down:${i}"${i === last ? " disabled" : ""}`) +
            iconButton("remove", t.remove, `class="danger" data-act="remove:${i}"`) + `</span>`
          : fav
            ? iconButton(on ? "star" : "starOff", t.favToggle, `class="star${on ? " on" : ""}" data-act="fav:${esc(fav.id)}:${i}" aria-pressed="${on}"`)
            : "";
        return `<li><span class="no">${i + 1}</span><span class="ch-title">${esc(c.title || `${t.chapter} ${i + 1}`)}</span>` +
          `${c.transcoding ? this._chip(t.transcoding, "warn") : ""}<span class="len">${esc(mmss(c.seconds))}</span>${tools}</li>`;
      }).join("")}</ol>`;
    }

    // The chapters of a bought figure with their favourite stars; with favourites set,
    // a switch says whether the box is steered by them
    _boughtDetail(f, chapters) {
      const t = this._t;
      const fav = f.favourites;
      let html = "";
      if (fav) {
        html += `<div class="switch-row"><ha-switch data-act="favon:${esc(f.id)}"${fav.active ? " checked" : ""} aria-label="${esc(t.favSwitch)}"></ha-switch>` +
          `<div class="text"><span>${esc(t.favSwitch)}</span><span class="supporting wrap">${esc(t.favHint)}</span></div></div>`;
      }
      if (this._favError?.id === f.id) {
        html += this._alert(fill(t.favFailed, { e: this._favError.message }), "error", "",
          `<ha-button slot="action" appearance="plain" data-act="favdismiss:${esc(f.id)}">${esc(t.dismiss)}</ha-button>`);
      }
      return html + this._chapterList(chapters, false, { id: f.id, set: new Set(fav?.chapters || []) });
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
        html += this._alert(fill(t.convErrors, { r: reasons }), "error");
      }
      if (edit) {
        const busy = edit.saving;
        html += `<div class="ch-bar">` +
          this._btn("save", t.save, "check", { look: "filled", disabled: busy }) +
          this._btn("cancel", t.cancel, "close", { disabled: busy }) +
          `<span class="muted small hint">${esc(t.editHint)}</span></div>`;
        if (edit.error) html += this._alert(fill(t.saveFailed, { e: edit.error }), "error");
        return html + this._chapterList(edit.chapters, true);
      }
      const busy = !!up && !up.error;
      const link = !busy && this._link?.id === f.id ? this._link : null;
      // Links need the Media Fetcher app; without it the button stays grey and says so on hover
      const app = this._library?.fetcher !== false;
      const linkBtn = this._btn(`link:${f.id}`, t.fromLink, "link", { disabled: busy || !!link || !app });
      html += `<div class="ch-bar">` +
        this._btn(`upload:${f.id}`, t.upload, "upload", { disabled: busy }) +
        (app ? linkBtn : `<span class="tip" title="${esc(t.fetcherMissing)}">${linkBtn}</span>`) +
        this._btn(`edit:${f.id}`, t.edit, "pencil", { disabled: busy || !f.chapters.length }) + `</div>`;
      if (link) {
        html += `<div class="link-form"><ha-form data-form="link"></ha-form>` +
          `<div class="ch-bar">${this._btn("linkadd", t.add, "check", { look: "filled" })}${this._btn("linkcancel", t.cancel, "close")}` +
          `<span class="muted small hint">${esc(t.linkHint)}</span></div></div>`;
      }
      if (up) {
        html += up.error
          ? this._alert(fill(up.link ? t.linkFailed : t.uploadFailed, { e: up.error }), "error", "",
            `<ha-button slot="action" appearance="plain" data-act="dismiss:${esc(f.id)}">${esc(t.dismiss)}</ha-button>`)
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
          this.shadowRoot.querySelector('ha-form[data-form="link"]')?.focus();
          return;
        case "linkadd":
          this._fetchLink();
          return;
        case "linkcancel":
          this._link = null;
          break;
        case "fav": {
          const [id, index] = arg.split(/:(\d+)$/);
          const f = tonie(id);
          if (!f) return;
          const set = new Set(f.favourites?.chapters || []);
          const i = Number(index);
          if (set.has(i)) set.delete(i); else set.add(i);
          // The first star switches the favourites on; later stars keep the switch as it is
          this._setFavourites(id, [...set], f.favourites ? f.favourites.active : true);
          return;
        }
        case "favon": {
          const f = tonie(arg);
          if (!f?.favourites) return;
          this._setFavourites(arg, f.favourites.chapters, !f.favourites.active);
          return;
        }
        case "favdismiss":
          this._favError = null;
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

    // The favourites of a bought figure go to the integration at once; the answer is kept
    async _setFavourites(id, chapters, active) {
      if (!this._hass) return;
      const f = this._library?.tonies.find((x) => x.id === id);
      if (!f) return;
      this._favError = null;
      try {
        const answer = await this._hass.callWS({ type: "storybox_plus/favourites/set", tonie_id: id, chapters, active });
        f.favourites = answer.favourites;
      } catch (err) {
        this._favError = { id, message: err?.message || String(err) };
      }
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
        `<button class="chip pick${range === k ? " on" : ""}" data-range="${k}" aria-pressed="${range === k}">${esc(t[`range_${k}`])}</button>`).join("");
      // Where the numbers come from, and so what they cannot contain: above everything else
      const note = this._alert(t.noteLocal, "info", t.noteLocalTitle);
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

  // The page is built from Home Assistant's elements; this sheet lays them out and
  // draws what Home Assistant has no element for (tabs, chips, lists, charts),
  // in the colours and sizes of the active theme
  const STYLE = `
  /* The panel's own container has no height of its own: the page takes the window */
  :host { display: block; height: 100vh; height: 100dvh; background: var(--primary-background-color); color: var(--primary-text-color);
    font-family: var(--ha-font-family-body, Roboto, Noto, sans-serif); font-size: var(--ha-font-size-m, 14px); line-height: 1.5;
    -webkit-font-smoothing: antialiased; }
  * { box-sizing: border-box; }
  /* Like the settings and other panels: the header in the sidebar's colour, with a line */
  ha-top-app-bar-fixed { height: 100%;
    --app-header-background-color: var(--sidebar-background-color, var(--card-background-color));
    --app-header-text-color: var(--sidebar-text-color, var(--primary-text-color));
    --app-header-border-bottom: 1px solid var(--divider-color); }
  /* One header row: icon, name, tabs; the tabs fill the bar's height for their line */
  .head { display: flex; align-items: center; height: var(--header-height, 56px); min-width: 0; }
  .brand { width: 24px; height: 24px; flex: none; margin-inline-end: 12px; object-fit: contain; }
  .name { flex: none; white-space: nowrap; }
  .app { display: flex; flex-direction: column;
    height: calc(100vh - var(--header-height, 56px) - var(--safe-area-inset-top, 0px));
    height: calc(100dvh - var(--header-height, 56px) - var(--safe-area-inset-top, 0px)); }
  .tabs { display: flex; flex: 0 1 auto; min-width: 0; height: 100%; margin-inline-start: 24px; overflow-x: auto; scrollbar-width: none;
    font-size: var(--ha-font-size-m, 14px); line-height: 1.5; }
  .tab { display: flex; align-items: center; justify-content: center; height: 100%; padding: 0 20px; position: relative;
    color: var(--sidebar-text-color, var(--primary-text-color)); text-decoration: none; font-weight: var(--ha-font-weight-medium, 500);
    white-space: nowrap; opacity: 0.8; }
  .tab:hover { background: color-mix(in srgb, var(--primary-text-color) 5%, transparent); }
  .tab.active { color: var(--primary-color); opacity: 1; }
  .tabs .tab.active::after { content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 2px; background: var(--primary-color); }
  .bottom-tabs { display: flex; flex: none; justify-content: space-around; background: var(--sidebar-background-color, var(--card-background-color));
    border-top: 1px solid var(--divider-color); padding-bottom: env(safe-area-inset-bottom); }
  .bottom-tabs .tab { flex: 1 1 0; flex-direction: column; gap: 2px; height: 56px; padding: 6px 2px 4px;
    font-size: var(--ha-font-size-xs, 11px); min-width: 0; }
  .bottom-tabs .tab span { overflow: hidden; text-overflow: ellipsis; max-width: 100%; }
  .bottom-tabs .tab ha-svg-icon { padding: 2px 12px; border-radius: 14px; box-sizing: content-box; }
  .bottom-tabs .tab.active ha-svg-icon { background: color-mix(in srgb, var(--primary-color) 15%, transparent); }
  .content { flex: 1 1 auto; min-height: 0; overflow-y: auto; }
  .sheet { max-width: 1040px; margin: 0 auto; padding: 16px; }
  .narrow .sheet { padding: 8px; }
  .about { text-align: center; color: var(--secondary-text-color); font-size: var(--ha-font-size-s, 12px); padding: 8px 0 24px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 0 16px; align-items: start; }
  .narrow .grid { grid-template-columns: 1fr; }
  ha-card { display: block; margin-bottom: 16px; overflow: hidden; }
  .narrow ha-card { margin-bottom: 8px; }
  ha-card .card-header { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 0; }
  .card-content { padding: 0 16px 16px; }
  .card-content.bare { padding-top: 16px; }
  ha-card.list .card-content { padding: 0; }
  ha-alert { display: block; margin-bottom: 16px; }
  ha-card ha-alert { margin: 0 0 8px; }
  ha-alert ha-button { margin-inline-start: 8px; }
  /* The battery: a section of its own at the bottom of a box's card */
  .tile { padding: 12px 16px 14px; border-top: 1px solid var(--divider-color);
    background: color-mix(in srgb, var(--primary-text-color) 4%, var(--card-background-color)); }
  .tile-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 4px; }
  .tile-title { font-weight: var(--ha-font-weight-medium, 500); }
  .tile .small { margin-top: 0; }
  ha-svg-icon { flex: none; }
  .chips { display: inline-flex; gap: 6px; flex-wrap: wrap; align-items: center; }
  .chip { display: inline-flex; align-items: center; padding: 0 8px; border-radius: 10px; font-size: var(--ha-font-size-xs, 12px);
    line-height: 20px; font-weight: var(--ha-font-weight-medium, 500);
    background: color-mix(in srgb, var(--primary-text-color) 8%, transparent); color: var(--secondary-text-color); white-space: nowrap; }
  .chip.ok { background: color-mix(in srgb, var(--success-color) 16%, transparent); color: var(--success-color); }
  .chip.err { background: color-mix(in srgb, var(--error-color) 16%, transparent); color: var(--error-color); }
  .chip.warn { background: color-mix(in srgb, var(--warning-color) 18%, transparent); color: var(--warning-color); }
  .chip.on { background: color-mix(in srgb, var(--primary-color) 16%, transparent); color: var(--primary-color); }
  .chip.pick { border: 0; font: inherit; font-size: var(--ha-font-size-s, 13px); line-height: 32px; padding: 0 14px; border-radius: 16px; cursor: pointer; }
  .chip.pick:hover:not(.on) { background: color-mix(in srgb, var(--primary-text-color) 14%, transparent); }
  .status { display: inline-flex; align-items: center; gap: 6px; margin-left: auto; font-size: var(--ha-font-size-m, 14px);
    color: var(--secondary-text-color); font-weight: var(--ha-font-weight-normal, 400); }
  .dot { width: 10px; height: 10px; border-radius: 50%; flex: none; background: var(--secondary-text-color); opacity: 0.6; }
  .dot.ok { background: var(--success-color); opacity: 1; }
  .dot.err { background: var(--error-color); opacity: 1; }
  .facts { display: flex; flex-wrap: wrap; gap: 6px 20px; margin-bottom: 12px; }
  .fact { display: inline-flex; align-items: center; gap: 6px; font-variant-numeric: tabular-nums; }
  .fact ha-svg-icon { --mdc-icon-size: 20px; color: var(--secondary-text-color); }
  .charge { display: inline-flex; align-items: center; color: var(--success-color); font-size: var(--ha-font-size-xs, 12px); }
  .charge ha-svg-icon, .state ha-svg-icon { --mdc-icon-size: 16px; color: inherit; }
  .batt { position: relative; width: 11px; height: 18px; border: 1.5px solid var(--secondary-text-color); border-radius: 2px; }
  .batt::before { content: ""; position: absolute; top: -4px; left: 2px; right: 2px; height: 2px; background: var(--secondary-text-color); border-radius: 1px; }
  .batt i { position: absolute; left: 1px; right: 1px; bottom: 1px; background: var(--success-color); border-radius: 1px; }
  .batt.low i { background: var(--error-color); }
  .play { display: flex; align-items: center; gap: 12px; }
  .pic { position: relative; flex: none; width: 56px; height: 56px; border-radius: 8px; overflow: hidden;
    background: color-mix(in srgb, var(--primary-text-color) 6%, transparent); color: var(--secondary-text-color); }
  .pic ha-svg-icon { position: absolute; left: 50%; top: 50%; --mdc-icon-size: 28px; transform: translate(-50%, -50%); opacity: 0.6; }
  .pic img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; background: var(--card-background-color); }
  .pic img.broken { display: none; }
  .pic.small { width: 40px; height: 40px; border-radius: 6px; }
  .pic.small ha-svg-icon { --mdc-icon-size: 20px; }
  .text { display: flex; flex: 1; flex-direction: column; min-width: 0; }
  .headline { line-height: 20px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .narrow .play .headline, .narrow .fig-head .headline { white-space: normal; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
  .supporting { font-size: var(--ha-font-size-xs, 12px); line-height: 16px; color: var(--secondary-text-color); margin-top: 2px;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .supporting.wrap { white-space: normal; }
  .state { display: inline-flex; align-items: center; gap: 4px; }
  .state.ok { color: var(--success-color); }
  .state.warn { color: var(--warning-color); }
  .progress { margin-top: 10px; }
  .bar { position: relative; height: 6px; border-radius: 3px; background: color-mix(in srgb, var(--primary-text-color) 10%, transparent); overflow: hidden; }
  .bar div { height: 100%; border-radius: 3px; background: var(--primary-color); transition: width 0.5s linear; }
  .times { display: flex; justify-content: space-between; margin-top: 4px; font-size: var(--ha-font-size-xs, 12px); }
  .times, .no, .rank, .len { color: var(--secondary-text-color); font-variant-numeric: tabular-nums; }
  .muted { color: var(--secondary-text-color); }
  .small { font-size: var(--ha-font-size-xs, 12px); line-height: 16px; margin-top: 8px; }
  .filters { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center; margin-bottom: 12px; }
  .filters ha-form.search { flex: 1 1 260px; min-width: 0; }
  .count { margin: 0 0 8px 4px; }
  .figure + .figure { border-top: 1px solid var(--divider-color); }
  /* A row that opens and closes, like the rows of Home Assistant's lists */
  .fig-head { display: flex; align-items: center; gap: 12px; width: 100%; padding: 10px 16px; cursor: pointer; outline: none; }
  .fig-head:hover, .fig-head:focus-visible { background: color-mix(in srgb, var(--primary-text-color) 5%, transparent); }
  .badges { display: inline-flex; align-items: center; gap: 6px; flex: none; }
  .narrow .badges { flex-wrap: wrap; justify-content: flex-end; max-width: 40%; }
  .lock { display: inline-flex; color: var(--secondary-text-color); }
  .lock ha-svg-icon { --mdc-icon-size: 18px; }
  .fig-head > ha-svg-icon:last-child { color: var(--secondary-text-color); transition: transform 0.2s; }
  .open > .fig-head > ha-svg-icon:last-child { transform: rotate(180deg); }
  .detail { display: none; padding: 0 16px 12px 84px; }
  .narrow .detail { padding-left: 16px; }
  .open > .detail { display: block; }
  .detail .small { margin: 0 0 6px; }
  /* The charge history in the battery section: a fold with a small table and a bar per cycle */
  .fold .fig-head { justify-content: space-between; gap: 8px; width: calc(100% + 8px); margin: 4px -4px 0; padding: 4px; border-radius: 8px; }
  .fold .detail { padding: 2px 0 4px; }
  table { border-collapse: collapse; width: 100%; }
  table.cycles th, table.cycles td { padding: 4px 10px 4px 0; text-align: left; white-space: nowrap; font-variant-numeric: tabular-nums; }
  table.cycles th { font-weight: var(--ha-font-weight-normal, 400); font-size: var(--ha-font-size-xs, 12px); color: var(--secondary-text-color); }
  table.cycles th:last-child, table.cycles td:last-child { width: 100%; padding-right: 0; }
  table.cycles tbody tr + tr td { border-top: 1px solid var(--divider-color); }
  .pf { display: flex; align-items: center; gap: 8px; }
  .pf .bar { flex: 1 1 32px; height: 5px; }
  .pf span { min-width: 44px; text-align: right; color: var(--secondary-text-color); }
  .chapters { list-style: none; margin: 0; padding: 0; }
  .chapters li { display: flex; align-items: center; gap: 10px; padding: 2px 0; min-height: 36px; line-height: 20px; }
  .chapters li + li { border-top: 1px solid var(--divider-color); }
  .chapters .no { flex: none; min-width: 24px; text-align: right; }
  .ch-title { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .len { flex: none; }
  /* The tools of a figure: upload and edit, or save and cancel while editing */
  .ch-bar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 2px 0 8px; }
  .ch-bar .hint { flex: 1 1 240px; margin: 0; }
  .link-form { margin: 2px 0 8px; }
  .link-form ha-form { display: block; margin-bottom: 8px; }
  .switch-row { display: flex; align-items: center; gap: 12px; margin: 2px 0 8px; }
  .switch-row ha-switch { flex: none; }
  ha-icon-button { --mdc-icon-button-size: 36px; --mdc-icon-size: 20px; color: var(--secondary-text-color); flex: none; }
  ha-icon-button.star.on { color: var(--state-active-color, var(--amber-color, #ffc107)); }
  ha-icon-button.danger:hover { color: var(--error-color); }
  ha-icon-button[slot="actionItems"] { --mdc-icon-button-size: 48px; --mdc-icon-size: 24px; color: inherit; }
  /* The header's stamp: when the open tab's data came; no room for it on a phone */
  .stamp { color: var(--secondary-text-color); font-size: var(--ha-font-size-s, 12px); white-space: nowrap;
    font-variant-numeric: tabular-nums; margin-inline-end: 4px; }
  @media (max-width: 600px) { .stamp { display: none; } }
  ha-icon-button.spin { animation: spin 1s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .chip.fav { background: color-mix(in srgb, var(--amber-color, #ffc107) 22%, transparent); color: var(--primary-text-color); }
  .tip { display: inline-flex; }
  .ch-tools { display: inline-flex; flex: none; gap: 0; margin-right: -8px; }
  .busy { margin: 0 0 8px; }
  .total { display: flex; align-items: baseline; gap: 6px; }
  .total .big { font-size: 44px; line-height: 52px; font-weight: 300; font-variant-numeric: tabular-nums; }
  .total .unit { font-size: var(--ha-font-size-l, 18px); color: var(--secondary-text-color); }
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
  `;

  customElements.define("storybox-plus-panel", StoryboxPlusPanel);
}
