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
    song: "M16,9H13V14.5A2.5,2.5 0 0,1 10.5,17A2.5,2.5 0 0,1 8,14.5A2.5,2.5 0 0,1 10.5,12C11.07,12 11.58,12.19 12,12.5V7H16M19,3H5A2,2 0 0,0 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V5A2,2 0 0,0 19,3Z",
    tune: "M3,17V19H9V17H3M3,5V7H13V5H3M13,21V19H21V17H13V15H11V21H13M7,9V11H3V13H7V15H9V9H7M21,13V11H11V13H21M15,9H17V7H21V5H17V3H15V9Z",
    refresh: "M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z",
    lock: "M12,17A2,2 0 0,0 14,15C14,13.89 13.1,13 12,13A2,2 0 0,0 10,15A2,2 0 0,0 12,17M18,8A2,2 0 0,1 20,10V20A2,2 0 0,1 18,22H6A2,2 0 0,1 4,20V10C4,8.89 4.9,8 6,8H7V6A5,5 0 0,1 12,1A5,5 0 0,1 17,6V8H18M12,3A3,3 0 0,0 9,6V8H15V6A3,3 0 0,0 12,3Z",
    chevron: "M7.41,8.58L12,13.17L16.59,8.58L18,10L12,15.41L6,9.41L7.41,8.58Z",
    play: "M8,5.14V19.14L19,12.14L8,5.14Z",
    pause: "M14,19H18V5H14M6,19H10V5H6V19Z",
    flash: "M7,2V13H10V22L17,10H13L17,2H7Z",
    volume: "M5,9V15H9L14,20V4L9,9M18.5,12C18.5,10.23 17.5,8.71 16,7.97V16C17.5,15.29 18.5,13.76 18.5,12Z",
    alarm: "M12,20A7,7 0 0,1 5,13A7,7 0 0,1 12,6A7,7 0 0,1 19,13A7,7 0 0,1 12,20M12,4A9,9 0 0,0 3,13A9,9 0 0,0 12,22A9,9 0 0,0 21,13A9,9 0 0,0 12,4M12.5,8H11V14L15.75,16.85L16.5,15.62L12.5,13.25V8M7.88,3.39L6.6,1.86L2,5.71L3.29,7.24L7.88,3.39M22,5.72L17.4,1.86L16.11,3.39L20.71,7.25L22,5.72Z",
    plus: "M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z",
    prev: "M6,18V6H8V18H6M9.5,12L18,6V18L9.5,12Z",
    headphones: "M12,1C7,1 3,5 3,10V17A3,3 0 0,0 6,20H9V12H5V10A7,7 0 0,1 12,3A7,7 0 0,1 19,10V12H15V20H18A3,3 0 0,0 21,17V10C21,5 16.97,1 12,1Z",
    next: "M16,18H18V6H16M6,18L14.5,12L6,6V18Z",
    minus: "M19,13H5V11H19V13Z",
    sleepOff: "M2,5.27L3.28,4L20,20.72L18.73,22L12.73,16H9V14L9.79,13.05L2,5.27M23,12H17V10L20.39,6H17V4H23V6L19.62,10H23V12M9.82,8H15V10L13.54,11.72L9.82,8M7,20H1V18L4.39,14H1V12H7V14L3.62,18H7V20Z",
    sleep: "M23,12H17V10L20.39,6H17V4H23V6L19.62,10H23V12M15,16H9V14L12.39,10H9V8H15V10L11.62,14H15V16M7,20H1V18L4.39,14H1V12H7V14L3.62,18H7V20Z",
    pencil: "M20.71,7.04C21.1,6.65 21.1,6 20.71,5.63L18.37,3.29C18,2.9 17.35,2.9 16.96,3.29L15.12,5.12L18.87,8.87M3,17.25V21H6.75L17.81,9.93L14.06,6.18L3,17.25Z",
    check: "M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z",
    close: "M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z",
    upload: "M9,16V10H5L12,3L19,10H15V16H9M5,20V18H19V20H5Z",
    up: "M13,20H11V8L5.5,13.5L4.08,12.08L12,4.16L19.92,12.08L18.5,13.5L13,8V20Z",
    down: "M11,4H13V16L18.5,10.5L19.92,11.92L12,19.84L4.08,11.92L5.5,10.5L11,16V4Z",
    remove: "M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z",
    sort: "M19 17H22L18 21L14 17H17V3H19M11 13V15L7.67 19H11V21H5V19L8.33 15H5V13M9 3H7C5.9 3 5 3.9 5 5V11H7V9H9V11H11V5C11 3.9 10.11 3 9 3M9 7H7V5H9Z",
    shuffle: "M14.83,13.41L13.42,14.82L16.55,17.95L14.5,20H20V14.5L17.96,16.54L14.83,13.41M14.5,4L16.54,6.04L4,18.59L5.41,20L17.96,7.46L20,9.5V4M10.59,9.17L5.41,4L4,5.41L9.17,10.58L10.59,9.17Z",
    star: "M12,17.27L18.18,21L16.54,13.97L22,9.24L14.81,8.62L12,2L9.19,8.62L2,9.24L7.45,13.97L5.82,21L12,17.27Z",
    starOff: "M12,15.39L8.24,17.66L9.23,13.38L5.91,10.5L10.29,10.13L12,6.09L13.71,10.13L18.09,10.5L14.77,13.38L15.76,17.66M22,9.24L14.81,8.63L12,2L9.19,8.63L2,9.24L7.45,13.97L5.82,21L12,17.27L18.18,21L16.54,13.97L22,9.24Z",
    text: "M18.5,4L19.66,8.35L18.7,8.61C18.25,7.74 17.79,6.87 17.26,6.43C16.73,6 16.11,6 15.5,6H13V16.5C13,17 13,17.5 13.33,17.75C13.67,18 14.33,18 15,18V19H9V18C9.67,18 10.33,18 10.67,17.75C11,17.5 11,17 11,16.5V6H8.5C7.89,6 7.27,6 6.74,6.43C6.21,6.87 5.75,7.74 5.3,8.61L4.34,8.35L5.5,4H18.5Z",
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
    ["preferences", "tune", "tabPreferences"],
  ];
  const KINDS = ["all", "content", "creative", "disc"];
  // Range chip, days asked from the backend (null: since the setup)
  const RANGES = [["7", 7], ["30", 30], ["365", 365], ["all", null]];

  const TEXTS = {
    en: {
      tabBoxes: "Boxes", tabFigures: "Figures", tabListening: "Listening", tabPreferences: "Settings",
      prefVoucher: "Tunes voucher", voucherCode: "Voucher code", voucherRedeem: "Redeem",
      voucherDone: "Redeemed: {n} Tunes added.", voucherNone: "Redeemed, but the cloud names no new Tune.", voucherFailed: "Redeeming failed: {e}",
      voucherHint: "A voucher can be redeemed once; the Tunes then show on the figures they fit.",
      fromText: "From text", textTitle: "Title (optional)", textBody: "Text to be spoken",
      textHint: "Piper, the local voice of Home Assistant, speaks the text; the recording becomes a chapter. The text stays in the house.",
      speechMissing: "Needs a Piper voice in Home Assistant: set up the Wyoming integration with Piper.",
      textBusy: "Piper speaks the text and it goes to the cloud …", textFailed: "Adding from text failed: {e}",
      fromCode: "From a code", codePlaceholder: "Content code", codeHint: "Ready-made content from a code (for example on a card) is added to the figure; the cloud then converts it.",
      codeFailed: "Adding from the code failed: {e}",
      prefHousehold: "Household", householdName: "Name of the household", householdSaved: "Saved", householdFailed: "Renaming failed: {e}",
      members: "Members", membersUnknown: "The members could not be read yet.", memberYou: "You",
      role_owner: "Owner", role_full: "Full access", role_limited: "Limited access", role_unknown: "Unknown role",
      membersHint: "As the cloud shows them to this account; members and invitations are managed in the app.",
      prefListening: "Listening time", prefAnalytics: "Count listening time",
      prefAnalyticsHint: "Keeps sums per day, figure, box, chapter and hour for the listening tab, never single plays. Switching it off deletes the sums.",
      prefFigures: "Figures", prefAutoLock: "Lock new figures and discs to the household",
      prefAutoLockHint: "A bought figure or disc that is new in the account is locked once, so it cannot be claimed into another household. Unlocked on its page or in the app, it stays unlocked.",
      prefNotices: "Notifications", prefMarkRead: "Mark notifications as read in the cloud once passed on",
      prefMarkReadHint: "The app then shows them no more. Broadcasts to all users are dismissed instead.",
      prefCloud: "Cloud", cloudVersion: "Backend version {v}", cloudTested: "tested", cloudUntested: "tested with {t}",
      cloudUnknown: "The cloud's version is not known yet.",
      cloudDiffers: "The cloud runs release {v}; Storybox Plus was tested with {t}. Should something not work, the cloud's interface may have changed.",
      prefFailed: "Saving the settings failed: {e}",
      lockSwitch: "Locked to the household", lockHint: "A locked figure cannot be claimed into another household.",
      lockFailed: "Changing the lock failed: {e}",
      tune: "Tune", tuneOn: "Tune on it: {t}", tuneRemove: "Take the Tune off", tunePick: "Bought Tune", tuneAssign: "Lay on",
      tuneLeft: "{n} more times", tuneHintCreative: "The figure's chapters stay; they play again once the Tune is taken off.",
      tuneHint: "The figure plays the Tune instead of its own story until it is taken off.", tuneFailed: "Changing the Tune failed: {e}",
      refresh: "Refresh", settings: "Settings", asOf: "As of {t}", retry: "Try again", loading: "Loading …",
      about: "Storybox Plus {version}", aboutCommit: "Storybox Plus {version} · commit {commit}",
      failed: "The data could not be read",
      noEntry: "No account is set up. Add one under Settings → Devices & services.",
      notLoaded: "No account is loaded at the moment. Home Assistant tries again by itself.",
      pushDown: "Live channel not connected – states may be stale",
      noBoxes: "No box in this account yet.", toniebox2: "Toniebox 2", classic: "Toniebox 1",
      online: "Online", offline: "Offline", unknown: "Unknown", charging: "charging",
      sleepUntil: "Sleep timer until {t}", sleepOn: "Sleep timer active", firmware: "Firmware",
      classicNote: "A Toniebox 1 reports no live data.", lastSeen: "Last seen {t}", never: "never",
      battery: "Battery", perFull: "about {h} h per full charge", perFullProjected: "about {h} h per full charge, projected",
      remaining: "lasts about {h} more", charge1: "1 charge", chargesN: "{n} charges", nowSince: "now {t} since {p} %", noCycles: "no discharge recorded yet",
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
      moveUp: "Move up", moveDown: "Move down", remove: "Remove", renameChapter: "Rename", chapterName: "Name of the chapter", apply: "Apply",
      sortTitle: "Sort A–Z", shuffle: "Shuffle", figureName: "Name of the figure", clearAll: "Remove all chapters",
      c_name: "Name of the figure", c_live: "Live mode: the newest chapter plays first",
      liveChip: "live",
      clearAsk1: "Really remove all {n} chapters of this figure?", clearYes1: "Yes, remove all",
      clearAsk2: "The cloud keeps no copy of your audio files: once saved, they are gone from it for good. Make sure you still have them somewhere else.",
      clearYes2: "I have them elsewhere, remove all", clearNo: "Keep them",
      shuffleSwap: "Shuffle when another figure replaces it", shuffleSwapHint: "On a Toniebox 2: once another figure is placed after it, the chapters get a new order. Taking it off and putting it back keeps where it was. Every shuffle makes the cloud convert the figure anew.",
      shuffleFailed: "Saving failed: {e}",
      figSettings: "Settings of the figure", boxSettingsOf: "Settings of the box", dlgClose: "Close",
      tuneOf: "Tune of the figure", renameFailed: "Saving failed: {e}",
      errConnection: "Home Assistant cannot be reached right now. Check the connection and try again.",
      errUnknown: "Something went wrong. Try again; if it keeps happening, the log of Home Assistant tells more.",
      err_cloud_error: "The Tonie cloud did not answer or refused the request. Try again in a moment.",
      err_unauthorized: "Only administrators of Home Assistant can do this.",
      err_unknown_command: "Storybox Plus is not ready yet, for example while Home Assistant starts. Try again in a moment.",
      err_unknown_entry: "The account is not loaded. Look at the integration in the settings of Home Assistant.",
      err_unloaded: "Storybox Plus was reloaded meanwhile. Try again.",
      err_unknown_figure: "This figure is no longer in the account. Refresh the page.",
      err_unknown_box: "This box is no longer in the account. Refresh the page.",
      err_unknown_household: "This household is no longer in the account. Refresh the page.",
      err_unknown_chapter: "The chapters changed meanwhile. Refresh the page and try again.",
      err_unknown_schedule: "This bedtime is gone meanwhile. Refresh the page.",
      err_unknown_file: "The file is gone; upload it again.", err_empty_file: "The file is empty.",
      err_not_creative: "Only creative figures take own chapters.",
      err_not_lockable: "Only bought figures and discs can be locked.",
      err_unknown_tune: "The account has no such Tune.", err_unsuitable_tune: "This Tune does not fit the figure.",
      err_no_tune: "No Tune lies on this figure.",
      err_fetcher_missing: "Links need the Media Fetcher app; it is not installed or not running.",
      err_fetcher_unavailable: "The Media Fetcher app does not answer. Check that it is running.",
      err_invalid_url: "That is no web link. Paste the whole link, starting with https://.",
      err_too_long: "The video is longer than the time still free on the figure.",
      err_too_large: "The file is larger than the figure can hold.",
      err_speech_missing: "Text needs a Piper voice in Home Assistant (Wyoming integration).",
      err_speech_failed: "Piper could not speak the text. Check the Piper app.",
      err_alarm_due: "A bedtime's alarm is set; a sleep timer would cancel it.",
      err_nothing_plays: "No figure is on the box.", err_not_supported: "This box does not have that setting.",
      err_invalid_value: "A Toniebox 1 takes 25, 50, 75 or 100 percent.",
      err_no_alarm: "This box has no bedtimes.",
      figVolume: "Volume of this figure", figVolumeBox: "As set on the box", figVolumeChip: "volume {v} / 13",
      figVolumeHint: "On a Toniebox 2 the figure plays at this level; taken off or replaced, the box gets its level from before back.",
      figVolumeFailed: "Saving the volume failed: {e}",
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
      total: "Listening time", top: "Most played", topPlaced: "Placed most often", placedTimes: "{n}×", perDay: "Per day", perWeek: "Per week", perBox: "Per box",
      weekOf: "Week of {d}", allBoxes: "All boxes", vsBefore: "{p} compared with the {n} days before",
      topChapters: "Most played chapters", whenListened: "When it is listened to",
      whenHint: "Summed over the period, per weekday and hour of the day; no single plays are kept.",
      noteLocalTitle: "Counted locally",
      noteLocal: "Home Assistant counts the listening time itself, from what a Toniebox 2 reports live. It does not come from the manufacturer's cloud and so cannot be complete: it starts with the setup, the Toniebox 1 is missing, and so is anything played while Home Assistant was not running.",
      disabled: "Counting is switched off on the settings tab.", noStats: "Nothing was counted yet.",
      bedtimes: "Bedtimes", addSchedule: "Add", scheduleNew: "New bedtime", scheduleUnnamed: "Bedtime",
      noSchedules: "No bedtime yet. A bedtime with an alarm wakes the child on the chosen days.",
      schedulesUnknown: "The bedtimes could not be read yet.",
      everyDay: "every day", alarmOn: "Alarm", scheduleOn: "Bedtime active",
      nextAlarm: "Next alarm {t}", alarmArmed: "set on the box", alarmPending: "set as soon as the box is online",
      alarmLater: "set the evening before",
      alarmHint: "Home Assistant sets the alarm on the box every evening, as soon as the box is online; the app sets it only once. While an alarm is due, the sleep timer actions and switching the box off are refused, because the box keeps only one timer.",
      f_name: "Name", f_days: "Days of the wake-up", f_sleep_time: "Bedtime", f_wakeup_time: "Wake-up",
      f_enabled: "Active", f_alarm_enabled: "Alarm at the wake-up", f_alarm_volume: "Alarm volume", f_alarm_morning_light: "Morning light",
      deleteSchedule: "Delete", deleteConfirm: "Really delete", scheduleFailed: "Saving the bedtime failed: {e}",
      headphones: "Headphones", headphonesBattery: "Headphones {p} %",
      ctlPrev: "Previous chapter", ctlNext: "Next chapter", ctlPlay: "Play", ctlPause: "Pause", ctlLouder: "Louder", ctlQuieter: "Quieter",
      ctlSleep: "Sleep timer {m} min", ctlSleepTitle: "Sleep timer", sleepMin: "{m} min", batteryDetails: "Battery and charge history", ctlSleepOff: "Cancel the sleep timer", ctlFailed: "The box did not get the command: {e}",
      boxSettings: "Settings", settingsPending: "waiting for the box", offlineMode: "offline mode",
      settingsFailed: "Saving the settings failed: {e}", noSettings: "The cloud names no settings of this box.",
      settingsHint: "The box takes the settings the next time it is online.",
      s_name: "Name", s_max_volume: "Maximum volume", s_max_headphone_volume: "Maximum headphone volume",
      s_lightring_brightness: "Light ring brightness", s_bedtime_lightring_brightness: "Light ring at bedtime",
      s_bedtime_max_volume: "Maximum volume at bedtime", s_bedtime_max_headphone_volume: "Maximum headphone volume at bedtime",
      s_skipping_enabled: "Skip chapters by tapping", s_skipping_direction: "Ear that skips forward",
      s_scrubbing_enabled: "Wind by tilting", s_accelerometer_enabled: "Tilt and tap",
      s_tap_direction: "Tap direction", s_led_level: "LED", s_age_mode: "Age mode", s_language: "Language",
      v_left: "Left", v_right: "Right", v_on: "On", v_off: "Off", v_dimmed: "Dimmed",
      sumVolume: "max. {v} %", volumeLevel: "level {v} of {max}", sumRing: "light ring {v} %", sumSkip: "skipping on", sumLed: "LED {v}",
      sumPhones: "headphones {v} %", sumTilt: "winding by tilting",
      nightMode: "Night mode of the light ring", nightSetup: "Set up night mode", nightNow: "night now", dayNow: "day now",
      nightSummary: "{start} – {end}: {night} %, otherwise {day} %",
      nightHint: "Home Assistant dims the light ring at the start and sets it back at the end; a brightness set in the app in between stays until the next change. The box takes it the next time it is online.",
      nightFailed: "Saving the night mode failed: {e}",
      n_enabled: "Active", n_start: "From", n_end: "Until", n_night: "Light ring at night", n_day: "Light ring otherwise",
    },
    de: {
      tabBoxes: "Boxen", tabFigures: "Figuren", tabListening: "Hörzeit", tabPreferences: "Einstellungen",
      prefVoucher: "Tunes-Gutschein", voucherCode: "Gutscheincode", voucherRedeem: "Einlösen",
      voucherDone: "Eingelöst: {n} Tunes hinzugefügt.", voucherNone: "Eingelöst, die Cloud nennt aber keinen neuen Tune.", voucherFailed: "Einlösen fehlgeschlagen: {e}",
      voucherHint: "Ein Gutschein lässt sich einmal einlösen; die Tunes erscheinen danach bei den Figuren, zu denen sie passen.",
      fromText: "Aus Text", textTitle: "Titel (optional)", textBody: "Text zum Vorlesen",
      textHint: "Piper, die lokale Stimme von Home Assistant, spricht den Text; die Aufnahme wird ein Kapitel. Der Text bleibt im Haus.",
      speechMissing: "Dafür wird eine Piper-Stimme in Home Assistant gebraucht: die Wyoming-Integration mit Piper einrichten.",
      textBusy: "Piper spricht den Text, er geht in die Cloud …", textFailed: "Hinzufügen aus Text fehlgeschlagen: {e}",
      fromCode: "Per Code", codePlaceholder: "Inhaltscode", codeHint: "Fertige Inhalte zu einem Code (etwa von einer Karte) kommen auf die Figur; die Cloud wandelt sie danach um.",
      codeFailed: "Hinzufügen per Code fehlgeschlagen: {e}",
      prefHousehold: "Haushalt", householdName: "Name des Haushalts", householdSaved: "Gespeichert", householdFailed: "Umbenennen fehlgeschlagen: {e}",
      members: "Mitglieder", membersUnknown: "Die Mitglieder konnten noch nicht gelesen werden.", memberYou: "Du",
      role_owner: "Besitzer", role_full: "Voller Zugriff", role_limited: "Eingeschränkter Zugriff", role_unknown: "Unbekannte Rolle",
      membersHint: "So, wie die Cloud sie diesem Konto zeigt; Mitglieder und Einladungen werden in der App verwaltet.",
      prefListening: "Hörzeit", prefAnalytics: "Hörzeit zählen",
      prefAnalyticsHint: "Speichert Summen je Tag, Figur, Box, Kapitel und Stunde für den Hörzeit-Tab, nie einzelne Wiedergaben. Ausgeschaltet werden die Summen gelöscht.",
      prefFigures: "Figuren", prefAutoLock: "Neue Figuren und Discs für den Haushalt sperren",
      prefAutoLockHint: "Eine gekaufte Figur oder Disc, die neu im Konto ist, wird einmal gesperrt, damit sie nicht in einen anderen Haushalt übernommen werden kann. Auf ihrer Seite oder in der App entsperrt, bleibt sie entsperrt.",
      prefNotices: "Benachrichtigungen", prefMarkRead: "Benachrichtigungen nach dem Weiterreichen in der Cloud als gelesen markieren",
      prefMarkReadHint: "Die App zeigt sie dann nicht mehr. Rundrufe an alle Nutzer werden stattdessen geschlossen.",
      prefCloud: "Cloud", cloudVersion: "Backend-Version {v}", cloudTested: "getestet", cloudUntested: "getestet mit {t}",
      cloudUnknown: "Die Version der Cloud ist noch nicht bekannt.",
      cloudDiffers: "Die Cloud läuft mit Release {v}; Storybox Plus wurde mit {t} getestet. Funktioniert etwas nicht, hat sich vielleicht die Schnittstelle der Cloud geändert.",
      prefFailed: "Einstellungen speichern fehlgeschlagen: {e}",
      lockSwitch: "Für den Haushalt gesperrt", lockHint: "Eine gesperrte Figur kann nicht in einen anderen Haushalt übernommen werden.",
      lockFailed: "Sperre ändern fehlgeschlagen: {e}",
      tune: "Tune", tuneOn: "Tune darauf: {t}", tuneRemove: "Tune abnehmen", tunePick: "Gekaufter Tune", tuneAssign: "Auflegen",
      tuneLeft: "noch {n}-mal", tuneHintCreative: "Die Kapitel der Figur bleiben erhalten und spielen wieder, sobald der Tune abgenommen wird.",
      tuneHint: "Die Figur spielt den Tune statt ihrer eigenen Geschichte, bis er abgenommen wird.", tuneFailed: "Tune ändern fehlgeschlagen: {e}",
      refresh: "Aktualisieren", settings: "Einstellungen", asOf: "Stand {t}", retry: "Erneut versuchen", loading: "Lädt …",
      about: "Storybox Plus {version}", aboutCommit: "Storybox Plus {version} · Commit {commit}",
      failed: "Die Daten ließen sich nicht lesen",
      noEntry: "Kein Konto eingerichtet. Unter Einstellungen → Geräte & Dienste hinzufügen.",
      notLoaded: "Gerade ist kein Konto geladen. Home Assistant versucht es selbst erneut.",
      pushDown: "Live-Kanal nicht verbunden – Zustände können veraltet sein",
      noBoxes: "Noch keine Box in diesem Konto.", toniebox2: "Toniebox 2", classic: "Toniebox 1",
      online: "Online", offline: "Offline", unknown: "Unbekannt", charging: "lädt",
      sleepUntil: "Schlaf-Timer bis {t}", sleepOn: "Schlaf-Timer aktiv", firmware: "Firmware",
      classicNote: "Eine Toniebox 1 meldet keine Live-Daten.", lastSeen: "Zuletzt gesehen {t}", never: "nie",
      battery: "Akku", perFull: "etwa {h} h pro Ladung", perFullProjected: "voraussichtlich etwa {h} h pro Ladung",
      remaining: "reicht noch etwa {h}", charge1: "1 Ladung", chargesN: "{n} Ladungen", nowSince: "jetzt {t} seit {p} %", noCycles: "noch kein Entladezyklus erfasst",
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
      moveUp: "Nach oben", moveDown: "Nach unten", remove: "Entfernen", renameChapter: "Umbenennen", chapterName: "Name des Kapitels", apply: "Übernehmen",
      sortTitle: "A–Z sortieren", shuffle: "Mischen", figureName: "Name der Figur", clearAll: "Alle Kapitel entfernen",
      c_name: "Name der Figur", c_live: "Live-Modus: das neueste Kapitel spielt zuerst",
      liveChip: "live",
      clearAsk1: "Wirklich alle {n} Kapitel dieser Figur entfernen?", clearYes1: "Ja, alle entfernen",
      clearAsk2: "Die Toniecloud behält keine Kopie deiner Audiodateien: Nach dem Speichern sind sie dort endgültig weg. Stell sicher, dass du sie noch anderswo hast.",
      clearYes2: "Ich habe sie anderswo, alle entfernen", clearNo: "Behalten",
      shuffleSwap: "Neu mischen, wenn eine andere Figur sie ersetzt", shuffleSwapHint: "Auf einer Toniebox 2: Sobald danach eine andere Figur aufgestellt wird, bekommen die Kapitel eine neue Reihenfolge. Abnehmen und wieder aufstellen behält die Stelle. Jedes Mischen lässt die Cloud die Figur neu umwandeln.",
      shuffleFailed: "Speichern fehlgeschlagen: {e}",
      figSettings: "Einstellungen der Figur", boxSettingsOf: "Einstellungen der Box", dlgClose: "Schließen",
      tuneOf: "Tune der Figur", renameFailed: "Speichern fehlgeschlagen: {e}",
      errConnection: "Home Assistant ist gerade nicht erreichbar. Bitte Verbindung prüfen und noch einmal versuchen.",
      errUnknown: "Da ist etwas schiefgegangen. Bitte noch einmal versuchen; bleibt es dabei, steht mehr im Protokoll von Home Assistant.",
      err_cloud_error: "Die Tonie-Cloud hat nicht geantwortet oder die Anfrage abgelehnt. Bitte gleich noch einmal versuchen.",
      err_unauthorized: "Das dürfen nur Administratoren von Home Assistant.",
      err_unknown_command: "Storybox Plus ist noch nicht bereit, etwa während Home Assistant startet. Bitte gleich noch einmal versuchen.",
      err_unknown_entry: "Das Konto ist nicht geladen. Bitte die Integration in den Einstellungen von Home Assistant ansehen.",
      err_unloaded: "Storybox Plus wurde zwischendurch neu geladen. Bitte noch einmal versuchen.",
      err_unknown_figure: "Diese Figur ist nicht mehr im Konto. Bitte die Seite aktualisieren.",
      err_unknown_box: "Diese Box ist nicht mehr im Konto. Bitte die Seite aktualisieren.",
      err_unknown_household: "Diesen Haushalt gibt es im Konto nicht mehr. Bitte die Seite aktualisieren.",
      err_unknown_chapter: "Die Kapitel haben sich zwischendurch geändert. Bitte die Seite aktualisieren und noch einmal versuchen.",
      err_unknown_schedule: "Diese Schlafenszeit gibt es nicht mehr. Bitte die Seite aktualisieren.",
      err_unknown_file: "Die Datei ist weg; bitte noch einmal hochladen.", err_empty_file: "Die Datei ist leer.",
      err_not_creative: "Nur Kreativ-Tonies nehmen eigene Kapitel.",
      err_not_lockable: "Nur gekaufte Figuren und Discs lassen sich sperren.",
      err_unknown_tune: "Diesen Tune hat das Konto nicht.", err_unsuitable_tune: "Dieser Tune passt nicht auf die Figur.",
      err_no_tune: "Auf dieser Figur liegt kein Tune.",
      err_fetcher_missing: "Links brauchen die App Media Fetcher; sie ist nicht installiert oder läuft nicht.",
      err_fetcher_unavailable: "Die App Media Fetcher antwortet nicht. Bitte prüfen, ob sie läuft.",
      err_invalid_url: "Das ist kein Weblink. Bitte den ganzen Link einfügen, beginnend mit https://.",
      err_too_long: "Das Video ist länger als die Zeit, die auf der Figur noch frei ist.",
      err_too_large: "Die Datei ist größer, als die Figur aufnehmen kann.",
      err_speech_missing: "Texte brauchen eine Piper-Stimme in Home Assistant (Wyoming-Integration).",
      err_speech_failed: "Piper konnte den Text nicht sprechen. Bitte die Piper-App prüfen.",
      err_alarm_due: "Ein Wecker einer Schlafenszeit ist gestellt; ein Schlaf-Timer würde ihn löschen.",
      err_nothing_plays: "Auf der Box steht keine Figur.", err_not_supported: "Diese Einstellung hat die Box nicht.",
      err_invalid_value: "Eine Toniebox 1 nimmt 25, 50, 75 oder 100 Prozent.",
      err_no_alarm: "Diese Box hat keine Schlafenszeiten.",
      figVolume: "Lautstärke dieser Figur", figVolumeBox: "Wie an der Box eingestellt", figVolumeChip: "Lautstärke {v} / 13",
      figVolumeHint: "Auf einer Toniebox 2 spielt die Figur mit dieser Stufe; abgenommen oder ersetzt, bekommt die Box ihre Stufe von vorher zurück.",
      figVolumeFailed: "Lautstärke speichern fehlgeschlagen: {e}",
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
      total: "Hörzeit", top: "Meistgehört", topPlaced: "Am häufigsten aufgelegt", placedTimes: "{n}×", perDay: "Pro Tag", perWeek: "Pro Woche", perBox: "Pro Box",
      weekOf: "Woche vom {d}", allBoxes: "Alle Boxen", vsBefore: "{p} gegenüber den {n} Tagen davor",
      topChapters: "Meistgehörte Kapitel", whenListened: "Wann gehört wird",
      whenHint: "Über den Zeitraum summiert, je Wochentag und Stunde; einzelne Wiedergaben werden nicht gespeichert.",
      noteLocalTitle: "Lokal mitgezählt",
      noteLocal: "Home Assistant zählt die Hörzeit selbst mit, aus dem, was eine Toniebox 2 live meldet. Sie stammt nicht aus der Hersteller-Cloud und ist deshalb nicht vollständig: Sie beginnt mit der Einrichtung, die Toniebox 1 fehlt, und Zeiten, in denen Home Assistant nicht lief, fehlen ebenso.",
      disabled: "Das Zählen ist im Einstellungen-Tab ausgeschaltet.", noStats: "Noch nichts gezählt.",
      bedtimes: "Schlafenszeiten", addSchedule: "Hinzufügen", scheduleNew: "Neue Schlafenszeit", scheduleUnnamed: "Schlafenszeit",
      noSchedules: "Noch keine Schlafenszeit. Eine Schlafenszeit mit Wecker weckt das Kind an den gewählten Tagen.",
      schedulesUnknown: "Die Schlafenszeiten ließen sich noch nicht lesen.",
      everyDay: "täglich", alarmOn: "Wecker", scheduleOn: "Schlafenszeit aktiv",
      nextAlarm: "Nächster Wecker {t}", alarmArmed: "auf der Box gestellt", alarmPending: "wird gestellt, sobald die Box online ist",
      alarmLater: "wird am Vorabend gestellt",
      alarmHint: "Home Assistant stellt den Wecker jeden Abend auf der Box, sobald sie online ist; die App stellt ihn nur einmal. Solange ein Wecker ansteht, lehnt die Integration den Schlaf-Timer und das Ausschalten der Box ab, weil die Box nur einen Timer kennt.",
      f_name: "Name", f_days: "Tage des Weckens", f_sleep_time: "Schlafenszeit", f_wakeup_time: "Wecken",
      f_enabled: "Aktiv", f_alarm_enabled: "Wecker beim Wecken", f_alarm_volume: "Lautstärke des Weckers", f_alarm_morning_light: "Morgenlicht",
      deleteSchedule: "Löschen", deleteConfirm: "Wirklich löschen", scheduleFailed: "Schlafenszeit speichern fehlgeschlagen: {e}",
      headphones: "Kopfhörer", headphonesBattery: "Kopfhörer {p} %",
      ctlPrev: "Vorheriges Kapitel", ctlNext: "Nächstes Kapitel", ctlPlay: "Abspielen", ctlPause: "Pausieren", ctlLouder: "Lauter", ctlQuieter: "Leiser",
      ctlSleep: "Schlaf-Timer {m} Min.", ctlSleepTitle: "Schlaf-Timer", sleepMin: "{m} Min.", batteryDetails: "Akku und Ladungsverlauf", ctlSleepOff: "Schlaf-Timer abbrechen", ctlFailed: "Die Box hat den Befehl nicht bekommen: {e}",
      boxSettings: "Einstellungen", settingsPending: "wartet auf die Box", offlineMode: "Offline-Modus",
      settingsFailed: "Einstellungen speichern fehlgeschlagen: {e}", noSettings: "Die Cloud nennt keine Einstellungen dieser Box.",
      settingsHint: "Die Box übernimmt die Einstellungen, sobald sie das nächste Mal online ist.",
      s_name: "Name", s_max_volume: "Maximale Lautstärke", s_max_headphone_volume: "Maximale Kopfhörer-Lautstärke",
      s_lightring_brightness: "Helligkeit des Lichtrings", s_bedtime_lightring_brightness: "Lichtring in der Schlafenszeit",
      s_bedtime_max_volume: "Maximale Lautstärke in der Schlafenszeit", s_bedtime_max_headphone_volume: "Maximale Kopfhörer-Lautstärke in der Schlafenszeit",
      s_skipping_enabled: "Kapitel per Klopfen überspringen", s_skipping_direction: "Ohr für vorwärts",
      s_scrubbing_enabled: "Spulen per Kippen", s_accelerometer_enabled: "Kippen und Klopfen",
      s_tap_direction: "Klopfrichtung", s_led_level: "LED", s_age_mode: "Altersmodus", s_language: "Sprache",
      v_left: "Links", v_right: "Rechts", v_on: "An", v_off: "Aus", v_dimmed: "Gedimmt",
      sumVolume: "max. {v} %", volumeLevel: "Stufe {v} von {max}", sumRing: "Lichtring {v} %", sumSkip: "Überspringen an", sumLed: "LED {v}",
      sumPhones: "Kopfhörer {v} %", sumTilt: "Spulen durch Kippen",
      nightMode: "Nachtmodus des Lichtrings", nightSetup: "Nachtmodus einrichten", nightNow: "gerade Nacht", dayNow: "gerade Tag",
      nightSummary: "{start} – {end}: {night} %, sonst {day} %",
      nightHint: "Home Assistant dimmt den Lichtring zu Beginn und stellt ihn am Ende zurück; eine Helligkeit, die zwischendurch in der App gesetzt wird, bleibt bis zum nächsten Wechsel. Die Box übernimmt es, sobald sie online ist.",
      nightFailed: "Nachtmodus speichern fehlgeschlagen: {e}",
      n_enabled: "Aktiv", n_start: "Von", n_end: "Bis", n_night: "Lichtring nachts", n_day: "Lichtring sonst",
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
  const WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];
  // "HH:MM" from Home Assistant's time field, which adds seconds
  const clock = (v) => (typeof v === "string" && /^\d{1,2}:\d{2}/.test(v) ? v.split(":").slice(0, 2).map((x) => x.padStart(2, "0")).join(":") : null);
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
        if (e.key === "Escape" && this._overlayHtml) {
          e.preventDefault();
          this._closeOverlay();
          return;
        }
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
      const many = households.size > 1;
      // A Toniebox 1 reports nothing live: it gets a small card of its own, after the Toniebox 2
      const live = o.boxes.filter((b) => b.generation === "toniebox_2");
      const rest = o.boxes.filter((b) => b.generation !== "toniebox_2");
      return html + `<div class="grid">${live.map((b) => this._box(b, many)).join("")}${rest.map((b) => this._miniBox(b, many)).join("")}</div>`;
    }

    // Online or offline as a small dot, the word in its tooltip
    _dot(b) {
      const t = this._t;
      const [state, label] = b.online === true ? ["ok", t.online] : b.online === false ? ["err", t.offline] : ["", t.unknown];
      const seen = b.online !== true && b.last_seen ? ` · ${fill(t.lastSeen, { t: this._relative(b.last_seen) })}` : "";
      return `<span class="dot ${state}" role="img" title="${esc(label + seen)}" aria-label="${esc(label + seen)}"></span>`;
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

    _box(b, showHousehold) {
      const t = this._t;
      const live = b.generation === "toniebox_2";
      const chips = showHousehold && b.household ? this._chip(b.household) : "";
      const pic = safeUrl(b.image_url);
      // Settings, night mode and bedtimes sit behind the box's cog
      const cog = b.settings || b.bedtime ? iconButton("cog", t.boxSettingsOf, `class="box-cog" data-act="boxset:${esc(b.id)}"`) : "";
      // The battery's level sits in the head; the rest of the battery opens in the overlay
      const batt = live && b.battery_stats
        ? `<button class="fact fact-btn" data-act="battset:${esc(b.id)}" title="${esc(t.batteryDetails)}" aria-label="${esc(t.batteryDetails)}">${this._batteryLevel(b)}</button>`
        : "";
      const title = `${pic ? `<img class="box-pic" src="${esc(pic)}" alt="">` : ""}<span class="box-name">${esc(b.name || b.id)}</span>${this._dot(b)}` +
        `<span class="chips">${chips}</span><span class="status">${batt}</span>${cog}`;
      const facts = [];
      if (Number.isFinite(b.volume)) {
        // The box's own percent once it reported the level; a level just sent shows as a level
        const sent = this._volSent?.box === b.id;
        const shown = Number.isFinite(b.volume_percent) && !sent ? `${b.volume_percent} %` : fill(t.volumeLevel, { v: b.volume, max: b.volume_max ?? 13 });
        facts.push(`<span class="fact${sent ? " pending" : ""}" title="${esc(fill(t.volumeLevel, { v: b.volume, max: b.volume_max ?? 13 }))}">${icon("volume")}${esc(shown)}</span>`);
      }
      if (b.headphones?.connected) {
        const hp = Number.isFinite(b.headphones.battery) ? fill(t.headphonesBattery, { p: b.headphones.battery }) : t.headphones;
        facts.push(`<span class="fact">${icon("headphones")}${esc(hp)}</span>`);
      }
      const sleep = this._sleep(b.sleep_timer);
      if (sleep) facts.push(`<span class="fact">${icon("sleep")}${esc(sleep)}</span>`);
      // The next alarm and a night mode at work stay on the card; the rest is behind the cog
      const next = b.bedtime?.next_alarm;
      if (next) {
        const when = new Date(time(next.at)).toLocaleString(this._lang, { weekday: "short", hour: "2-digit", minute: "2-digit" });
        facts.push(`<span class="fact">${icon("alarm")}${esc(fill(t.nextAlarm, { t: when }))}</span>`);
      }
      if (b.night?.mode?.enabled && b.night.phase === "night") facts.push(this._chip(t.nightMode, "on"));
      let body = facts.length ? `<div class="facts">${facts.join("")}</div>` : "";
      if (live) body += this._playback(b.playback) + this._controls(b);
      else body += `<div class="muted">${esc(t.classicNote)}</div>`;
      const notes = [];
      if (!live && b.last_seen) notes.push(fill(t.lastSeen, { t: this._relative(b.last_seen) }));
      if (notes.length) body += `<div class="muted small">${esc(notes.join(" · "))}</div>`;
      // The battery is a section of its own at the bottom of the card
      return this._card(title, body);
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

    // Play, pause, chapters, volume and the sleep timer of a Toniebox 2 that is online
    _controls(b) {
      const t = this._t;
      if (b.online !== true) return "";
      const p = b.playback;
      const placed = !!p?.tonie_id;
      const vol = Number.isFinite(b.volume) ? b.volume : null;
      const max = b.volume_max ?? 13;
      const busy = this._ctlBusy === b.id;
      const alarm = b.bedtime?.next_alarm?.due;
      const timerOn = !!this._sleep(b.sleep_timer);
      const btn = (cmd, ic, label, disabled, value = "") =>
        iconButton(ic, label, `data-act="ctl:${esc(b.id)}:${cmd}${value !== "" ? `:${value}` : ""}"${disabled || busy ? " disabled" : ""}`);
      let html = `<div class="controls">` +
        btn("previous", "prev", t.ctlPrev, !placed) +
        (p?.playing ? btn("pause", "pause", t.ctlPause, !placed) : btn("play", "play", t.ctlPlay, !placed)) +
        btn("next", "next", t.ctlNext, !placed) + `<span class="ctl-gap"></span>` +
        btn("volume", "minus", t.ctlQuieter, vol === null || vol <= 0, vol === null ? "" : vol - 1) +
        btn("volume", "plus", t.ctlLouder, vol === null || vol >= max, vol === null ? "" : vol + 1) +
        `<span class="ctl-gap"></span>`;
      // The alarm of a bedtime uses the same timer; the timer stays out of its way
      if (!alarm) {
        html += timerOn
          ? btn("sleep_clear", "sleepOff", t.ctlSleepOff, false)
          : `<span class="sleep-pick" title="${esc(t.ctlSleepTitle)}">${icon("sleep")}` + [30, 60].map((m) =>
            `<button class="chip pick" data-act="ctl:${esc(b.id)}:sleep:${m}" aria-label="${esc(fill(t.ctlSleep, { m }))}"${busy ? " disabled" : ""}>` +
            `${esc(fill(t.sleepMin, { m }))}</button>`).join("") + `</span>`;
      }
      html += `</div>`;
      if (this._ctlError?.id === b.id) html += this._alert(fill(t.ctlFailed, { e: this._ctlError.message }), "error");
      return html;
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

    // The timer counts as set unless its state says otherwise; a timer that ends
    // with an alarm is the bedtime's, shown there
    _sleep(timer) {
      if (!timer?.state || timer.alarm || /^(off|inactive|disabled|stopped|finished|none|idle)$/i.test(timer.state)) return null;
      const until = time(timer.until);
      if (!Number.isFinite(until)) return this._t.sleepOn;
      return fill(this._t.sleepUntil, { t: new Date(until).toLocaleTimeString(this._lang, { hour: "2-digit", minute: "2-digit" }) });
    }

    // The battery tile: the level, how long a charge lasts and, behind a fold, the
    // completed discharges. The numbers are the backend's; here they are only formatted.
    // The level with its little battery; nothing is known while the box is switched off
    _batteryLevel(b) {
      const t = this._t;
      if (!Number.isFinite(b.battery)) return `<span class="batt"><i style="height:0"></i></span>–`;
      const low = b.battery < 20 && !b.charging;
      return `<span class="batt${low ? " low" : ""}"><i style="height:${Math.max(0, Math.min(100, b.battery))}%"></i></span>` +
        `${b.battery} %${b.charging ? `<span class="charge">${icon("flash")}${esc(t.charging)}</span>` : ""}`;
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
        this._btn(`edit:${f.id}`, t.edit, "pencil", { disabled: busy }) + `</div>`;
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
  .card-header .dot { margin-left: 4px; }
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
  .clear-ask { margin: 4px 0 8px; }
  .clear-ask .ch-bar { margin-top: 8px; }
  .tune-row { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 16px; margin: 4px 0 8px; }
  .tune-row ha-form { flex: 0 1 320px; display: block; }
  .tune-row .hint { flex: 1 1 240px; margin: 0; }
  .vol-row { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 16px; margin: 4px 0 8px; }
  .vol-row ha-form { flex: 0 1 280px; display: block; }
  .vol-row .hint { flex: 1 1 240px; margin: 0; }
  .link-form ha-form { display: block; margin-bottom: 8px; }
  .switch-row { display: flex; align-items: center; gap: 12px; margin: 2px 0 8px; }
  .grow { flex: 1; }
  .compare { margin-top: 8px; }
  .heat-boxes { margin-bottom: 10px; }
  .heatmap { display: grid; grid-template-columns: auto repeat(24, minmax(0, 1fr)); gap: 2px; align-items: center; }
  .hm-day { font-size: var(--ha-font-size-xs, 12px); color: var(--secondary-text-color); padding-right: 6px; }
  .hm-cell { aspect-ratio: 1; border-radius: 2px; min-height: 8px;
    background: color-mix(in srgb, var(--primary-color) calc(var(--a) * 100%), color-mix(in srgb, var(--primary-text-color) 6%, transparent)); }
  .hm-hour { font-size: var(--ha-font-size-xs, 11px); color: var(--secondary-text-color); }
  .controls { display: flex; flex-wrap: wrap; align-items: center; gap: 2px; margin: 8px 0 4px; }
  .ctl-gap { width: 12px; }
  .sleep-pick { display: inline-flex; align-items: center; gap: 6px; margin-left: 4px; color: var(--secondary-text-color); }
  .sleep-pick .chip.pick { line-height: 28px; padding: 0 12px; background: color-mix(in srgb, var(--primary-text-color) 8%, transparent); color: var(--primary-text-color); }
  .sleep-pick .chip.pick[disabled] { opacity: 0.5; cursor: default; }
  .fact.pending { opacity: .6; }
  .fact-btn { border: 0; background: none; color: inherit; font: inherit; padding: 2px 8px; margin: -2px -8px; border-radius: 12px; cursor: pointer; }
  .fact-btn:hover, .fact-btn:focus-visible { background: color-mix(in srgb, var(--primary-text-color) 8%, transparent); outline: none; }
  .batt-level { font-size: var(--ha-font-size-2xl, 24px); margin: 0 0 6px; }
  .ov-foot { margin-top: 12px; }
  .batt-view .pref-head { margin-top: 16px; }
  .box-pic { width: 40px; height: 40px; object-fit: contain; flex: none; margin-right: 4px; }
  .box-pic.broken { display: none; }
  .box-pic.small { width: 32px; height: 32px; margin-right: 0; }
  .mini-box { padding: 16px; align-self: start; }
  .mini-head { display: flex; align-items: center; gap: 12px; }
  .mini-text { flex: 1 1 auto; min-width: 0; display: flex; flex-direction: column; }
  .mini-title { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 8px; }
  .mini-title .box-name { font-size: var(--ha-font-size-l, 16px); }
  .mini-text .supporting { white-space: normal; }
  .box-cog { margin: -6px -8px -6px 0; }
  .fig-head .fig-cog { margin: -6px 0; }
  .name-row { display: flex; align-items: center; gap: 12px; margin-bottom: 4px; }
  .name-row ha-form { flex: 1 1 auto; display: block; }
  .ov-body .name-row ha-form { margin-bottom: 0; }
  .ov { position: fixed; inset: 0; z-index: 8; display: flex; align-items: center; justify-content: center; padding: 24px; }
  .ov-back { position: absolute; inset: 0; background: rgba(0, 0, 0, 0.45); }
  .ov-card { position: relative; width: min(640px, 100%); max-height: calc(100dvh - 48px); overflow: auto; outline: none;
    background: var(--ha-card-background, var(--card-background-color, #fff)); color: var(--primary-text-color);
    border-radius: var(--ha-dialog-border-radius, 24px); box-shadow: 0 12px 32px rgba(0, 0, 0, 0.35); padding: 12px 24px 24px; }
  .ov-head { display: flex; align-items: flex-start; gap: 8px; margin: 4px -12px 12px 0; position: sticky; top: -12px;
    background: inherit; padding-top: 8px; z-index: 1; }
  .ov-titles { flex: 1 1 auto; min-width: 0; display: flex; flex-direction: column; }
  .ov-title { font-size: var(--ha-font-size-xl, 22px); line-height: 28px; }
  .ov-body ha-form { display: block; margin-bottom: 8px; }
  .ov-body .tile { padding: 12px 0 14px; background: none; }
  .ov-body .tile:first-child { border-top: 0; padding-top: 0; }
  .ov-body .vol-row, .ov-body .tune-row { display: block; }
  .ov-body .vol-row .hint, .ov-body .tune-row .hint { display: block; margin: 0 0 8px; }
  .ov-body .switch-row { margin: 12px 0; }
  .ov-actions { display: flex; justify-content: flex-end; flex-wrap: wrap; gap: 8px; margin-top: 16px; }
  @media (max-width: 600px) {
    .ov { align-items: flex-end; padding: 0; }
    .ov-card { width: 100%; max-height: 92dvh; border-radius: 24px 24px 0 0; padding: 8px 16px 24px; }
  }
  .pref-head { font-weight: var(--ha-font-weight-medium, 500); margin: 12px 0 4px; }
  .pref-head:first-child { margin-top: 0; }
  .household-row { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 12px; }
  .household-row ha-form { flex: 1 1 260px; display: block; }
  .members { margin: 4px 0 12px; }
  .members-head { font-size: var(--ha-font-size-s, 13px); color: var(--secondary-text-color); margin: 8px 0 4px; }
  .member { display: flex; align-items: center; gap: 12px; padding: 6px 0; border-bottom: 1px solid var(--divider-color); }
  .member:last-of-type { border-bottom: 0; }
  .member .text { flex: 1 1 auto; min-width: 0; display: flex; flex-direction: column; }
  .member .text .supporting { overflow: hidden; text-overflow: ellipsis; }
  .member-avatar { flex: none; width: 32px; height: 32px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center;
    font-weight: 500; background: color-mix(in srgb, var(--primary-color) 16%, transparent); color: var(--primary-color); }
  .member-avatar.owner { background: color-mix(in srgb, var(--success-color) 18%, transparent); color: var(--success-color); }
  .pref-cloud { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 10px; }
  .night-row { margin-top: 8px; }
  .tile-head .chip { margin-left: 4px; }
  .alarm-next { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 10px; margin: 4px 0 6px; }
  .schedules { list-style: none; margin: 0; padding: 0; }
  .schedules li { display: flex; align-items: center; gap: 12px; padding: 6px 0; }
  .schedules li + li { border-top: 1px solid var(--divider-color); }
  .schedules li.editing { display: block; }
  .schedules ha-switch { flex: none; }
  .schedules .text { display: flex; flex-direction: column; flex: 1; min-width: 0; }
  .alarm-mark { display: inline-flex; vertical-align: middle; color: var(--secondary-text-color); }
  .alarm-mark ha-svg-icon { --mdc-icon-size: 16px; }
  .sched-form { padding: 6px 0; }
  .sched-form ha-form { display: block; margin: 6px 0 8px; }
  ha-button.danger-btn.confirm { --ha-button-text-color: var(--error-color); color: var(--error-color); }
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
