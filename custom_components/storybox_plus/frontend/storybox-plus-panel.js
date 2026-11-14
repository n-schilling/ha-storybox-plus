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

// What the page shares with the dashboard card; the version of this script keeps both in step
const {
  MDI, TEXTS, esc, icon, iconButton, fill, time, safeUrl, pad, hm, mmss, hours, cap, dayKey, parseDay, WEEKDAYS, clock, STYLE, BoxView,
} = await import(new URL(`./storybox-plus-common.js${new URL(import.meta.url).search}`, import.meta.url).href);

if (!customElements.get("storybox-plus-panel")) {
  // How often a creative figure is read again while the cloud converts its chapters (ms)
  const CONVERT_REFRESH = 15000;
  // Audio the cloud converts; the list only helps the file picker, the cloud decides
  const AUDIO_TYPES = "audio/*,.mp3,.m4a,.m4b,.aac,.ogg,.oga,.opus,.wav,.flac,.wma";

  // Tab id (also the URL hash), icon, text
  const TABS = [
    ["boxes", "boxes", "tabBoxes"],
    ["figures", "figures", "tabFigures"],
    ["listening", "listening", "tabListening"],
    ["preferences", "tune", "tabPreferences"],
  ];
  const KINDS = ["all", "content", "creative", "disc"];
  // Range chip, days asked from the backend (null: since the setup)
  const RANGES = [["7", 7], ["30", 30], ["365", 365], ["all", null]];

  const tabFromHash = () => {
    const id = (window.location.hash || "").slice(1);
    return TABS.some(([t]) => t === id) ? id : "boxes";
  };

  class StoryboxPlusPanel extends BoxView(HTMLElement) {
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
      // A refused change of favourites, or of a figure's volume: { id, message }
      this._favError = null;
      this._volError = null;
      // The bedtime being edited: { box, id (null: new), data, saving, error, confirm }
      this._sched = null;
      // The settings of a box being edited: { box, data, orig, saving, error }
      this._boxEdit = null;
      // The night mode of a box being edited: { box, data, saving, error }
      this._nightEdit = null;
      this._uploadTarget = null;
      this._bindOnce();
      this._upgrade(["hass", "narrow", "route", "panel"]);
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
      // Escape closes an open overlay wherever the focus is, also outside the page;
      // a field or menu that uses the key itself stops it before it gets here
      this._onKey = (e) => {
        if (e.key !== "Escape" || !this._overlayHtml || e.defaultPrevented) return;
        e.preventDefault();
        this._closeOverlay();
      };
      window.addEventListener("hashchange", this._onHash);
      window.addEventListener("keydown", this._onKey);
      document.addEventListener("visibilitychange", this._onVisible);
      this._syncTimers();
      if (this._hass) this._ensure();
    }

    disconnectedCallback() {
      window.removeEventListener("hashchange", this._onHash);
      window.removeEventListener("keydown", this._onKey);
      document.removeEventListener("visibilitychange", this._onVisible);
      this._syncTimers();
    }

    // Loads what the open tab shows; every tab needs the overview once, for the
    // version at the bottom and, on the figures, the boxes' names
    _ensure() {
      if (!this._hass || document.visibilityState === "hidden") return;
      if (this._tab === "boxes" || this._tab === "preferences") this._loadOverview();
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
        // While a bedtime is edited the form stays as it is
        this._poll = window.setInterval(() => { if (!this._sched && !this._boxEdit && !this._nightEdit) this._loadOverview(); }, REFRESH);
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
        this._errors[key] = this._errText(err);
      }
      this._busy.delete(key);
      this._render();
    }

    _loadOverview() {
      return this._fetch("overview", { type: "storybox_plus/overview" }, (d) => { this._overview = d; this._keepVolume(); });
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
      this._figDialog = null;
      this._boxDialog = null;
      this._battDialog = null;
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
        const heat = el.closest?.("[data-heatbox]");
        if (heat) {
          this._heatBox = heat.dataset.heatbox || null;
          this._render();
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
        else this._act(act);
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
        if (sw) this._act(sw.dataset.act);
      });
      // The search and the link are forms of Home Assistant; they tell their value
      root.addEventListener("value-changed", (e) => {
        const form = e.target.closest?.("ha-form[data-form]");
        if (!form) return;
        const value = e.detail?.value || {};
        if (form.dataset.form === "link" && this._link) this._link.url = value.url || "";
        if (form.dataset.form === "code" && this._code) this._code.token = value.token || "";
        if (form.dataset.form === "speak" && this._speak) {
          this._speak.title = value.title || "";
          this._speak.text = value.text || "";
        }
        if (form.dataset.form === "chname" && this._edit) this._edit.renameTitle = value.title || "";
        if (form.dataset.form === "figname" && this._figDialog) {
          const before = this._figName?.id === this._figDialog ? this._figName : { id: this._figDialog };
          this._figName = { ...before, name: value.name || "" };
          // Only the button follows the typing; the field keeps its focus
          const f = this._library?.tonies.find((x) => x.id === this._figDialog);
          const btn = this.shadowRoot.querySelector(`#overlay ha-button[data-act="figrename:${CSS.escape(this._figDialog)}"]`);
          const name = this._figName.name.trim();
          if (btn) btn.disabled = !name || name === f?.name || !!this._figName.busy;
        }
        if (form.dataset.form.startsWith("voucher:")) {
          const id = form.dataset.form.slice(8);
          ((this._voucher ||= {})[id] ||= {}).code = value.code || "";
          return;
        }
        if (form.dataset.form.startsWith("home:")) {
          (this._homeNames ||= {})[form.dataset.form.slice(5)] = value.name || "";
          return;
        }
        if (form.dataset.form.startsWith("tune:")) {
          (this._tunePick ||= {})[form.dataset.form.slice(5)] = value.tune;
          return;
        }
        if (form.dataset.form.startsWith("vol:")) {
          this._setFigureVolume(form.dataset.form.slice(4), value.level === "box" ? null : Number(value.level));
          return;
        }
        if (form.dataset.form === "schedule" && this._sched) this._sched.data = { ...value };
        if (form.dataset.form === "settings" && this._boxEdit) this._boxEdit.data = { ...value };
        if (form.dataset.form === "night" && this._nightEdit) this._nightEdit.data = { ...value };
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
      this._renderOverlay();
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
      this._renderOverlay();
      this._header();
    }

    // The overlay above the page: the settings of a figure or a box, or a form to add
    // chapters. It is drawn apart from the sheet, so the page under it stays as it is
    _renderOverlay() {
      const host = this.shadowRoot.getElementById("overlay");
      if (!host) return;
      const html = this._overlay();
      if (html === this._overlayHtml) return;
      const opened = !this._overlayHtml && !!html;
      this._overlayHtml = html;
      host.innerHTML = html;
      this._hydrate(host);
      if (opened) host.querySelector(".ov-card")?.focus();
    }

    _overlay() {
      const t = this._t;
      let title = "";
      let sub = "";
      let body = "";
      if (this._tab === "figures" && this._library) {
        const find = (id) => this._library.tonies.find((x) => x.id === id);
        const f = find(this._figDialog) || find(this._tuneDialog) || find(this._link?.id) || find(this._speak?.id) || find(this._code?.id);
        if (f && this._figDialog === f.id) [title, body] = [t.figSettings, this._figureSettings(f)];
        else if (f && this._tuneDialog === f.id) [title, body] = [t.tuneOf, this._tuneRow(f)];
        else if (f && this._link?.id === f.id) [title, body] = [t.fromLink, this._linkBody()];
        else if (f && this._speak?.id === f.id) [title, body] = [t.fromText, this._speakBody()];
        else if (f && this._code?.id === f.id) [title, body] = [t.fromCode, this._codeBody()];
        sub = f?.name || "";
      } else if (this._tab === "boxes" && this._overview && this._battDialog) {
        const b = this._overview.boxes.find((x) => x.id === this._battDialog);
        if (b?.battery_stats) [title, sub, body] = [t.battery, b.name || b.id, this._battery(b)];
      } else if (this._tab === "boxes" && this._overview && this._boxDialog) {
        const b = this._overview.boxes.find((x) => x.id === this._boxDialog);
        if (b) {
          title = t.boxSettingsOf;
          sub = b.name || b.id;
          // The firmware matters seldom; it is noted at the end of the settings
          body = (b.settings ? this._settingsTile(b) : "") + (b.bedtime ? this._bedtime(b) : "") +
            (b.firmware ? `<div class="muted small ov-foot">${esc(`${t.firmware} ${b.firmware}`)}</div>` : "");
        }
      }
      if (!body) return "";
      return `<div class="ov"><div class="ov-back" data-act="dlgclose"></div>` +
        `<div class="ov-card" role="dialog" aria-modal="true" aria-label="${esc(title)}" tabindex="-1">` +
        `<div class="ov-head"><div class="ov-titles"><span class="ov-title">${esc(title)}</span>` +
        (sub ? `<span class="supporting">${esc(sub)}</span>` : "") + `</div>` +
        iconButton("close", t.dlgClose, 'data-act="dlgclose"') + `</div><div class="ov-body">${body}</div></div></div>`;
    }

    // Closing drops what was open in it; a text being spoken or a code being redeemed waits
    _closeOverlay() {
      if (this._speak?.busy || this._code?.busy || this._boxEdit?.saving || this._nightEdit?.saving || this._sched?.saving || this._figName?.busy) return;
      this._figDialog = null;
      this._tuneDialog = null;
      this._figName = null;
      this._boxDialog = null;
      this._battDialog = null;
      this._link = null;
      this._speak = null;
      this._code = null;
      this._boxEdit = null;
      this._nightEdit = null;
      this._sched = null;
      this._render();
    }

    _linkBody() {
      const t = this._t;
      return `<ha-form data-form="link"></ha-form><div class="muted small">${esc(t.linkHint)}</div>` +
        `<div class="ov-actions">${this._btn("linkcancel", t.cancel, "close")}${this._btn("linkadd", t.add, "check", { look: "filled" })}</div>`;
    }

    _speakBody() {
      const t = this._t;
      const sp = this._speak;
      let html = sp.busy
        ? `<div class="muted small busy">${esc(t.textBusy)}</div>`
        : `<ha-form data-form="speak"></ha-form><div class="muted small">${esc(t.textHint)}</div>` +
          `<div class="ov-actions">${this._btn("speakcancel", t.cancel, "close")}${this._btn("speakadd", t.add, "check", { look: "filled" })}</div>`;
      if (sp.error) html += this._alert(fill(t.textFailed, { e: sp.error }), "error");
      return html;
    }

    _codeBody() {
      const t = this._t;
      const c = this._code;
      return `<ha-form data-form="code"></ha-form><div class="muted small">${esc(t.codeHint)}</div>` +
        (c.error ? this._alert(fill(t.codeFailed, { e: c.error }), "error") : "") +
        `<div class="ov-actions">${this._btn("codecancel", t.cancel, "close", { disabled: !!c.busy })}` +
        `${this._btn("codeadd", t.add, "check", { look: "filled", disabled: !!c.busy })}</div>`;
    }

    // What a figure has to set: a creative one its name and live mode, every one its
    // volume; a bought one its lock, a creative one shuffling on swap. The Tune has its own.
    _figureSettings(f) {
      const t = this._t;
      let html = "";
      if (f.kind === "creative") {
        const fn = this._figName?.id === f.id ? this._figName : null;
        const name = String(fn?.name ?? f.name).trim();
        html += `<div class="name-row"><ha-form data-form="figname"></ha-form>` +
          this._btn(`figrename:${f.id}`, t.save, "check", { look: "filled", disabled: !name || name === f.name || !!fn?.busy }) + `</div>`;
        if (fn?.error) html += this._alert(fill(t.renameFailed, { e: fn.error }), "error");
        html += `<div class="switch-row"><ha-switch data-act="figlive:${esc(f.id)}"${f.live ? " checked" : ""}${fn?.busy ? " disabled" : ""} aria-label="${esc(t.c_live)}"></ha-switch>` +
          `<div class="text"><span>${esc(t.c_live)}</span></div></div>`;
      }
      html += this._volumeRow(f);
      if (f.kind === "content" || f.kind === "disc") html += this._lockRow(f);
      if (f.kind === "creative" && f.chapters.length > 1) {
        html += `<div class="switch-row"><ha-switch data-act="swapshuffle:${esc(f.id)}"${f.shuffle_on_swap ? " checked" : ""} aria-label="${esc(t.shuffleSwap)}"></ha-switch>` +
          `<div class="text"><span>${esc(t.shuffleSwap)}</span><span class="supporting wrap">${esc(t.shuffleSwapHint)}</span></div></div>`;
        if (this._shuffleError?.id === f.id) html += this._alert(fill(t.shuffleFailed, { e: this._shuffleError.message }), "error");
      }
      return html;
    }

    // Home Assistant's forms take their schema, data and labels as properties
    _hydrate(host) {
      const t = this._t;
      const forms = {
        search: [[{ name: "query", selector: { text: { type: "search" } } }], { query: this._query }, () => t.search],
        link: [[{ name: "url", required: true, selector: { text: { type: "url" } } }], { url: this._link?.url || "" }, () => t.linkPlaceholder],
        chname: [[{ name: "title", required: true, selector: { text: {} } }], { title: this._edit?.renameTitle ?? "" }, () => t.chapterName],
        speak: [
          [{ name: "title", selector: { text: {} } }, { name: "text", required: true, selector: { text: { multiline: true } } }],
          { title: this._speak?.title || "", text: this._speak?.text || "" },
          (f) => (f.name === "title" ? t.textTitle : t.textBody),
        ],
        code: [[{ name: "token", required: true, selector: { text: {} } }], { token: this._code?.token || "" }, () => t.codePlaceholder],
        figname: [
          [{ name: "name", required: true, selector: { text: {} } }],
          { name: this._figName?.name ?? this._library?.tonies.find((x) => x.id === this._figDialog)?.name ?? "" },
          () => t.c_name,
        ],
        schedule: [this._scheduleSchema(), this._sched?.data || {}, (f) => t[`f_${f.name}`] || f.name],
        settings: [this._settingsSchema(), this._boxEdit?.data || {}, (f) => t[`s_${f.name}`] || f.name],
        night: [this._nightSchema(), this._nightEdit?.data || {}, (f) => t[`n_${f.name}`] || f.name],
      };
      for (const form of host.querySelectorAll("ha-form[data-form^='vol:']")) {
        const f = this._library?.tonies.find((x) => x.id === form.dataset.form.slice(4));
        const options = [{ value: "box", label: t.figVolumeBox }, ...Array.from({ length: 13 }, (_, i) => ({ value: String(i + 1), label: `${i + 1} / 13` }))];
        form.hass = this._hass;
        form.schema = [{ name: "level", required: true, selector: { select: { mode: "dropdown", options } } }];
        form.data = { level: f?.volume ? String(f.volume) : "box" };
        form.computeLabel = () => t.figVolume;
      }
      for (const form of host.querySelectorAll("ha-form[data-form^='voucher:']")) {
        const id = form.dataset.form.slice(8);
        form.hass = this._hass;
        form.schema = [{ name: "code", required: true, selector: { text: {} } }];
        form.data = { code: this._voucher?.[id]?.code || "" };
        form.computeLabel = () => t.voucherCode;
      }
      for (const form of host.querySelectorAll("ha-form[data-form^='home:']")) {
        const id = form.dataset.form.slice(5);
        const home = (this._overview?.entries || []).flatMap((e) => e.households || []).find((h) => h.id === id);
        form.hass = this._hass;
        form.schema = [{ name: "name", required: true, selector: { text: {} } }];
        form.data = { name: this._homeNames?.[id] ?? home?.name ?? "" };
        form.computeLabel = () => t.householdName;
      }
      for (const form of host.querySelectorAll("ha-form[data-form^='tune:']")) {
        const id = form.dataset.form.slice(5);
        const fits = (this._library?.tunes || []).filter((x) => x.suitable.includes(id) && !x.assigned.includes(id));
        const options = fits.map((x) => ({ value: x.id, label: x.remaining != null ? `${x.title} (${fill(t.tuneLeft, { n: x.remaining })})` : x.title }));
        form.hass = this._hass;
        form.schema = [{ name: "tune", required: true, selector: { select: { mode: "dropdown", options } } }];
        form.data = { tune: this._tunePick?.[id] || fits[0]?.id };
        form.computeLabel = () => t.tunePick;
      }
      for (const form of host.querySelectorAll("ha-form[data-form]:not([data-form^='vol:']):not([data-form^='tune:']):not([data-form^='home:']):not([data-form^='voucher:'])")) {
        const [schema, data, label] = forms[form.dataset.form];
        form.hass = this._hass;
        form.schema = schema;
        form.data = data;
        form.computeLabel = label;
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
        <div id="overlay"></div>
        <input type="file" id="upload" accept="${AUDIO_TYPES}" multiple hidden>`;
      const menu = this.shadowRoot.querySelector("ha-menu-button");
      menu.hass = this._hass;
      menu.narrow = this._narrow;
      this._sheetHtml = null;
      this._overlayHtml = null;
    }

    // The settings tab: per account the preferences and the cloud's version
    _preferences() {
      const t = this._t;
      const o = this._overview;
      const err = this._errors.overview;
      if (!o) return err ? this._fail(err) : this._loading();
      let html = err ? this._fail(err) : "";
      const loaded = o.entries.filter((e) => e.loaded && e.preferences);
      if (!o.entries.length) return html + this._alert(t.noEntry);
      if (!loaded.length) return html + this._alert(t.notLoaded);
      if (this._prefError) html += this._alert(fill(t.prefFailed, { e: this._prefError }), "error");
      const row = (act, on, label, hint) =>
        `<div class="switch-row"><ha-switch data-act="${esc(act)}"${on ? " checked" : ""} aria-label="${esc(label)}"></ha-switch>` +
        `<div class="text"><span>${esc(label)}</span><span class="supporting wrap">${esc(hint)}</span></div></div>`;
      for (const e of loaded) {
        const p = e.preferences;
        const c = e.cloud || {};
        // Only the release counts, not the commit behind it
        let cloud = `<div class="muted small">${esc(t.cloudUnknown)}</div>`;
        if (c.version) {
          cloud = `<div class="pref-cloud"><span>${esc(fill(t.cloudVersion, { v: c.version }))}</span>` +
            this._chip(c.matches ? t.cloudTested : fill(t.cloudUntested, { t: c.tested }), c.matches ? "ok" : "warn") + `</div>`;
          if (!c.matches) cloud += this._alert(fill(t.cloudDiffers, { v: c.release, t: c.tested }), "warning");
        }
        const homes = (e.households || []).map((h) =>
          `<div class="household-row"><ha-form data-form="home:${esc(h.id)}"></ha-form>` +
          this._btn(`homesave:${h.id}`, t.save, "check", { disabled: this._homeBusy === h.id }) + `</div>` +
          (this._homeError?.id === h.id ? this._alert(fill(t.householdFailed, { e: this._homeError.message }), "error") : "") +
          this._members(h)).join("");
        const v = this._voucher?.[e.entry_id] || {};
        const voucher = `<div class="household-row"><ha-form data-form="voucher:${esc(e.entry_id)}"></ha-form>` +
          this._btn(`voucher:${e.entry_id}`, t.voucherRedeem, "check", { disabled: !!v.busy }) + `</div>` +
          `<div class="muted small">${esc(t.voucherHint)}</div>` +
          (v.error ? this._alert(fill(t.voucherFailed, { e: v.error }), "error") : "") +
          (v.done != null ? this._alert(v.done ? fill(t.voucherDone, { n: v.done }) : t.voucherNone, "success") : "");
        const body =
          `<div class="pref-head">${esc(t.prefHousehold)}</div>${homes}` +
          `<div class="pref-head">${esc(t.prefVoucher)}</div>${voucher}` +
          `<div class="pref-head">${esc(t.prefListening)}</div>` + row(`panalytics:${e.entry_id}`, p.analytics, t.prefAnalytics, t.prefAnalyticsHint) +
          `<div class="pref-head">${esc(t.prefFigures)}</div>` + row(`pautolock:${e.entry_id}`, p.auto_lock, t.prefAutoLock, t.prefAutoLockHint) +
          `<div class="pref-head">${esc(t.prefNotices)}</div>` + row(`pmarkread:${e.entry_id}`, p.mark_read, t.prefMarkRead, t.prefMarkReadHint) +
          `<div class="pref-head">${esc(t.prefCloud)}</div>` + cloud;
        html += this._card(loaded.length > 1 ? esc(e.title) : "", body);
      }
      return html;
    }

    // Who belongs to a household: shown only, managed in the app
    _members(h) {
      const t = this._t;
      if (!Array.isArray(h.members)) return `<div class="muted small">${esc(t.membersUnknown)}</div>`;
      const order = { owner: 0, full: 1, limited: 2 };
      const list = [...h.members].sort((a, b) => (order[a.role] ?? 3) - (order[b.role] ?? 3) || String(a.name).localeCompare(String(b.name)));
      const rows = list.map((m) => {
        const full = [m.first_name, m.last_name].filter(Boolean).join(" ");
        const title = full || m.name;
        const sub = [full && m.name !== full && m.name !== m.first_name ? m.name : "", m.email && m.email !== title ? m.email : ""].filter(Boolean).join(" · ");
        const initial = String(title || "?").trim().charAt(0).toUpperCase();
        return `<div class="member"><span class="member-avatar${m.role === "owner" ? " owner" : ""}" aria-hidden="true">${esc(initial)}</span>` +
          `<div class="text"><span>${esc(title)}${m.self ? " " + this._chip(t.memberYou, "on") : ""}</span>` +
          (sub ? `<span class="supporting">${esc(sub)}</span>` : "") + `</div>` +
          this._chip(t[`role_${m.role}`] || t.role_unknown, m.role === "owner" ? "ok" : "") + `</div>`;
      }).join("");
      return `<div class="members"><div class="members-head">${esc(t.members)} (${list.length})</div>${rows}` +
        `<div class="muted small">${esc(t.membersHint)}</div></div>`;
    }

    async _redeemVoucher(entryId) {
      const v = ((this._voucher ||= {})[entryId] ||= {});
      const code = String(v.code || "").trim();
      if (!code || v.busy || !this._hass) return;
      v.busy = true;
      v.error = null;
      v.done = null;
      this._render();
      try {
        const answer = await this._hass.callWS({ type: "storybox_plus/voucher/redeem", entry_id: entryId, code });
        v.done = answer.count;
        v.code = "";
        if (this._library) this._library.tunes = answer.tunes;
      } catch (err) {
        v.error = this._errText(err);
      }
      v.busy = false;
      this._render();
    }

    // Piper speaks in Home Assistant; the integration uploads the recording as a chapter
    async _addFromText() {
      const sp = this._speak;
      const text = String(sp?.text || "").trim();
      if (!sp || !text || sp.busy || !this._hass) return;
      sp.busy = true;
      sp.error = null;
      this._refreshList();
      const msg = { type: "storybox_plus/chapters/add_text", tonie_id: sp.id, text };
      if (String(sp.title || "").trim()) msg.title = sp.title.trim();
      try {
        this._replaceTonie(await this._hass.callWS(msg));
        if (this._speak === sp) this._speak = null;
      } catch (err) {
        sp.busy = false;
        sp.error = this._errText(err);
      }
      this._refreshList();
    }

    async _redeemCode() {
      const code = this._code;
      const token = String(code?.token || "").trim();
      if (!code || !token || code.busy || !this._hass) return;
      code.busy = true;
      code.error = null;
      this._refreshList();
      try {
        this._replaceTonie(await this._hass.callWS({ type: "storybox_plus/figure/redeem_token", tonie_id: code.id, token }));
        if (this._code === code) this._code = null;
      } catch (err) {
        code.busy = false;
        code.error = this._errText(err);
      }
      this._refreshList();
    }

    async _renameHousehold(id) {
      const name = String(this._homeNames?.[id] ?? "").trim();
      const entry = (this._overview?.entries || []).find((e) => (e.households || []).some((h) => h.id === id));
      const home = entry?.households.find((h) => h.id === id);
      if (!name || !home || name === home.name || !this._hass || this._homeBusy) return;
      this._homeBusy = id;
      this._homeError = null;
      this._render();
      try {
        const answer = await this._hass.callWS({ type: "storybox_plus/household/rename", household_id: id, name });
        home.name = name;
        entry.title = answer.entry_title;
        delete this._homeNames[id];
      } catch (err) {
        this._homeError = { id, message: this._errText(err) };
      }
      this._homeBusy = null;
      this._render();
    }

    async _setPreference(entryId, key) {
      const entry = this._overview?.entries.find((e) => e.entry_id === entryId);
      if (!entry?.preferences || !this._hass) return;
      this._prefError = null;
      try {
        entry.preferences = await this._hass.callWS({ type: "storybox_plus/preferences/set", entry_id: entryId, [key]: !entry.preferences[key] });
        if (key === "analytics") {
          // The integration sets the account up anew; the counted sums change with it
          this._stats = {};
          window.setTimeout(() => this._loadOverview(), 4000);
        }
      } catch (err) {
        this._prefError = this._errText(err);
      }
      this._render();
    }

    async _setLock(id) {
      const f = this._library?.tonies.find((x) => x.id === id);
      if (!f || !this._hass) return;
      this._lockError = null;
      try {
        f.locked = (await this._hass.callWS({ type: "storybox_plus/figure/lock", tonie_id: id, locked: !f.locked })).locked;
      } catch (err) {
        this._lockError = { id, message: this._errText(err) };
      }
      this._refreshList();
    }

    _tuneOn(id) {
      return (this._library?.tunes || []).find((x) => x.assigned.includes(id)) || null;
    }

    // A bought Tune on the figure, or the Tunes that fit it to lay one on
    _tuneRow(f) {
      const t = this._t;
      const on = this._tuneOn(f.id);
      const fits = (this._library?.tunes || []).filter((x) => x.suitable.includes(f.id) && !x.assigned.includes(f.id));
      if (!on && !fits.length) return "";
      const busy = this._tuneBusy === f.id;
      let html = `<div class="tune-row">`;
      if (on) {
        html += `<span>${esc(fill(t.tuneOn, { t: on.title }))}</span>` + this._btn(`tuneoff:${f.id}`, t.tuneRemove, "close", { disabled: busy });
      } else {
        html += `<ha-form data-form="tune:${esc(f.id)}"></ha-form>` + this._btn(`tuneon:${f.id}`, t.tuneAssign, "check", { disabled: busy });
      }
      html += `<span class="muted small hint">${esc(f.kind === "creative" ? t.tuneHintCreative : t.tuneHint)}</span></div>`;
      if (this._tuneError?.id === f.id) html += this._alert(fill(t.tuneFailed, { e: this._tuneError.message }), "error");
      return html;
    }

    async _setTune(id, tuneId) {
      if (!this._hass || this._tuneBusy) return;
      this._tuneBusy = id;
      this._tuneError = null;
      this._refreshList();
      try {
        const answer = await this._hass.callWS({ type: "storybox_plus/figure/tune", tonie_id: id, tune_id: tuneId });
        this._library.tunes = answer.tunes;
        // A creative figure plays other chapters now; a bought one keeps its own as they were
        if (answer.figure?.kind === "creative") this._replaceTonie(answer.figure);
      } catch (err) {
        this._tuneError = { id, message: this._errText(err) };
      }
      this._tuneBusy = null;
      this._refreshList();
    }

    // The lock of a bought figure or disc
    _lockRow(f) {
      const t = this._t;
      let html = `<div class="switch-row"><ha-switch data-act="lock:${esc(f.id)}"${f.locked ? " checked" : ""} aria-label="${esc(t.lockSwitch)}"></ha-switch>` +
        `<div class="text"><span>${esc(t.lockSwitch)}</span><span class="supporting wrap">${esc(t.lockHint)}</span></div></div>`;
      if (this._lockError?.id === f.id) html += this._alert(fill(t.lockFailed, { e: this._lockError.message }), "error");
      return html;
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
        case "preferences": return this._preferences() + this._about();
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

    _language(code) {
      if (!code) return "";
      const base = String(code).split(/[-_]/)[0];
      try {
        return new Intl.DisplayNames([this._lang], { type: "language" }).of(base) || code;
      } catch {
        return code;
      }
    }

    // A failure as a sentence for the user: known codes get their own text, a lost
    // connection says so; whatever else came keeps its message, never an object
    _errText(err) {
      const t = this._t;
      const e = err && typeof err === "object" && err.error && typeof err.error === "object" ? err.error : err;
      if (e == null) return t.errUnknown;
      if (typeof e === "number" || [1, 2, 3].includes(e.code)) return t.errConnection;
      const code = typeof e === "object" ? e.code : null;
      if (code && t[`err_${code}`]) return t[`err_${code}`];
      const raw = typeof e === "string" ? e : typeof e.message === "string" ? e.message : "";
      if (/connection (lost|closed)|failed to fetch|socket/i.test(raw)) return t.errConnection;
      return raw.trim() || t.errUnknown;
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
      const many = households.size > 1;
      // A Toniebox 1 reports nothing live: it gets a small card of its own, after the Toniebox 2
      const live = o.boxes.filter((b) => b.generation === "toniebox_2");
      const rest = o.boxes.filter((b) => b.generation !== "toniebox_2");
      return html + `<div class="grid">${live.map((b) => this._box(b, many)).join("")}${rest.map((b) => this._miniBox(b, many)).join("")}</div>`;
    }

    // A Toniebox 1 as a small card: its settings in a sentence and when it was last
    // seen; the cloud knows no connection state of it, so it shows none
    _miniBox(b, showHousehold) {
      const t = this._t;
      const pic = safeUrl(b.image_url);
      const seen = b.last_seen ? fill(t.lastSeen, { t: this._relative(b.last_seen) }) : "";
      const st = b.settings;
      const chips = (showHousehold && b.household ? this._chip(b.household) : "") +
        (st?.applied === false ? this._chip(t.settingsPending, "warn") : "");
      const summary = st ? this._settingsSummary(st, true) : "";
      const cog = st ? iconButton("cog", t.boxSettingsOf, `data-act="boxset:${esc(b.id)}"`) : "";
      const lines = [summary, seen].filter(Boolean).map((x) => `<span class="supporting">${esc(x)}</span>`).join("");
      return `<ha-card class="mini-box"><div class="mini-head">` +
        (pic ? `<img class="box-pic small" src="${esc(pic)}" alt="">` : "") +
        `<div class="mini-text"><div class="mini-title"><span class="box-name">${esc(b.name || b.id)}</span>${chips}</div>${lines}</div>` +
        cog + `</div></ha-card>`;
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
    // with a switch each, and the form to change or add one
    _bedtime(b) {
      const t = this._t;
      const bt = b.bedtime;
      const editing = this._sched?.box === b.id ? this._sched : null;
      let html = `<div class="tile-head"><span class="tile-title">${esc(t.bedtimes)}</span>` +
        (editing || !bt.schedules ? "" : this._btn(`sadd:${b.id}`, t.addSchedule, "plus")) + `</div>`;
      const next = bt.next_alarm;
      if (next) {
        const at = new Date(time(next.at));
        const when = at.toLocaleString(this._lang, { weekday: "short", hour: "2-digit", minute: "2-digit" });
        const [state, kind] = next.armed ? [t.alarmArmed, "ok"] : next.due ? [t.alarmPending, "warn"] : [t.alarmLater, ""];
        html += `<div class="alarm-next"><span class="fact">${icon("alarm")}${esc(fill(t.nextAlarm, { t: when }))}</span>` +
          `${this._chip(state, kind)}</div>`;
      }
      if (!bt.schedules) return `<div class="tile">${html}<div class="muted small">${esc(t.schedulesUnknown)}</div></div>`;
      if (!bt.schedules.length && !editing) html += `<div class="muted small">${esc(t.noSchedules)}</div>`;
      if (bt.schedules.length) {
        html += `<ul class="schedules">${bt.schedules.map((s) => {
          if (editing?.id === s.id) return `<li class="editing">${this._scheduleForm(editing)}</li>`;
          const times = `${s.sleep_time || "–"} – ${s.wakeup_time || "–"}`;
          const facts = [this._days(s.days), times];
          return `<li><ha-switch data-act="son:${esc(b.id)}:${esc(s.id)}"${s.enabled ? " checked" : ""} aria-label="${esc(t.scheduleOn)}"${this._sched ? " disabled" : ""}></ha-switch>` +
            `<div class="text"><span>${esc(s.name || t.scheduleUnnamed)}${s.alarm_enabled ? ` <span class="alarm-mark" title="${esc(t.alarmOn)}">${icon("alarm")}</span>` : ""}</span>` +
            `<span class="supporting">${esc(facts.join(" · "))}</span></div>` +
            iconButton("pencil", t.edit, `data-act="sedit:${esc(b.id)}:${esc(s.id)}"${this._sched ? " disabled" : ""}`) + `</li>`;
        }).join("")}</ul>`;
      }
      if (editing && editing.id === null) html += this._scheduleForm(editing);
      if (bt.schedules.some((s) => s.alarm_enabled)) html += `<div class="muted small">${esc(t.alarmHint)}</div>`;
      return `<div class="tile">${html}</div>`;
    }

    _scheduleForm(edit) {
      const t = this._t;
      const busy = edit.saving;
      let html = `<div class="sched-form">${edit.id === null ? `<div class="tile-title">${esc(t.scheduleNew)}</div>` : ""}<ha-form data-form="schedule"></ha-form>` +
        `<div class="ch-bar">${this._btn("ssave", t.save, "check", { look: "filled", disabled: busy })}${this._btn("scancel", t.cancel, "close", { disabled: busy })}`;
      if (edit.id !== null) {
        html += this._btn("sdel", edit.confirm ? t.deleteConfirm : t.deleteSchedule, "remove", { disabled: busy, attrs: `class="danger-btn${edit.confirm ? " confirm" : ""}"` });
      }
      html += `</div>`;
      if (edit.error) html += this._alert(fill(t.scheduleFailed, { e: edit.error }), "error");
      return html + `</div>`;
    }

    _scheduleSchema() {
      const days = WEEKDAYS.map((d) => ({ value: d, label: this._dayName(d, "long") }));
      return [
        { name: "name", required: true, selector: { text: {} } },
        { name: "days", required: true, selector: { select: { multiple: true, mode: "list", options: days } } },
        { name: "", type: "grid", schema: [
          { name: "sleep_time", required: true, selector: { time: { no_second: true } } },
          { name: "wakeup_time", required: true, selector: { time: { no_second: true } } },
        ] },
        { name: "enabled", selector: { boolean: {} } },
        { name: "alarm_enabled", selector: { boolean: {} } },
        { name: "alarm_volume", selector: { number: { min: 0, max: 100, step: 5, mode: "slider", unit_of_measurement: "%" } } },
        { name: "alarm_morning_light", selector: { boolean: {} } },
      ];
    }

    // Buttons and switches: "verb:argument"; the bedtimes' verbs begin with "s",
    // the box settings' with "b"
    _act(act) {
      if (/^s(add|edit|save|cancel|del|on)(:|$)/.test(act)) this._scheduleAction(act);
      else if (/^b(edit|save|cancel)(:|$)/.test(act)) this._settingsAction(act);
      else if (/^n(edit|save|cancel|on)(:|$)/.test(act)) this._nightAction(act);
      else if (act.startsWith("pautolock:")) this._setPreference(act.slice(10), "auto_lock");
      else if (act.startsWith("pmarkread:")) this._setPreference(act.slice(10), "mark_read");
      else if (act.startsWith("panalytics:")) this._setPreference(act.slice(11), "analytics");
      else if (act === "dlgclose") this._closeOverlay();
      else if (/^(fig|box|batt|tune)set:/.test(act)) {
        this._closeOverlay();
        if (this._overlayHtml) return;
        const [kind, id] = act.split(/:(.*)/s);
        if (kind === "figset") this._figDialog = id;
        else if (kind === "tuneset") this._tuneDialog = id;
        else if (kind === "boxset") this._boxDialog = id;
        else this._battDialog = id;
        this._render();
      }
      else if (act.startsWith("lock:")) this._setLock(act.slice(5));
      else if (act.startsWith("swapshuffle:")) this._setShuffleOnSwap(act.slice(12));
      else if (act.startsWith("figrename:")) this._updateFigure(act.slice(10), "name");
      else if (act.startsWith("figlive:")) this._updateFigure(act.slice(8), "live");
      else if (act.startsWith("homesave:")) this._renameHousehold(act.slice(9));
      else if (act.startsWith("voucher:")) this._redeemVoucher(act.slice(8));
      else if (act.startsWith("ctl:")) {
        const [, boxId, command, value] = act.split(":");
        this._command(boxId, command, value);
      }
      else if (act.startsWith("tuneoff:")) this._setTune(act.slice(8), null);
      else if (act.startsWith("tuneon:")) {
        const id = act.slice(7);
        const pick = this._tunePick?.[id] || (this._library?.tunes || []).find((x) => x.suitable.includes(id))?.id;
        if (pick) this._setTune(id, pick);
      }
      else this._chapterAction(act);
    }

    // The settings of a box: a summary with the state of the transfer, and the form
    _settingsTile(b) {
      const t = this._t;
      const st = b.settings;
      const editing = this._boxEdit?.box === b.id ? this._boxEdit : null;
      const chips = (st.applied === false ? this._chip(t.settingsPending, "warn") : "") +
        (st.offline_mode ? this._chip(t.offlineMode, "warn") : "");
      let html = `<div class="tile-head"><span class="tile-title">${esc(t.boxSettings)}</span>${chips}<span class="grow"></span>` +
        (editing ? "" : iconButton("pencil", t.edit, `data-act="bedit:${esc(b.id)}"${this._sched || this._boxEdit ? " disabled" : ""}`)) + `</div>`;
      if (editing) return `<div class="tile">${html}${this._settingsForm(editing)}</div></div>`;
      html += `<div class="muted small">${esc(this._settingsSummary(st))}</div>`;
      if (b.night) html += this._night(b);
      return `<div class="tile">${html}</div>`;
    }

    // The settings form, opened; the caller closes the form's outer div
    _settingsForm(editing) {
      const t = this._t;
      let html = `<div class="sched-form"><ha-form data-form="settings"></ha-form><div class="ch-bar">` +
        this._btn("bsave", t.save, "check", { look: "filled", disabled: editing.saving }) +
        this._btn("bcancel", t.cancel, "close", { disabled: editing.saving }) +
        `<span class="muted small hint">${esc(t.settingsHint)}</span></div>`;
      if (editing.error) html += this._alert(fill(t.settingsFailed, { e: editing.error }), "error");
      return html;
    }

    // The settings in one sentence; a Toniebox 1 names all of its few
    _settingsSummary(st, all = false) {
      const t = this._t;
      const v = st.values || {};
      const parts = [];
      if (v.max_volume != null) parts.push(fill(t.sumVolume, { v: v.max_volume }));
      if (all && v.max_headphone_volume != null) parts.push(fill(t.sumPhones, { v: v.max_headphone_volume }));
      if (v.lightring_brightness != null) parts.push(fill(t.sumRing, { v: v.lightring_brightness }));
      if (v.skipping_enabled) parts.push(t.sumSkip);
      if (v.led_level) parts.push(fill(t.sumLed, { v: t[`v_${v.led_level}`] || v.led_level }));
      if (all && v.accelerometer_enabled) parts.push(t.sumTilt);
      return parts.length ? cap(parts.join(" · ")) : t.noSettings;
    }

    // The night mode of the light ring: a switch with the span, or the form
    _night(b) {
      const t = this._t;
      const mode = b.night.mode;
      const editing = this._nightEdit?.box === b.id ? this._nightEdit : null;
      const busy = this._sched || this._boxEdit || this._nightEdit;
      if (editing) {
        let html = `<div class="sched-form"><div class="tile-title">${esc(t.nightMode)}</div><ha-form data-form="night"></ha-form><div class="ch-bar">` +
          this._btn("nsave", t.save, "check", { look: "filled", disabled: editing.saving }) +
          this._btn("ncancel", t.cancel, "close", { disabled: editing.saving }) +
          `<span class="muted small hint">${esc(t.nightHint)}</span></div>`;
        if (editing.error) html += this._alert(fill(t.nightFailed, { e: editing.error }), "error");
        return html + `</div>`;
      }
      if (!mode) {
        return `<div class="ch-bar night-row">${this._btn(`nedit:${b.id}`, t.nightSetup, "sleep", { disabled: !!busy })}</div>`;
      }
      const phase = b.night.phase === "night" ? this._chip(t.nightNow, "on") : b.night.phase === "day" ? this._chip(t.dayNow) : "";
      return `<ul class="schedules night-row"><li><ha-switch data-act="non:${esc(b.id)}"${mode.enabled ? " checked" : ""} aria-label="${esc(t.nightMode)}"${busy ? " disabled" : ""}></ha-switch>` +
        `<div class="text"><span>${esc(t.nightMode)} ${phase}</span><span class="supporting">${esc(fill(t.nightSummary, mode))}</span></div>` +
        iconButton("pencil", t.edit, `data-act="nedit:${esc(b.id)}"${busy ? " disabled" : ""}`) + `</li></ul>`;
    }

    _nightSchema() {
      const percent = { number: { min: 0, max: 100, step: 1, mode: "slider", unit_of_measurement: "%" } };
      return [
        { name: "enabled", selector: { boolean: {} } },
        { name: "", type: "grid", schema: [
          { name: "start", required: true, selector: { time: { no_second: true } } },
          { name: "end", required: true, selector: { time: { no_second: true } } },
        ] },
        { name: "night", required: true, selector: percent },
        { name: "day", required: true, selector: percent },
      ];
    }

    _nightAction(act) {
      const [verb, boxId] = act.split(/:(.*)/s);
      const box = this._overview?.boxes.find((x) => x.id === boxId);
      switch (verb) {
        case "nedit": {
          if (!box?.night || this._nightEdit || this._boxEdit || this._sched) return;
          const mode = box.night.mode;
          const ring = box.settings?.values?.lightring_brightness;
          this._nightEdit = { box: boxId, saving: false, error: null, data: mode
            ? { enabled: mode.enabled, start: mode.start, end: mode.end, night: mode.night, day: mode.day }
            : { enabled: true, start: "19:00", end: "07:00", night: 10, day: Number.isFinite(ring) ? ring : 60 } };
          break;
        }
        case "ncancel":
          if (this._nightEdit?.saving) return;
          this._nightEdit = null;
          break;
        case "nsave":
          this._saveNight();
          return;
        case "non": {
          const mode = box?.night?.mode;
          if (!mode) return;
          this._sendNight(boxId, { ...mode, enabled: !mode.enabled });
          return;
        }
        default:
          return;
      }
      this._render();
    }

    async _saveNight() {
      const edit = this._nightEdit;
      if (!edit || edit.saving) return;
      const d = edit.data;
      const mode = { enabled: !!d.enabled, start: clock(d.start), end: clock(d.end), night: Math.round(Number(d.night)), day: Math.round(Number(d.day)) };
      if (!mode.start || !mode.end || !Number.isFinite(mode.night) || !Number.isFinite(mode.day)) return;
      edit.saving = true;
      edit.error = null;
      this._render();
      await this._sendNight(edit.box, mode, edit);
      this._render();
    }

    // The integration answers with the box as it is afterwards
    async _sendNight(boxId, mode, edit = null) {
      if (!this._hass) return;
      try {
        const box = await this._hass.callWS({ type: "storybox_plus/night/set", box_id: boxId,
          enabled: mode.enabled, start: mode.start, end: mode.end, night: mode.night, day: mode.day });
        const boxes = this._overview?.boxes || [];
        const i = boxes.findIndex((x) => x.id === boxId);
        if (i >= 0) boxes[i] = box;
        if (edit && this._nightEdit === edit) this._nightEdit = null;
      } catch (err) {
        if (edit) {
          edit.saving = false;
          edit.error = this._errText(err);
        } else {
          this._errors.overview = this._errText(err);
        }
      }
      if (!edit) this._render();
    }

    _settingsSchema() {
      const t = this._t;
      const edit = this._boxEdit;
      if (!edit) return [];
      const box = this._overview?.boxes.find((x) => x.id === edit.box);
      const values = box?.settings?.values || {};
      const live = box?.generation === "toniebox_2";
      const pick = (options) => ({ select: { mode: "dropdown", options } });
      const sides = [["left", t.v_left], ["right", t.v_right]].map(([value, label]) => ({ value, label }));
      const percent = (min) => ({ number: { min, max: 100, step: 1, mode: "slider", unit_of_measurement: "%" } });
      const volumes = [25, 50, 75, 100].map((n) => ({ value: String(n), label: `${n} %` }));
      const language = (code) => {
        try {
          return new Intl.DisplayNames([this._lang], { type: "language" }).of(code) || code;
        } catch {
          return code;
        }
      };
      const withCurrent = (list, current) => (current && !list.includes(current) ? [...list, current] : list);
      const fields = {
        // A Toniebox 2 takes any percent, a classic box the four steps
        max_volume: live ? percent(1) : pick(volumes),
        max_headphone_volume: live ? percent(1) : pick(volumes),
        lightring_brightness: percent(0),
        bedtime_lightring_brightness: percent(0),
        bedtime_max_volume: percent(1),
        bedtime_max_headphone_volume: percent(1),
        skipping_enabled: { boolean: {} },
        skipping_direction: pick(sides),
        scrubbing_enabled: { boolean: {} },
        accelerometer_enabled: { boolean: {} },
        tap_direction: pick(sides),
        led_level: pick(["on", "dimmed", "off"].map((value) => ({ value, label: t[`v_${value}`] }))),
        age_mode: pick(withCurrent(["1+", "3+"], values.age_mode).map((value) => ({ value, label: value }))),
        language: pick(withCurrent(["de", "en", "en-us", "fr"], values.language).map((value) => ({ value, label: language(value) }))),
      };
      return [
        { name: "name", required: true, selector: { text: {} } },
        ...Object.keys(fields).filter((k) => k in values).map((k) => ({ name: k, required: true, selector: fields[k] })),
      ];
    }

    _settingsAction(act) {
      const [verb, boxId] = act.split(/:(.*)/s);
      switch (verb) {
        case "bedit": {
          const box = this._overview?.boxes.find((x) => x.id === boxId);
          if (!box?.settings || this._boxEdit || this._sched || this._nightEdit) return;
          // The volume choices are a list of words for the form; the integration wants numbers
          const data = { name: box.name, ...box.settings.values };
          if (box.generation !== "toniebox_2") for (const k of ["max_volume", "max_headphone_volume"]) if (k in data) data[k] = String(data[k]);
          this._boxEdit = { box: boxId, data, orig: { ...data }, saving: false, error: null };
          break;
        }
        case "bcancel":
          if (this._boxEdit?.saving) return;
          this._boxEdit = null;
          break;
        case "bsave":
          this._saveSettings();
          return;
        default:
          return;
      }
      this._render();
    }

    // Only what changed goes to the integration
    async _saveSettings() {
      const edit = this._boxEdit;
      if (!edit || edit.saving || !this._hass) return;
      const msg = { type: "storybox_plus/box/settings", box_id: edit.box };
      for (const [k, v] of Object.entries(edit.data)) {
        if (v === edit.orig[k] || v === undefined || v === null) continue;
        if (k === "name") {
          if (!String(v).trim()) return;
          msg.name = String(v).trim();
        } else if (k === "max_volume" || k === "max_headphone_volume") msg[k] = Math.round(Number(v));
        else if (typeof edit.orig[k] === "number") msg[k] = Math.round(Number(v));
        else msg[k] = v;
      }
      if (Object.keys(msg).length === 2) {
        this._boxEdit = null;
        this._render();
        return;
      }
      edit.saving = true;
      edit.error = null;
      this._render();
      try {
        const box = await this._hass.callWS(msg);
        const boxes = this._overview?.boxes || [];
        const i = boxes.findIndex((x) => x.id === edit.box);
        if (i >= 0) boxes[i] = box;
        if (this._boxEdit === edit) this._boxEdit = null;
      } catch (err) {
        edit.saving = false;
        edit.error = this._errText(err);
      }
      this._render();
    }

    _scheduleAction(act) {
      const [verb, rest = ""] = act.split(/:(.*)/s);
      const [boxId, id] = rest.split(/:(.*)/s);
      const box = this._overview?.boxes.find((x) => x.id === boxId);
      const edit = this._sched;
      switch (verb) {
        case "sadd":
          if (!box || edit) return;
          this._sched = { box: boxId, id: null, saving: false, error: null, confirm: false,
            data: { name: "", days: WEEKDAYS.slice(0, 5), sleep_time: "19:00", wakeup_time: "06:30", enabled: true, alarm_enabled: true, alarm_volume: 50, alarm_morning_light: true } };
          break;
        case "sedit": {
          const s = box?.bedtime?.schedules?.find((x) => x.id === id);
          if (!s || edit) return;
          const { id: _id, ...data } = s;
          this._sched = { box: boxId, id: s.id, saving: false, error: null, confirm: false, data: { ...data, days: [...s.days] } };
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
          if (!edit.confirm) {
            edit.confirm = true;
            break;
          }
          this._saveSchedule(true);
          return;
        case "son": {
          const s = box?.bedtime?.schedules?.find((x) => x.id === id);
          if (!s || edit) return;
          this._sendSchedule(boxId, { type: "storybox_plus/bedtime/save", box_id: boxId, schedule_id: s.id, enabled: !s.enabled });
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
        msg = {
          type: "storybox_plus/bedtime/save", box_id: edit.box,
          name: String(d.name || "").trim(), days: Array.isArray(d.days) ? d.days : [],
          sleep_time: clock(d.sleep_time), wakeup_time: clock(d.wakeup_time),
          enabled: !!d.enabled, alarm_enabled: !!d.alarm_enabled,
          alarm_volume: Math.round(Number(d.alarm_volume ?? 100)), alarm_morning_light: !!d.alarm_morning_light,
        };
        if (edit.id !== null) msg.schedule_id = edit.id;
        if (!msg.days.length || !msg.sleep_time || !msg.wakeup_time) return;
      }
      edit.saving = true;
      edit.error = null;
      this._render();
      const ok = await this._sendSchedule(edit.box, msg, edit);
      if (ok && this._sched === edit) this._sched = null;
      this._render();
    }

    // The integration answers with the box as it is afterwards
    async _sendSchedule(boxId, msg, edit = null) {
      try {
        const box = await this._hass.callWS(msg);
        const boxes = this._overview?.boxes || [];
        const i = boxes.findIndex((x) => x.id === boxId);
        if (i >= 0) boxes[i] = box;
        if (!edit) this._render();
        return true;
      } catch (err) {
        if (edit) {
          edit.saving = false;
          edit.confirm = false;
          edit.error = this._errText(err);
        } else {
          this._errors.overview = this._errText(err);
          this._render();
        }
        return false;
      }
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
        this._ctlError = { id: boxId, message: this._errText(err) };
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
      const b = this._overview?.boxes?.find((x) => x.id === sent.box);
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

    // The battery in the overlay: level, what a charge lasts, and the charge history
    _battery(b) {
      const t = this._t;
      const s = b.battery_stats;
      const level = this._batteryLevel(b);
      const cur = s.current;
      const parts = [];
      if (Number.isFinite(b.battery_remaining_hours)) parts.push(fill(t.remaining, { h: hours(b.battery_remaining_hours) }));
      if (Number.isFinite(s.average_full_hours)) parts.push(fill(t.perFull, { h: this._num(s.average_full_hours) }));
      else if (Number.isFinite(cur?.per_full)) parts.push(fill(t.perFullProjected, { h: this._num(cur.per_full) }));
      if (s.count > 0) parts.push(fill(s.count === 1 ? t.charge1 : t.chargesN, { n: s.count }));
      if (Number.isFinite(cur?.hours) && Number.isFinite(cur?.from)) parts.push(fill(t.nowSince, { t: hours(cur.hours), p: cur.from }));
      // The overlay is titled "Battery" already: the level leads, large
      let html = `<div class="batt-level fact">${level}</div>` +
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
        html += `<div class="pref-head">${esc(t.history)}</div><table class="cycles"><thead><tr>` +
          `<th>${esc(t.colDay)}</th><th>${esc(t.colOn)}</th><th>${esc(t.colLevel)}</th><th>${esc(t.colPerFull)}</th></tr></thead>` +
          `<tbody>${rows}</tbody></table>`;
      }
      return `<div class="batt-view">${html}</div>`;
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
        (f.volume ? this._chip(fill(t.figVolumeChip, { v: f.volume })) : "") +
        (this._tuneOn(f.id) ? this._chip(t.tune, "on") : "") +
        (f.live ? this._chip(t.liveChip) : "") +
        (f.locked ? `<span class="lock" title="${esc(t.locked)}">${icon("lock")}</span>` : "");
      let detail = "";
      if (f.kind === "creative") {
        const free = [fill(t.free, { t: hm(f.seconds_remaining) })];
        if (Number.isFinite(f.chapters_remaining)) free.push(fill(f.chapters_remaining === 1 ? t.chapter1 : t.chaptersN, { n: f.chapters_remaining }));
        detail += `<div class="muted small">${esc(free.join(" · "))}</div>`;
      }
      // Only a creative figure takes chapters; a bought one takes favourites. Volume,
      // lock, Tune and shuffling sit behind the figure's cog
      detail += f.kind === "creative" ? this._creativeDetail(f) : this._boughtDetail(f, chapters);
      return `<div class="figure${open ? " open" : ""}"><div class="fig-head" role="button" tabindex="0" data-fold="${esc(f.id)}" aria-expanded="${open}">` +
        `${this._pic(f.image_url)}<div class="text"><span class="headline">${esc(f.name)}</span>` +
        `${sub ? `<span class="supporting">${sub}</span>` : ""}<span class="supporting">${meta}</span></div>` +
        `<span class="badges">${badges}</span>` +
        (this._tuneOn(f.id) || (this._library?.tunes || []).some((x) => x.suitable.includes(f.id) && !x.assigned.includes(f.id))
          ? iconButton("song", t.tuneOf, `class="fig-cog" data-act="tuneset:${esc(f.id)}"`) : "") +
        `${iconButton("cog", t.figSettings, `class="fig-cog" data-act="figset:${esc(f.id)}"`)}` +
        `${icon("chevron")}</div><div class="detail">${detail}</div></div>`;
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
            iconButton("pencil", t.renameChapter, `data-act="chrename:${i}"`) +
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
          this._btn("save", t.save, "check", { look: "filled", disabled: busy || !!edit.clearStep }) +
          this._btn("cancel", t.cancel, "close", { disabled: busy }) +
          `<span class="muted small hint">${esc(t.editHint)}</span></div>`;
        if (edit.chapters.length) {
          html += `<div class="ch-bar">` +
            (edit.chapters.length > 1 ? this._btn("sorttitle", t.sortTitle, "sort", { disabled: busy }) + this._btn("shuffle", t.shuffle, "shuffle", { disabled: busy }) : "") +
            this._btn("clearall", t.clearAll, "remove", { disabled: busy || !!edit.clearStep, attrs: 'class="danger-btn"' }) + `</div>`;
        }
        // Removing all chapters asks twice: once whether, once whether the files are kept elsewhere
        if (edit.clearStep === 1 || edit.clearStep === 2) {
          const [text, yes] = edit.clearStep === 1
            ? [fill(t.clearAsk1, { n: edit.chapters.length }), t.clearYes1]
            : [t.clearAsk2, t.clearYes2];
          html += `<div class="clear-ask">` + this._alert(text, edit.clearStep === 1 ? "warning" : "error") +
            // Keeping them is the obvious choice, first and filled; removing comes second, plain
            `<div class="ch-bar">${this._btn("clearno", t.clearNo, "check", { look: "filled" })}` +
            `${this._btn("clearyes", yes, "remove", { attrs: 'variant="danger"' })}</div></div>`;
        }
        if (edit.error) html += this._alert(fill(t.saveFailed, { e: edit.error }), "error");
        // One chapter at a time gets a new name, in a form above the list
        if (Number.isInteger(edit.renaming) && edit.chapters[edit.renaming]) {
          html += `<div class="link-form"><ha-form data-form="chname"></ha-form><div class="ch-bar">` +
            this._btn("chrenameok", t.apply, "check", { look: "filled" }) + this._btn("chrenamecancel", t.cancel, "close") + `</div></div>`;
        }
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
        (this._library?.speech
          ? this._btn(`text:${f.id}`, t.fromText, "text", { disabled: busy || this._speak?.id === f.id })
          : `<span class="tip" title="${esc(t.speechMissing)}">${this._btn(`text:${f.id}`, t.fromText, "text", { disabled: true })}</span>`) +
        this._btn(`code:${f.id}`, t.fromCode, "plus", { disabled: busy || this._code?.id === f.id }) +
        // Without chapters there is nothing to edit: name and live mode sit behind the cog
        (f.chapters.length ? this._btn(`edit:${f.id}`, t.edit, "pencil", { disabled: busy }) : "") + `</div>`;
      // Link, text and code open their form in the overlay
      if (up) {
        html += up.error
          ? this._alert(fill(up.link ? t.linkFailed : t.uploadFailed, { e: up.error }), "error", "",
            `<ha-button slot="action" appearance="plain" data-act="dismiss:${esc(f.id)}">${esc(t.dismiss)}</ha-button>`)
          : `<div class="muted small busy">${esc(this._progressText(up))}</div>`;
      }
      return html + this._chapterList(f.chapters);
    }

    // The name or the live mode of a creative figure, from its settings
    async _updateFigure(id, what) {
      const f = this._library?.tonies.find((x) => x.id === id);
      if (!f || !this._hass || this._figName?.busy) return;
      const fn = this._figName?.id === id ? this._figName : { id, name: f.name };
      const msg = { type: "storybox_plus/figure/update", tonie_id: id };
      if (what === "name") {
        const name = String(fn.name || "").trim();
        if (!name || name === f.name) return;
        msg.name = name;
      } else msg.live = !f.live;
      this._figName = { ...fn, busy: true, error: null };
      this._refreshList();
      try {
        this._replaceTonie(await this._hass.callWS(msg));
        this._figName = { id, name: undefined, busy: false, error: null };
      } catch (err) {
        this._figName = { ...fn, busy: false, error: this._errText(err) };
      }
      this._refreshList();
    }

    async _setShuffleOnSwap(id) {
      const f = this._library?.tonies.find((x) => x.id === id);
      if (!f || !this._hass) return;
      this._shuffleError = null;
      try {
        f.shuffle_on_swap = (await this._hass.callWS({ type: "storybox_plus/figure/shuffle_on_swap", tonie_id: id, enabled: !f.shuffle_on_swap })).shuffle_on_swap;
      } catch (err) {
        this._shuffleError = { id, message: this._errText(err) };
      }
      this._refreshList();
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
        case "link":
          if (this._uploads[arg] && !this._uploads[arg].error) return;
          delete this._uploads[arg];
          this._link = { id: arg, url: "" };
          this._figDialog = null;
          this._refreshList();
          this.shadowRoot.querySelector('ha-form[data-form="link"]')?.focus();
          return;
        case "linkadd":
          this._fetchLink();
          return;
        case "code":
          this._code = { id: arg, token: "", busy: false, error: null };
          this._figDialog = null;
          break;
        case "text":
          if (!this._library?.speech) return;
          this._speak = { id: arg, title: "", text: "", busy: false, error: null };
          this._figDialog = null;
          break;
        case "speakcancel":
          if (this._speak?.busy) return;
          this._speak = null;
          break;
        case "speakadd":
          this._addFromText();
          return;
        case "codecancel":
          if (this._code?.busy) return;
          this._code = null;
          break;
        case "codeadd":
          this._redeemCode();
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
      // The chapters go only when they changed, because every change makes the cloud convert
      const before = this._library?.tonies.find((x) => x.id === edit.id);
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
        edit.error = this._errText(err);
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
          up.error = this._errText(err);
          break;
        }
      }
      if (!up.error && this._uploads[id] === up) delete this._uploads[id];
      this._refreshList();
    }

    // The volume of a figure goes to the integration at once; the answer is kept
    async _setFigureVolume(id, level) {
      const f = this._library?.tonies.find((x) => x.id === id);
      if (!f || !this._hass || (f.volume ?? null) === level) return;
      this._volError = null;
      try {
        f.volume = (await this._hass.callWS({ type: "storybox_plus/figure/volume", tonie_id: id, level })).volume;
      } catch (err) {
        this._volError = { id, message: this._errText(err) };
      }
      this._refreshList();
    }

    // The level of a figure, for every kind of figure, below its chapters' tools
    _volumeRow(f) {
      const t = this._t;
      let html = `<div class="vol-row"><ha-form data-form="vol:${esc(f.id)}"></ha-form><span class="muted small hint">${esc(t.figVolumeHint)}</span></div>`;
      if (this._volError?.id === f.id) html += this._alert(fill(t.figVolumeFailed, { e: this._volError.message }), "error");
      return html;
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
        this._favError = { id, message: this._errText(err) };
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
            up.error = this._errText({ code: ev.code, message: ev.message });
            end();
          } else {
            up.stage = ev.stage;
            if (ev.title) up.name = ev.title;
            up.pct = ev.total ? Math.floor((ev.done / ev.total) * 100) : null;
          }
          this._refreshList();
        }, { type: "storybox_plus/chapters/add_link", tonie_id: id, url }, { resubscribe: false });
      } catch (err) {
        up.error = this._errText(err);
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
        `<div class="muted">${esc(t.total)} · ${esc(label)}</div>` + this._comparison(s));
      if (!s.total_seconds && !s.top.length && !s.top_placed?.length) return html + this._card("", `<div class="muted">${esc(t.noStats)}</div>`);
      const max = Math.max(...s.top.map((x) => x.seconds), 1);
      if (s.top.length) {
        html += this._card(esc(t.top), `<ol class="top">${s.top.map((x, i) =>
          `<li><span class="rank">${i + 1}</span>${this._pic(x.image_url, " small")}<div class="text"><span class="headline">${esc(x.name || t.unknownFigure)}</span>` +
          `<div class="bar"><div style="width:${((100 * x.seconds) / max).toFixed(1)}%"></div></div></div><span class="len">${esc(hm(x.seconds))}</span></li>`).join("")}</ol>`);
      }
      if (s.top_placed?.length) {
        const pmax = Math.max(...s.top_placed.map((x) => x.times), 1);
        html += this._card(esc(t.topPlaced), `<ol class="top placed">${s.top_placed.map((x, i) =>
          `<li><span class="rank">${i + 1}</span>${this._pic(x.image_url, " small")}<div class="text"><span class="headline">${esc(x.name || t.unknownFigure)}</span>` +
          `<div class="bar"><div style="width:${((100 * x.times) / pmax).toFixed(1)}%"></div></div></div><span class="len">${esc(fill(t.placedTimes, { n: x.times }))}</span></li>`).join("")}</ol>`);
      }
      if (s.top_chapters?.length) {
        const cmax = Math.max(...s.top_chapters.map((x) => x.seconds), 1);
        html += this._card(esc(t.topChapters), `<ol class="top">${s.top_chapters.map((x, i) =>
          `<li><span class="rank">${i + 1}</span>${this._pic(x.image_url, " small")}<div class="text"><span class="headline">${esc(x.title || `${t.chapter} ${x.chapter + 1}`)}</span>` +
          `<span class="supporting">${esc(x.name || t.unknownFigure)} · ${esc(t.chapter)} ${x.chapter + 1}</span>` +
          `<div class="bar"><div style="width:${((100 * x.seconds) / cmax).toFixed(1)}%"></div></div></div><span class="len">${esc(hm(x.seconds))}</span></li>`).join("")}</ol>`);
      }
      html += this._dayChart(s);
      html += this._heatmap(s);
      if (s.per_box.length) {
        html += this._card(esc(t.perBox), `<table class="kv">${s.per_box.map((b) =>
          `<tr><th>${esc(b.name || b.box_id)}</th><td>${esc(hm(b.seconds))} h</td></tr>`).join("")}</table>`);
      }
      return html;
    }

    // The change against the window of the same length before, while that one was counted
    _comparison(s) {
      if (!s.days || !Number.isFinite(s.previous_total_seconds) || s.previous_total_seconds <= 0) return "";
      const change = Math.round(((s.total_seconds - s.previous_total_seconds) / s.previous_total_seconds) * 100);
      const p = `${change > 0 ? "+" : change < 0 ? "−" : "±"}${Math.abs(change)} %`;
      const kind = change > 0 ? "ok" : change < 0 ? "warn" : "";
      return `<div class="compare">${this._chip(fill(this._t.vsBefore, { p, n: s.days }), kind)}</div>`;
    }

    // Weekdays as rows, hours as columns; the shade is the share of the busiest cell.
    // With several boxes, chips choose one or all of them
    _heatmap(s) {
      const t = this._t;
      const boxes = Array.isArray(s.heatmap_boxes) ? s.heatmap_boxes : [];
      const pick = boxes.find((b) => b.box_id === this._heatBox);
      const grid = pick ? pick.grid : s.heatmap;
      if (!Array.isArray(grid) || !grid.flat().some((v) => v > 0)) return "";
      const max = Math.max(...grid.flat(), 1);
      const days = WEEKDAYS.map((d) => this._dayName(d));
      let rows = "";
      grid.forEach((hours, w) => {
        rows += `<div class="hm-day">${esc(days[w])}</div>` + hours.map((v, h) => {
          const share = v / max;
          return `<div class="hm-cell" style="--a:${share.toFixed(3)}" title="${esc(`${days[w]} ${pad(h)}:00 · ${hm(v)} h`)}"></div>`;
        }).join("");
      });
      const scale = `<div></div>` + Array.from({ length: 24 }, (_, h) => `<div class="hm-hour">${h % 6 === 0 ? pad(h) : ""}</div>`).join("");
      const chips = boxes.length > 1
        ? `<div class="chips heat-boxes">` + [["", t.allBoxes], ...boxes.map((b) => [b.box_id, b.name || b.box_id])].map(([id, name]) =>
          `<button class="chip pick${(pick ? pick.box_id : "") === id ? " on" : ""}" data-heatbox="${esc(id)}" aria-pressed="${(pick ? pick.box_id : "") === id}">${esc(name)}</button>`).join("") + `</div>`
        : "";
      return this._card(esc(t.whenListened), `${chips}<div class="heatmap">${rows}${scale}</div><div class="muted small">${esc(t.whenHint)}</div>`);
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

  customElements.define("storybox-plus-panel", StoryboxPlusPanel);
}
