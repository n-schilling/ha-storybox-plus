// Storybox Plus: what the page in the sidebar and the dashboard card share, the
// icons, the texts in both languages, small helpers, the style sheet and the
// drawing of a box's card. The page and the card import it with the version of
// their own script, so a browser never mixes an old module with a new page.

export const MDI = {
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

export const TEXTS = {
  en: {
    cardName: "Toniebox", cardDescription: "The live state of a Toniebox 2 with its buttons.", cardEntity: "Toniebox 2 (media player)",
    cardNoEntity: "Choose the media player of a Toniebox 2.", cardUnknown: "This is no Toniebox 2 of Storybox Plus.", cardDenied: "You may not see this Toniebox.",
    cardShow: "Show", show_picture: "Picture of the box", show_battery: "Battery", show_volume: "Volume", show_headphones: "Headphones",
    show_sleep_timer: "Running sleep timer", show_next_alarm: "Next alarm", show_night_mode: "Night mode of the light ring",
    show_playback: "What plays", show_controls: "Buttons",
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
    cardName: "Toniebox", cardDescription: "Der Live-Stand einer Toniebox 2 mit ihren Knöpfen.", cardEntity: "Toniebox 2 (Media Player)",
    cardNoEntity: "Wähle den Media Player einer Toniebox 2.", cardUnknown: "Das ist keine Toniebox 2 von Storybox Plus.", cardDenied: "Diese Toniebox darfst du nicht sehen.",
    cardShow: "Anzeigen", show_picture: "Bild der Box", show_battery: "Akku", show_volume: "Lautstärke", show_headphones: "Kopfhörer",
    show_sleep_timer: "Laufender Schlaf-Timer", show_next_alarm: "Nächster Wecker", show_night_mode: "Nachtmodus des Lichtrings",
    show_playback: "Was gerade läuft", show_controls: "Knöpfe",
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

export const esc = (v) =>
  String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
export const icon = (name) => `<ha-svg-icon path="${MDI[name]}"></ha-svg-icon>`;
export const iconButton = (name, label, attrs = "") =>
  `<ha-icon-button path="${MDI[name]}" label="${esc(label)}"${attrs ? ` ${attrs}` : ""}></ha-icon-button>`;
export const fill = (text, values) => text.replace(/\{(\w+)\}/g, (_, k) => values[k] ?? "");
export const time = (iso) => (iso ? Date.parse(iso) : NaN);
// Only web addresses go into an <img>
export const safeUrl = (u) => (typeof u === "string" && /^https?:\/\//i.test(u) ? u : null);
export const pad = (n) => String(n).padStart(2, "0");
// h:mm for lengths and listening time, m:ss for positions and chapters
export const hm = (s) => {
  if (!Number.isFinite(s) || s < 0) return "–";
  const m = Math.round(s / 60);
  return `${Math.floor(m / 60)}:${pad(m % 60)}`;
};
export const mmss = (s) => {
  if (!Number.isFinite(s) || s < 0) return "–:––";
  const v = Math.floor(s);
  return `${Math.floor(v / 60)}:${pad(v % 60)}`;
};
// Battery hours from the backend, as "h:mm h"; nothing is made of a missing value
export const hours = (h) => (Number.isFinite(h) ? `${hm(h * 3600)} h` : "–");
export const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
// Local calendar days as "YYYY-MM-DD", like the backend's per_day keys
export const dayKey = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
export const parseDay = (key) => {
  const [y, m, d] = String(key).split("-").map(Number);
  return new Date(y, (m || 1) - 1, d || 1);
};
export const WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];
// "HH:MM" from Home Assistant's time field, which adds seconds
export const clock = (v) => (typeof v === "string" && /^\d{1,2}:\d{2}/.test(v) ? v.split(":").slice(0, 2).map((x) => x.padStart(2, "0")).join(":") : null);
// The page is built from Home Assistant's elements; this sheet lays them out and
// draws what Home Assistant has no element for (tabs, chips, lists, charts),
// in the colours and sizes of the active theme
export const STYLE = `
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


// The drawing of a box's card, for the page and the dashboard card alike. The
// element using it brings _hass and its own state (a command running, a level just sent).
export const BoxView = (Base) => class extends Base {
    // Home Assistant may set properties before the element is defined (its script
    // waits for this module first); such a value hides the setter until handed on
    _upgrade(names) {
      for (const name of names) {
        if (!Object.prototype.hasOwnProperty.call(this, name)) continue;
        const value = this[name];
        delete this[name];
        this[name] = value;
      }
    }

    get _lang() {
      return this._hass?.locale?.language || this._hass?.language || "en";
    }

    get _t() {
      return this._lang.toLowerCase().startsWith("de") ? TEXTS.de : TEXTS.en;
    }

    _relative(iso) {
      const ms = time(iso);
      if (!Number.isFinite(ms)) return this._t.never;
      const diff = (ms - Date.now()) / 1000;
      const abs = Math.abs(diff);
      const [unit, div] = abs < 60 ? ["second", 1] : abs < 3600 ? ["minute", 60] : abs < 86400 ? ["hour", 3600] : ["day", 86400];
      return new Intl.RelativeTimeFormat(this._lang, { numeric: "auto" }).format(Math.round(diff / div), unit);
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

    _pic(url, extra = "") {
      const src = safeUrl(url);
      return `<div class="pic${extra}">${icon("figures")}${src ? `<img src="${esc(src)}" alt="" loading="lazy">` : ""}</div>`;
    }

    // Online or offline as a small dot, the word in its tooltip
    _dot(b) {
      const t = this._t;
      const [state, label] = b.online === true ? ["ok", t.online] : b.online === false ? ["err", t.offline] : ["", t.unknown];
      const seen = b.online !== true && b.last_seen ? ` · ${fill(t.lastSeen, { t: this._relative(b.last_seen) })}` : "";
      return `<span class="dot ${state}" role="img" title="${esc(label + seen)}" aria-label="${esc(label + seen)}"></span>`;
    }

    // card: the dashboard card's configuration, null on the page. The card has neither the
    // cog nor the battery's overlay, and leaves out each part its show_<part> turns off.
    _box(b, showHousehold, card = null) {
      const t = this._t;
      const live = b.generation === "toniebox_2";
      const show = (part) => !card || card[`show_${part}`] !== false;
      const chips = showHousehold && b.household ? this._chip(b.household) : "";
      const pic = show("picture") ? safeUrl(b.image_url) : null;
      // Settings, night mode and bedtimes sit behind the box's cog
      const cog = !card && (b.settings || b.bedtime) ? iconButton("cog", t.boxSettingsOf, `class="box-cog" data-act="boxset:${esc(b.id)}"`) : "";
      // The battery's level sits in the head; on the page the rest of the battery opens in the overlay
      const batt = !live || !show("battery") ? "" : card
        ? `<span class="fact">${this._batteryLevel(b)}</span>`
        : b.battery_stats
          ? `<button class="fact fact-btn" data-act="battset:${esc(b.id)}" title="${esc(t.batteryDetails)}" aria-label="${esc(t.batteryDetails)}">${this._batteryLevel(b)}</button>`
          : "";
      const title = `${pic ? `<img class="box-pic" src="${esc(pic)}" alt="">` : ""}<span class="box-name">${esc(b.name || b.id)}</span>${this._dot(b)}` +
        `<span class="chips">${chips}</span><span class="status">${batt}</span>${cog}`;
      const facts = [];
      if (Number.isFinite(b.volume) && show("volume")) {
        // The box's own percent once it reported the level; a level just sent shows as a level
        const sent = this._volSent?.box === b.id;
        const shown = Number.isFinite(b.volume_percent) && !sent ? `${b.volume_percent} %` : fill(t.volumeLevel, { v: b.volume, max: b.volume_max ?? 13 });
        facts.push(`<span class="fact${sent ? " pending" : ""}" title="${esc(fill(t.volumeLevel, { v: b.volume, max: b.volume_max ?? 13 }))}">${icon("volume")}${esc(shown)}</span>`);
      }
      if (b.headphones?.connected && show("headphones")) {
        const hp = Number.isFinite(b.headphones.battery) ? fill(t.headphonesBattery, { p: b.headphones.battery }) : t.headphones;
        facts.push(`<span class="fact">${icon("headphones")}${esc(hp)}</span>`);
      }
      const sleep = this._sleep(b.sleep_timer);
      if (sleep && show("sleep_timer")) facts.push(`<span class="fact">${icon("sleep")}${esc(sleep)}</span>`);
      // The next alarm and a night mode at work stay on the card; the rest is behind the cog
      const next = b.bedtime?.next_alarm;
      if (next && show("next_alarm")) {
        const when = new Date(time(next.at)).toLocaleString(this._lang, { weekday: "short", hour: "2-digit", minute: "2-digit" });
        facts.push(`<span class="fact">${icon("alarm")}${esc(fill(t.nextAlarm, { t: when }))}</span>`);
      }
      if (b.night?.mode?.enabled && b.night.phase === "night" && show("night_mode")) facts.push(this._chip(t.nightMode, "on"));
      let body = facts.length ? `<div class="facts">${facts.join("")}</div>` : "";
      if (live) {
        // In parts the dashboard card can lay out side by side when it is wide
        const now = show("playback") ? `<div class="now">${this._playback(b.playback)}</div>` : "";
        const ctl = show("controls") ? this._controls(b) : "";
        body = `<div class="box-body">${body}${now}${ctl ? `<div class="ctl">${ctl}</div>` : ""}</div>`;
      } else body += `<div class="muted">${esc(t.classicNote)}</div>`;
      const notes = [];
      if (!live && b.last_seen) notes.push(fill(t.lastSeen, { t: this._relative(b.last_seen) }));
      if (notes.length) body += `<div class="muted small">${esc(notes.join(" · "))}</div>`;
      return this._card(title, body);
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
};
