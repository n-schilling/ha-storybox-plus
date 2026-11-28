// Storybox Plus: what the page in the sidebar and the dashboard card share, the
// icons, the texts in English and German, small helpers, the number format, the
// shared style and the drawing of a box's card. The page and the card import it
// with the version of their own script, so a browser never mixes an old module
// with a new page.

export const MDI = {
  download: "M5,20H19V18H5M19,9H15V3H9V9H5L12,16L19,9Z",
  copy: "M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z",
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
  repeat: "M17,17H7V14L3,18L7,22V19H19V13H17M7,7H17V10L21,6L17,2V5H5V11H7V7Z",
  repeatOne: "M13,15V9H12L10,10V11H11.5V15M17,17H7V14L3,18L7,22V19H19V13H17M7,7H17V10L21,6L17,2V5H5V11H7V7Z",
  tracks: "M15,6H3V8H15V6M15,10H3V12H15V10M3,16H11V14H3V16M17,6V14.18C16.69,14.07 16.35,14 16,14A3,3 0 0,0 13,17A3,3 0 0,0 16,20A3,3 0 0,0 19,17V8H22V6H17Z",
  close: "M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z",
  upload: "M9,16V10H5L12,3L19,10H15V16H9M5,20V18H19V20H5Z",
  up: "M13,20H11V8L5.5,13.5L4.08,12.08L12,4.16L19.92,12.08L18.5,13.5L13,8V20Z",
  down: "M11,4H13V16L18.5,10.5L19.92,11.92L12,19.84L4.08,11.92L5.5,10.5L11,16V4Z",
  remove: "M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z",
  sort: "M19 17H22L18 21L14 17H17V3H19M11 13V15L7.67 19H11V21H5V19L8.33 15H5V13M9 3H7C5.9 3 5 3.9 5 5V11H7V9H9V11H11V5C11 3.9 10.11 3 9 3M9 7H7V5H9Z",
  shuffle: "M14.83,13.41L13.42,14.82L16.55,17.95L14.5,20H20V14.5L17.96,16.54L14.83,13.41M14.5,4L16.54,6.04L4,18.59L5.41,20L17.96,7.46L20,9.5V4M10.59,9.17L5.41,4L4,5.41L9.17,10.58L10.59,9.17Z",
  playAll: "M19,9H2V11H19V9M19,5H2V7H19V5M2,15H15V13H2V15M17,13V19L22,16L17,13Z",
  star: "M12,17.27L18.18,21L16.54,13.97L22,9.24L14.81,8.62L12,2L9.19,8.62L2,9.24L7.45,13.97L5.82,21L12,17.27Z",
  starOff: "M12,15.39L8.24,17.66L9.23,13.38L5.91,10.5L10.29,10.13L12,6.09L13.71,10.13L18.09,10.5L14.77,13.38L15.76,17.66M22,9.24L14.81,8.63L12,2L9.19,8.63L2,9.24L7.45,13.97L5.82,21L12,17.27L18.18,21L16.54,13.97L22,9.24Z",
  text: "M18.5,4L19.66,8.35L18.7,8.61C18.25,7.74 17.79,6.87 17.26,6.43C16.73,6 16.11,6 15.5,6H13V16.5C13,17 13,17.5 13.33,17.75C13.67,18 14.33,18 15,18V19H9V18C9.67,18 10.33,18 10.67,17.75C11,17.5 11,17 11,16.5V6H8.5C7.89,6 7.27,6 6.74,6.43C6.21,6.87 5.75,7.74 5.3,8.61L4.34,8.35L5.5,4H18.5Z",
  link: "M10.59,13.41C11,13.8 11,14.44 10.59,14.83C10.2,15.22 9.56,15.22 9.17,14.83C7.22,12.88 7.22,9.71 9.17,7.76V7.76L12.71,4.22C14.66,2.27 17.83,2.27 19.78,4.22C21.73,6.17 21.73,9.34 19.78,11.29L18.29,12.78C18.3,11.96 18.17,11.14 17.89,10.36L18.36,9.88C19.54,8.71 19.54,6.81 18.36,5.64C17.19,4.46 15.29,4.46 14.12,5.64L10.59,9.17C9.41,10.34 9.41,12.24 10.59,13.41M13.41,9.17C13.8,8.78 14.44,8.78 14.83,9.17C16.78,11.12 16.78,14.29 14.83,16.24V16.24L11.29,19.78C9.34,21.73 6.17,21.73 4.22,19.78C2.27,17.83 2.27,14.66 4.22,12.71L5.71,11.22C5.7,12.04 5.83,12.86 6.11,13.65L5.64,14.12C4.46,15.29 4.46,17.19 5.64,18.36C6.81,19.54 8.71,19.54 9.88,18.36L13.41,14.83C14.59,13.66 14.59,11.76 13.41,10.59C13,10.2 13,9.56 13.41,9.17Z",
  // The areas of the page: mdi:account-music-outline, mdi:tune-variant
  figuresArea: "M11,4A4,4 0 0,1 15,8A4,4 0 0,1 11,12A4,4 0 0,1 7,8A4,4 0 0,1 11,4M11,6A2,2 0 0,0 9,8A2,2 0 0,0 11,10A2,2 0 0,0 13,8A2,2 0 0,0 11,6M11,13C12.1,13 13.66,13.23 15.11,13.69C14.5,14.07 14,14.6 13.61,15.23C12.79,15.03 11.89,14.9 11,14.9C8.03,14.9 4.9,16.36 4.9,17V18.1H13.04C13.13,18.8 13.38,19.44 13.76,20H3V17C3,14.34 8.33,13 11,13M18.5,10H20L22,10V12H20V17.5A2.5,2.5 0 0,1 17.5,20A2.5,2.5 0 0,1 15,17.5A2.5,2.5 0 0,1 17.5,15C17.86,15 18.19,15.07 18.5,15.21V10Z",
  setup: "M8 13C6.14 13 4.59 14.28 4.14 16H2V18H4.14C4.59 19.72 6.14 21 8 21S11.41 19.72 11.86 18H22V16H11.86C11.41 14.28 9.86 13 8 13M8 19C6.9 19 6 18.1 6 17C6 15.9 6.9 15 8 15S10 15.9 10 17C10 18.1 9.1 19 8 19M19.86 6C19.41 4.28 17.86 3 16 3S12.59 4.28 12.14 6H2V8H12.14C12.59 9.72 14.14 11 16 11S19.41 9.72 19.86 8H22V6H19.86M16 9C14.9 9 14 8.1 14 7C14 5.9 14.9 5 16 5S18 5.9 18 7C18 8.1 17.1 9 16 9Z",
  // mdi:information-outline, the (i)
  info: "M11,9H13V7H11M12,20C7.59,20 4,16.41 4,12C4,7.59 7.59,4 12,4C16.41,4 20,7.59 20,12C20,16.41 16.41,20 12,20M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M11,17H13V11H11V17Z",
  save: "M15,9H5V5H15M12,19A3,3 0 0,1 9,16A3,3 0 0,1 12,13A3,3 0 0,1 15,16A3,3 0 0,1 12,19M17,3H5C3.89,3 3,3.9 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V7L17,3Z",
  chevronRight: "M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z",
};

export const TEXTS = {
  en: {
    cardName: "Toniebox", cardDescription: "What plays on the Tonieboxes 2, with their buttons.", cardEntity: "Toniebox 2 (none: all of them)",
    cardMissing: "No Toniebox 2 to show.", cardUnknown: "This is no Toniebox 2 of Storybox Plus.",
    cardTitle: "Title", cardSize: "Size", sizeAuto: "By the space the card gets", sizeSmall: "Small", sizeMedium: "Medium", sizeLarge: "Large",
    cardShow: "Show", show_picture: "Picture of the box", show_battery: "Battery", show_volume: "Volume", show_headphones: "Headphones",
    show_sleep_timer: "Running sleep timer", show_next_alarm: "Next alarm", show_night_mode: "Night mode of the light ring",
    show_playback: "What plays", show_controls: "Buttons",
    tabBoxes: "Boxes", tabFigures: "Figures", tabListening: "Listening", tabSetup: "Setup",
    pgBoxes: "Overview", pgFigures: "Figures", pgTunes: "Tunes", pgSummary: "Summary", pgTimes: "Times",
    pgSetup: "Overview", pgHousehold: "Household", pgPreferences: "Preferences", pgLog: "Log",
    logLevel: "Log level", logLevelHint: "What the integration writes to its log and to Home Assistant's log. Info logs every change in the cloud, Debug every request and push message as well. The level stays across restarts; debug logging turned on on Home Assistant's integration page wins until it is turned off.",
    logL_debug: "Debug", logL_info: "Info", logL_warning: "Warning", logL_error: "Error",
    logLines: "Latest lines", logLinesHint: "The latest 500 lines of the days kept, newest first; Download gives all of them. IDs are cut to their first six characters.",
    logDays: "Keep lines for", logDaysUnit: "days", logDaysHint: "The lines are written to one file per day in Home Assistant's storage folder, so they survive a restart; older days are deleted. 0 writes nothing: the page shows the lines since the start only. At most 90 days.", logDownload: "Download", logLinesMemoryHint: "The latest lines since Home Assistant started, newest first; nothing is kept on disk. IDs are cut to their first six characters.", logEmpty: "No lines yet at this level.", logCopy: "Copy", logCopied: "The lines are copied.", logEffective: "Home Assistant's debug logging is on: the integration logs at {l} until it is turned off.",
    vSettings: "Settings", vNight: "Night mode", vBedtimes: "Bedtimes", vBattery: "Battery", vChapters: "Chapters", vTune: "Tune", vAdd: "Add",
    vAutomations: "Automations",
    autoIntro: "Ready-made automations, with the IDs of this figure or box filled in. Copy one, open a new automation, choose Edit in YAML from the menu at the top right, paste it over what is there, adjust the times and texts, and save.",
    autoIntroHelp: "Home Assistant offers no way for an integration to open the automation editor with content, so the snippet goes through the clipboard. Nothing runs until you save the automation. The figure is named by its ID, so it keeps working when the figure is renamed.",
    autoNew: "New automation", autoCopy: "Copy", autoCopied: "Copied. Paste it into a new automation, in YAML.",
    autoNoBox: "For this figure there is nothing to automate yet: automations that react to a placed figure need a Toniebox 2.",
    autoPlacedTitle: "When this figure is placed", autoPlacedHint: "Starts a sleep timer of 45 minutes on the Toniebox 2 the figure is placed on. Replace the action with anything else, such as dimming the light.",
    autoPlacedAlias: "{n} placed: sleep timer",
    autoGreetTitle: "A greeting every evening", autoGreetHint: "At 18:30 the voice chosen under Setup → Preferences speaks the text as a new chapter; the greeting of the day before is removed. With the live mode on (Settings of the figure), it plays first.",
    autoGreetAlias: "{n}: greeting every evening", autoGreetText: "Good night! Sleep well and dream something lovely.", autoGreetChapter: "Good night",
    autoShuffleTitle: "Shuffle every morning", autoShuffleHint: "At 7:00 the chapters get a new random order. The cloud converts the figure for it; a box fetches it the next time it is placed.",
    autoShuffleAlias: "{n}: shuffle every morning",
    autoCleanTitle: "Tidy up every week", autoCleanHint: "On Sundays at 20:00 only the last 10 chapters stay. The removed audio is gone; the cloud keeps no copy.",
    autoCleanAlias: "{n}: keep the last 10 chapters",
    autoQuietTitle: "Quieter in the evening", autoQuietHint: "At 19:00 the maximum volume goes down, at 7:00 back to what it is now. The box's own bedtime limits (Settings) may already be enough.",
    autoQuietAlias: "{n}: quieter in the evening",
    autoRepeatTitle: "Repeat this figure",
    autoRepeatHint: "Placed on a Toniebox 2, the figure repeats as a whole until it is taken off.",
    autoRepeatAlias: "{n} placed: repeat",
    autoLateTitle: "Not late in the evening",
    autoLateHint: "Placed between 19:30 and 6:00, the Toniebox 2 pauses at once. Change the times to your evening.",
    autoLateAlias: "{n}: not late in the evening",
    autoTellTitle: "A note when it is placed",
    autoTellHint: "Writes a note into Home Assistant's notifications. Replace the action with a message to your phone to be told on the way.",
    autoTellAlias: "{n} placed: note",
    autoTellText: "{n} plays on {box}.",
    autoSleepTitle: "A sleep timer every evening",
    autoSleepHint: "At 19:30, if the box plays, it falls asleep by itself half an hour later.",
    autoSleepAlias: "{n}: sleep timer every evening",
    autoBatteryTitle: "A note when the battery runs low",
    autoBatteryHint: "Writes a note into Home Assistant's notifications once the battery falls below 20 percent. Replace the action with a message to your phone.",
    autoBatteryAlias: "{n}: battery low",
    autoBatteryText: "The battery is below 20 percent. Time for the charger.",
    grpGeneral: "General", grpLight: "Light", grpBedtime: "At bedtime", grpControls: "Tapping and tilting", grpPresence: "In the network",
    s_presence_entity: "Presence entity", h_presence_entity: "A device tracker of the box (from your router's integration, for example) or a binary sensor for connectivity, such as a ping. Empty: the box shows no state, as before.",
    s_presence_lag: "Lag taken off the active time", h_presence_lag: "How long the box stays in the network after its last use, as the entity sees it: the box's own standby and the entity's delay together. It is taken off the end of every stretch in the network; a stretch no longer than this counts nothing. Measured at about 20 minutes with a router's device tracker; 0 counts everything.",
    presenceHint: "A Toniebox 1 tells the cloud nothing live. If Home Assistant sees the box in your network, the page can show whether it is online and count its active time. The entity is kept in Home Assistant only.",
    activeTime: "Active time of the Toniebox 1", activeHelp: "How long the box was in the network, by its presence entity. This is an indication, not listening time: the box stays awake for some minutes after the last sound and the entity notices its leaving late (the lag set in the box's settings is taken off for that), time with a figure on it that does not play counts too, and a box in offline mode is not seen at all. It is not part of the listening time above.",
    refresh: "Refresh", integration: "Integration in Home Assistant", info: "Explanation", asOf: "As of {t}", loading: "Loading …",
    about: "Storybox Plus {version}", aboutCommit: "Storybox Plus {version} · commit {commit}",
    errDetail: "Message",
    e_not_loaded: "The account is not loaded.", e_not_found: "This is gone meanwhile. Refresh and try again.",
    e_invalid_format: "The input does not fit.", e_unauthorized: "This needs an administrator.",
    e_other: "That did not work. Please try again.",
    e_connection: "Home Assistant cannot be reached right now.",
    e_cloud_error: "The Tonie cloud did not answer or refused it.",
    e_invalid_command: "The box needs a value for this.",
    e_no_favourites: "The figure on the box has no favourites.",
    e_tune_plays: "A Tune lies on the figure; its chapters take no stars.",
    e_other_figure: "Another figure is on the box now.",
    e_unloaded: "Storybox Plus was reloaded meanwhile. Please try again.",
    e_unknown_command: "Storybox Plus is not ready yet. Please try again in a moment.",
    e_unknown_household: "This household is gone meanwhile. Refresh and try again.",
    e_unknown_chapter: "The chapters changed meanwhile. Refresh and try again.",
    e_unknown_schedule: "This bedtime is gone meanwhile. Refresh and try again.",
    e_unknown_file: "The file is gone; upload it again.", e_empty_file: "The file is empty.",
    e_upload_failed: "The file did not reach Home Assistant.",
    e_not_creative: "Only creative figures take own chapters.",
    e_not_lockable: "Only bought figures and discs can be locked.",
    e_unknown_tune: "The account has no such Tune.", e_unsuitable_tune: "This Tune does not fit the figure.",
    e_no_tune: "No Tune lies on this figure.",
    e_tune_on: "A Tune lies on this figure. Take it off first, then add chapters.",
    e_tune_not_changed: "The cloud took the Tune change but does not show it yet. Check the figure again in a minute.",
    e_chapter_missing: "The cloud answered, but the chapter is not on the figure. Nothing was added.",
    e_fetcher_missing: "Links need the Media Fetcher app.",
    e_fetcher_unavailable: "The Media Fetcher app does not answer.",
    e_invalid_url: "That is no web link.",
    e_too_long: "The video is longer than the time still free on the figure.",
    e_too_large: "The file is larger than the figure can hold.",
    e_speech_missing: "Texts need a voice in Home Assistant.",
    e_speech_failed: "The voice could not speak the text.",
    e_alarm_due: "An alarm is set; a sleep timer would cancel it.",
    e_nothing_plays: "No figure is on the box.", e_not_supported: "This box does not have that setting.",
    e_invalid_value: "A Toniebox 1 takes 25, 50, 75 or 100 percent.",
    e_no_alarm: "This box has no bedtimes.",
    noEntry: "No account is set up.", noEntryHelp: "Add one under Settings → Devices & services → Add integration → Storybox Plus.",
    notLoaded: "No account is loaded at the moment.", notLoadedHelp: "Home Assistant tries again by itself; its page of the integration says why.",
    pushDown: "Live channel not connected", pushDownHelp: "The boxes' states come with the next poll and may be a few minutes old until the live channel is back.",
    noBoxes: "No box in this account yet.",
    online: "Online", offline: "Offline", unknown: "Unknown", charging: "charging",
    sleepUntil: "Sleep timer until {t}", sleepOn: "Sleep timer active", firmware: "Firmware",
    h_firmware: "The software on the box; the box updates it itself.",
    classicNote: "A Toniebox 1 reports no live data.", lastSeen: "Last seen {t}", never: "never",
    battery: "Battery", batteryHelp: "Home Assistant records every discharge of a Toniebox 2 and works out from them how long a full charge lasts.",
    perFull: "about {h} h per full charge", perFullProjected: "about {h} h per full charge, projected",
    remaining: "lasts about {h} more", charge1: "1 charge", chargesN: "{n} charges", nowSince: "now {t} since {p} %", noCycles: "no discharge recorded yet",
    history: "Charge history", colDay: "Day", colOn: "Run time", colLevel: "Level", colPerFull: "Per full charge", batteryDetails: "Battery and charge history",
    playing: "Playing", paused: "Paused", placed: "Figure placed", nothing: "Nothing on the box",
    chapter: "Chapter", unknownFigure: "Unknown figure", search: "Search figures and chapters", kindLabel: "Kind of figure",
    kind_all: "All", kind_content: "Tonies", kind_creative: "Creative-Tonies", kind_disc: "Discs",
    kind1_creative: "Creative-Tonie", kind1_disc: "Disc",
    figure1: "1 figure", figuresAll: "{n} figures", figuresOf: "{n} of {m} figures",
    noFigures: "No figure in the household yet.", noMatch: "No figure matches.",
    chapter1: "1 chapter", chaptersN: "{n} chapters", noChapters: "No chapters yet.", chaptersFree: "room for {n} more chapters",
    chaptersHelp: "Edit rearranges, renames and removes chapters; new ones come from the view Add.",
    onBox: "on {box}", locked: "Locked", transcoding: "converting", free: "Free: {t} h",
    edit: "Edit", save: "Save", cancel: "Cancel", upload: "Upload", uploadFiles: "Choose files", dismiss: "Dismiss", add: "Add", next: "Continue",
    uploadLine: "Audio files from this device become chapters.",
    uploadHint: "Each file becomes a chapter named after the file; the cloud converts it, a box downloads the figure again.",
    moveUp: "Move up", moveDown: "Move down", remove: "Remove", renameChapter: "Rename", chapterName: "Name of the chapter", apply: "Apply",
    sortTitle: "Sort A–Z", shuffle: "Shuffle", clearAll: "Remove all chapters",
    clearAsk1: "Really remove all {n} chapters of this figure?", clearYes1: "Yes, remove all",
    clearAsk2: "The cloud keeps no copy of your audio files: once saved, they are gone from it for good.",
    clearYes2: "I have them elsewhere, remove all", clearNo: "Keep them",
    editHint: "The changes are sent together when you save. The cloud then converts the figure anew, and a box downloads it again.",
    convErrors: "The last conversion dropped chapters: {r}", convErrorsHelp: "The cloud takes common audio formats up to 90 minutes in total; upload the dropped files again in another format.",
    reason_wrongFormat: "unsupported format", reason_tooLong: "more than 90 minutes in total", reason_unknownError: "unknown error",
    c_name: "Name of the figure", h_c_name: "As the app and the boxes show it.",
    c_live: "Live mode", h_c_live: "The newest chapter plays first, as for a message that was just recorded.",
    liveChip: "live",
    shuffleSwap: "Shuffle when another figure replaces it",
    shuffleSwapHint: "On a Toniebox 2: once another figure is placed after it, the chapters get a new order. Taking it off and putting it back keeps where it was. Every shuffle makes the cloud convert the figure anew.",
    lockSwitch: "Locked to the household", lockHint: "A locked figure cannot be claimed into another household, for example when it is lent to a friend.",
    figVolume: "Volume of this figure", figVolumeBox: "As set on the box", figVolumeChip: "volume {v} / 13",
    figVolumeHint: "On a Toniebox 2 the figure plays at this level; taken off or replaced, the box gets its level from before back. The 13 levels divide the maximum volume set for the box: level 13 is that maximum, not the loudest the box can play, so a figure never plays louder than the maximum allows.",
    favChip: "{n} favourites", favChip1: "1 favourite", favOn: "Mark as a favourite", favOff: "Favourite: take the star off",
    favIs: "Favourite",
    favHint: "A star marks a favourite chapter. How the favourites play on a Toniebox 2 is set for the account under Setup → Preferences, and for this figure alone under Settings.",
    favMode: "How its favourites play",
    favModeHint: "On a Toniebox 2, once the figure has a star. Favourites first: placed on the box, the figure starts with its favourites and plays the other chapters after them. Random favourite first: the same, with another favourite at the front each time. Only the favourites: every other chapter is skipped and the box pauses after the last favourite. Only the favourites at bedtime: favourites first by day, only the favourites within a bedtime of the box. The beginning of a chapter that is skipped can be heard for a moment; without the internet or Home Assistant the box plays as it always does.",
    favMode_account: "As for the account ({m})", favMode_off: "As the box plays, stars are kept", favMode_first: "Favourites first",
    favMode_random: "Random favourite first", favMode_only: "Only the favourites", favMode_bedtime: "Only the favourites at bedtime",
    favNow_first: "Favourites first", favNow_random: "Favourites first", favNow_only: "Only favourites", favNowAll: "Everything today",
    favAll: "Everything today", favAllOn: "Play every chapter until the figure is taken off",
    favAllOff: "Every chapter plays until the figure is taken off. Follow the favourites again",
    prefFavourites: "Favourites", prefFavMode: "How favourites play",
    prefFavModeHint: "On a Toniebox 2, for every figure with a star that has no setting of its own. Favourites first: placed on the box, a figure starts with its favourites and plays the other chapters after them. Random favourite first: the same, with another favourite at the front each time. Only the favourites: every other chapter is skipped and the box pauses after the last favourite. Only the favourites at bedtime: favourites first by day, only the favourites within a bedtime of the box. The same figure placed again within two minutes plays on where it was.",
    pgFavourites: "Favourites", favListNone: "No chapter has a star yet. Open a figure and mark its best chapters, or tap the star of the chapter that plays.",
    favListHelp: "Every chapter with a star. A chapter of a figure that stands on a Toniebox 2 plays with a tap.",
    favPlay: "Play on {box}", favOnBox: "on {box}",
    statFav: "Favourites", statFavShare: "of the listening time went to favourite chapters",
    statFavHelp: "Counted by the stars as they are now, over the time whose chapter is known. Chapters of creative figures are counted by their position, so arranging them anew mixes their times.",
    statFavNone: "No chapter has a star yet.",
    statHidden: "Heard a lot, no star yet", statHiddenHelp: "The chapters without a star that were heard longest: favourites nobody marked yet. The star marks them.",
    statUnheard: "Stars hardly heard", statUnheardHelp: "Favourites that were heard for less than a minute over these days, of figures that were listened to. The star takes them off the favourites.",
    statPlays: "about {n}×",
    tune: "Tune", tuneOn: "Tune on it: {t}", tuneRemove: "Take the Tune off", tunePick: "Bought Tune", tuneAssign: "Lay on",
    tuneLeft: "{n} more times", tuneHintCreative: "The figure's chapters stay; they play again once the Tune is taken off.",
    tuneHint: "The figure plays the Tune instead of its own story until it is taken off.",
    tunesTitle: "Bought Tunes", tunesHelp: "A Tune is bought content that lies on a fitting figure instead of its own story; lay one on in the figure's view Tune.",
    noTunes: "No Tune in the account yet.", tuneOnFigure: "on {f}", tuneInUse: "in use",
    prefVoucher: "Tunes voucher", voucherCode: "Voucher code", voucherRedeem: "Redeem",
    voucherDone: "Redeemed: {n} Tunes added.", voucherNone: "Redeemed, but the cloud names no new Tune.",
    voucherHint: "A voucher can be redeemed once; the Tunes then show on the figures they fit.",
    fromCode: "Content from a code", codePlaceholder: "Content code", codeFigure: "Creative figure",
    codeHint: "Ready-made content from a code (for example on a card) is added to the figure; the cloud then converts it.",
    codeAdded: "The content was added to {f}.",
    fromLink: "From YouTube", linkPlaceholder: "Link to a YouTube video",
    linkHint: "The audio of the video becomes a chapter, named after the video. It is fetched through Home Assistant.",
    linkProbe: "Reading the video …", linkFetch: "Fetching {name} …", linkFetchPct: "Fetching {name} ({p} %) …",
    linkConvert: "Converting {name} …", linkUpload: "Uploading {name} to the cloud …",
    fetcherMissing: "Needs the Media Fetcher app.", fetcherHelp: "Install it in Home Assistant under Settings → Apps; it fetches the audio of a video.",
    fromText: "From text", textTitle: "Title (optional)", textBody: "Text to be spoken",
    textHint: "A voice of Home Assistant speaks the text; the recording becomes a chapter. With Piper the text stays in the house; a voice of a cloud service, chosen in the preferences, gets the text.",
    speechMissing: "Needs a voice.", speechHelp: "Set up the Wyoming integration with Piper in Home Assistant, or choose another text-to-speech entity under Setup → Preferences.",
    textBusy: "The voice speaks the text and it goes to the cloud …", textAdded: "The spoken text was added as a chapter.", linkAdded: "„{name}“ was added as a chapter.",
    uploading: "Uploading {name} ({n} of {m}) …",
    range_7: "7 days", range_30: "30 days", range_365: "365 days", range_all: "All", rangeLabel: "Period",
    lastDays: "last {n} days", since: "since {d}", sinceSetup: "since the setup",
    total: "Listening time", top: "Most played", topPlaced: "Placed most often", placedTimes: "{n}×", perDay: "Per day", perWeek: "Per week", perBox: "Listening time of the Toniebox 2",
    weekOf: "Week of {d}", allBoxes: "All boxes", heatBoxLabel: "Box", vsBefore: "{p} compared with the {n} days before",
    chartDays: "Listening time on {n} days, {total} h in all; the most on {top} with {v} h.",
    chartWeeks: "Listening time in {n} weeks, {total} h in all; the most in the {top} with {v} h.",
    topChapters: "Most played chapters", whenListened: "When it is listened to",
    whenHint: "Summed over the period, per weekday and hour of the day; no single plays are kept.",
    noteLocal: "Home Assistant counts the listening time itself, from what a Toniebox 2 reports live. It does not come from the manufacturer's cloud and so cannot be complete: it starts with the setup, the Toniebox 1 is missing, and so is anything played while Home Assistant was not running.",
    disabled: "Counting is switched off.", disabledHelp: "Switch it on under Setup → Preferences; it starts from then on.",
    noStats: "Nothing was counted yet.",
    bedtimes: "Bedtimes", addSchedule: "Add", scheduleNew: "New bedtime", scheduleUnnamed: "Bedtime",
    noSchedules: "No bedtime yet.", schedulesUnknown: "The bedtimes could not be read yet.",
    schedulesUnknownHelp: "The cloud names them with the next poll; refresh in a minute.",
    everyDay: "every day", alarmOn: "Alarm", scheduleOn: "Bedtime active", confirmDelete: "Delete the bedtime {name}?",
    nextAlarm: "Next alarm {t}", alarmArmed: "set on the box", alarmPending: "set as soon as the box is online",
    alarmLater: "set the evening before",
    alarmHint: "A bedtime with an alarm wakes the child on the chosen days. Home Assistant sets the alarm on the box every evening, as soon as the box is online; the app sets it only once. While an alarm is due, the sleep timer and switching the box off are refused, because the box keeps only one timer.",
    f_name: "Name", f_days: "Days of the wake-up", f_sleep_time: "Bedtime", f_wakeup_time: "Wake-up",
    f_enabled: "Active", f_alarm_enabled: "Alarm at the wake-up", f_alarm_volume: "Alarm volume", f_alarm_morning_light: "Sunrise light",
    deleteSchedule: "Delete",
    wakeUpLight: "Wake-up light", noWakeUpLight: "No wake-up light set.", setWakeUpLight: "Set", f_at: "Date and time", f_tone: "Tone", tone1: "Morning Glow", tone2: "Birdsong Rhythm", tone3: "Sound Hopper", tone4: "Wake-up Call", tone5: "Good Morning Beat", e_alarm_too_soon: "Choose a time at least 5 minutes from now; the box takes no closer alarm.",
    wakeUpLightHint: "One alarm at a time of its own, like the app's wake-up light: with a tone, a volume and the sunrise light. It needs a time at least 5 minutes ahead. Home Assistant sets it on the box once it is less than 18 hours away and the box is online; a box that comes online less than 5 minutes before misses it. If a bedtime's alarm rings earlier, that one is set first and the wake-up light after it. Once it has rung, it is gone.",
    headphones: "Headphones", headphonesBattery: "Headphones, battery {p} %",
    repeatOff: "Repeat: off", repeatAll: "Repeat: the whole figure", repeatOne: "Repeat: this chapter",
    ctlTracks: "Chapters", tracksTitle: "Chapters",
    ctlPrev: "Previous chapter", ctlNext: "Next chapter", ctlPlay: "Play", ctlPause: "Pause", ctlLouder: "Louder", ctlQuieter: "Quieter",
    ctlSleep: "Sleep timer {m} min", ctlSleepTitle: "Sleep timer", sleepMin: "{m} min", sleepOwn: "Other duration in minutes", sleepStart: "Start", ctlSleepOff: "Cancel the sleep timer",
    boxSettingsOf: "Settings of the box", settingsPending: "Waiting for the box", offlineMode: "Offline mode",
    offlineHelp: "The box is set to work without the cloud; it takes changes only once it is back online.",
    noSettings: "The cloud names no settings of this box.",
    settingsHint: "The box takes the settings the next time it is online.",
    s_name: "Name", h_name: "As the app and Home Assistant show the box.",
    s_max_volume: "Maximum volume", h_max_volume: "The loudest the box plays through its speaker. A Toniebox 1 knows 25, 50, 75 and 100 %.",
    s_max_headphone_volume: "Maximum headphone volume", h_max_headphone_volume: "The loudest the box plays through headphones.",
    s_lightring_brightness: "Light ring brightness", h_lightring_brightness: "How bright the ring of the box shines; 0 % is off.",
    s_bedtime_lightring_brightness: "Light ring at bedtime", h_bedtime_lightring_brightness: "The brightness of the ring while a bedtime runs.",
    s_bedtime_max_volume: "Maximum volume at bedtime", h_bedtime_max_volume: "The loudest the speaker plays while a bedtime runs.",
    s_bedtime_max_headphone_volume: "Maximum headphone volume at bedtime", h_bedtime_max_headphone_volume: "The loudest the headphones play while a bedtime runs.",
    s_skipping_enabled: "Skip chapters by tapping", h_skipping_enabled: "A tap on the side of the box skips to the next or the previous chapter.",
    s_skipping_direction: "Ear that skips forward", h_skipping_direction: "Which side of the box skips forward when tapped.",
    s_scrubbing_enabled: "Wind by tilting", h_scrubbing_enabled: "Tilting the box winds forward or back within the chapter.",
    s_accelerometer_enabled: "Tilt and tap", h_accelerometer_enabled: "Whether the box reacts to tilting and tapping at all.",
    s_tap_direction: "Tap direction", h_tap_direction: "Which side of a Toniebox 1 skips forward when tapped.",
    s_led_level: "LED", h_led_level: "The light of a Toniebox 1: on, dimmed or off.",
    s_age_mode: "Age mode", h_age_mode: "1+ makes a Toniebox 2 simpler to handle for the youngest; 3+ allows all its gestures.",
    s_language: "Language", h_language: "The language the box speaks its own messages in.",
    v_left: "Left", v_right: "Right", v_on: "On", v_off: "Off", v_dimmed: "Dimmed", sOn: "on", sOff: "off",
    sumVolume: "max. {v} %", volumeLevel: "level {v} of {max}", sumRing: "light ring {v} %", sumSkip: "skipping on", sumLed: "LED {v}",
    sumPhones: "headphones {v} %", sumTilt: "winding by tilting",
    nightMode: "Night mode of the light ring", nightNow: "Night now: the light ring is dimmed", dayNow: "Day now: the light ring is bright",
    nightPhaseHelp: "Home Assistant switches between the two brightnesses at the start and the end of the night.",
    nightHint: "Home Assistant dims the light ring at the start and sets it back at the end; a brightness set in the app in between stays until the next change. The box takes it the next time it is online.",
    n_enabled: "Active", h_n_enabled: "Switched off, the light ring keeps the brightness it has.",
    n_start: "From", h_n_start: "When the night begins.", n_end: "Until", h_n_end: "When the night ends; it may be on the next day.",
    n_night: "Light ring at night", h_n_night: "The brightness during the night; 0 % is off.",
    n_day: "Light ring otherwise", h_n_day: "The brightness the ring gets back at the end of the night.",
    setupTitle: "Setup", setupHelp: "The steps in their order; Continue leads to the first open one.",
    stepAccount: "Account loaded", stepHousehold: "Household named", stepPreferences: "Preferences chosen",
    stepDone: "Done", stepOpen: "Open", sOpen: "Open",
    extrasTitle: "Optional", stepFetcher: "Media Fetcher app", stepPiper: "Voice for texts",
    sInstalled: "Ready", sOptional: "Not set up",
    h_fetcher: "Fetches the audio of a YouTube video for a chapter. Install it in Home Assistant under Settings → Apps.",
    h_piper: "Speaks a text for a chapter. Set up the Wyoming integration with Piper in Home Assistant, or choose another text-to-speech entity under Preferences.",
    prefAnalyticsShort: "counting", prefAutoLockShort: "locking", prefMarkReadShort: "marking read",
    prefHousehold: "Household", householdName: "Name of the household", h_householdName: "As the app shows it to all members.",
    noHouseholds: "The account has no household yet.",
    membersCount: "Members ({n})", membersUnknown: "The members could not be read yet.", memberYou: "You",
    role_owner: "Owner", role_full: "Full access", role_limited: "Limited access", role_unknown: "Unknown role",
    membersHint: "As the cloud shows them to this account; members and invitations are managed in the app.",
    prefListening: "Listening time", prefAnalytics: "Count listening time",
    prefKeep: "Keep listening time", prefKeepHint: "Older days are deleted; the sums are small, so all of them can stay.",
    prefKeep_365: "1 year", prefKeep_730: "2 years", prefKeep_1825: "5 years", prefKeep_0: "Always",
    prefChapters: "New chapters", prefEngine: "Speech for texts", prefEngineHint: "The text-to-speech entity of Home Assistant that speaks a text as a chapter. Empty: Piper, the local voice, if it is set up; the text stays in the house then. A voice of a cloud service gets the text to speak it, and long texts may exceed what it takes at once.", prefVoice: "Voice for texts", prefVoiceHint: "The voice that speaks a text as a chapter, in the language of the page. Piper fetches a voice it does not have yet the first time, which takes a moment.",
    prefVoiceDefault: "Default voice", prefVoiceNone: "No voice set up",
    prefFetchMax: "Largest file from a link", prefFetchMaxHint: "A file the Media Fetcher app delivers that is larger is refused. A figure holds 90 minutes, about 90 MB as M4A. 10 to 2000 MB.",
    prefAnalyticsHint: "Keeps sums per day, figure, box, chapter and hour for the area Listening, never single plays. Switching it off deletes the sums.",
    prefFigures: "Figures", prefAutoLock: "Lock new figures and discs to the household",
    prefAutoLockHint: "A bought figure or disc that is new in the account is locked once, so it cannot be claimed into another household. Unlocked on its page or in the app, it stays unlocked.",
    prefNotices: "Notifications", prefMarkRead: "Mark notifications as read in the cloud once passed on",
    prefMarkReadHint: "The app then shows them no more. Broadcasts to all users are dismissed instead.",
    prefCloud: "Cloud",
    cloudUnknown: "The cloud's version is not known yet.",
   
    cloudCheck: "Test the cloud interface",
    cloudFits: "The cloud fits this version.",
    cloudNew: "The cloud was updated. The test shows whether everything still fits.",
    cloudBad: "The cloud answers differently than this version expects. Something may not work.",
    cloudDetail: "Backend version {v}, tested with {t}.",
    cloudChecked: "Last tested on {d}.",
    cloudCheckHelp: "When the manufacturer updates its cloud, Storybox Plus tests by itself whether everything still fits. The test only reads and changes nothing.",
   
   
   
    cloudIssue: "Report on GitHub",
    cloudIssueHelp: "Opens a new issue with what the test found. It names requests, fields and versions, nothing of your account.",
   
    openFigure: "Open the figure",
  },
  de: {
    cardName: "Toniebox", cardDescription: "Was auf den Tonieboxen 2 läuft, mit ihren Knöpfen.", cardEntity: "Toniebox 2 (keine: alle)",
    cardMissing: "Keine Toniebox 2 zum Anzeigen.", cardUnknown: "Das ist keine Toniebox 2 von Storybox Plus.",
    cardTitle: "Titel", cardSize: "Größe", sizeAuto: "Nach dem Platz, den die Karte bekommt", sizeSmall: "Klein", sizeMedium: "Mittel", sizeLarge: "Groß",
    cardShow: "Anzeigen", show_picture: "Bild der Box", show_battery: "Akku", show_volume: "Lautstärke", show_headphones: "Kopfhörer",
    show_sleep_timer: "Laufender Schlaf-Timer", show_next_alarm: "Nächster Wecker", show_night_mode: "Nachtmodus des Lichtrings",
    show_playback: "Was gerade läuft", show_controls: "Knöpfe",
    tabBoxes: "Boxen", tabFigures: "Figuren", tabListening: "Hörzeit", tabSetup: "Einrichtung",
    pgBoxes: "Übersicht", pgFigures: "Figuren", pgTunes: "Tunes", pgSummary: "Zusammenfassung", pgTimes: "Zeiten",
    pgSetup: "Übersicht", pgHousehold: "Haushalt", pgPreferences: "Einstellungen", pgLog: "Protokoll",
    logLevel: "Protokollstufe", logLevelHint: "Was die Integration in ihr Protokoll und ins Home-Assistant-Log schreibt. Info protokolliert jede Änderung in der Cloud, Debug zusätzlich jede Anfrage und jede Push-Nachricht. Die Stufe bleibt über Neustarts erhalten; das Debug-Logging auf der Integrationsseite von Home Assistant gilt vorrangig, bis es wieder aus ist.",
    logL_debug: "Debug", logL_info: "Info", logL_warning: "Warnung", logL_error: "Fehler",
    logLines: "Letzte Zeilen", logLinesHint: "Die letzten 500 Zeilen der aufbewahrten Tage, neueste zuerst; Herunterladen liefert alle. IDs sind auf ihre ersten sechs Zeichen gekürzt.",
    logDays: "Zeilen aufbewahren", logDaysUnit: "Tage", logDaysHint: "Die Zeilen werden tageweise in eine Datei im Speicherordner von Home Assistant geschrieben und überstehen so einen Neustart; ältere Tage werden gelöscht. 0 schreibt nichts: Die Seite zeigt dann nur die Zeilen seit dem Start. Höchstens 90 Tage.", logDownload: "Herunterladen", logLinesMemoryHint: "Die letzten Zeilen seit dem Start von Home Assistant, neueste zuerst; nichts wird auf Platte aufbewahrt. IDs sind auf ihre ersten sechs Zeichen gekürzt.", logEmpty: "Auf dieser Stufe gibt es noch keine Zeilen.", logCopy: "Kopieren", logCopied: "Die Zeilen sind kopiert.", logEffective: "Das Debug-Logging von Home Assistant ist an: Die Integration protokolliert auf Stufe {l}, bis es wieder aus ist.",
    vSettings: "Einstellungen", vNight: "Nachtmodus", vBedtimes: "Schlafenszeiten", vBattery: "Akku", vChapters: "Kapitel", vTune: "Tune", vAdd: "Hinzufügen",
    vAutomations: "Automationen",
    autoIntro: "Fertige Automationen, mit den IDs dieser Figur oder Box schon eingesetzt. Eine kopieren, eine neue Automation öffnen, oben rechts im Menü In YAML bearbeiten wählen, alles Vorhandene durch den Text ersetzen, Zeiten und Texte anpassen und speichern.",
    autoIntroHelp: "Home Assistant bietet Integrationen keinen Weg, den Automations-Editor mit Inhalt zu öffnen, deshalb geht der Text über die Zwischenablage. Es läuft nichts, bevor du die Automation speicherst. Die Figur steht mit ihrer ID drin, so funktioniert es auch nach einer Umbenennung.",
    autoNew: "Neue Automation", autoCopy: "Kopieren", autoCopied: "Kopiert. In eine neue Automation einfügen, im YAML-Modus.",
    autoNoBox: "Für diese Figur gibt es noch nichts zu automatisieren: Automationen, die auf eine aufgelegte Figur reagieren, brauchen eine Toniebox 2.",
    autoPlacedTitle: "Wenn diese Figur aufgelegt wird", autoPlacedHint: "Startet einen Schlaf-Timer von 45 Minuten auf der Toniebox 2, auf die die Figur gelegt wird. Die Aktion lässt sich durch etwas anderes ersetzen, etwa Licht dimmen.",
    autoPlacedAlias: "{n} aufgelegt: Schlaf-Timer",
    autoGreetTitle: "Jeden Abend ein Gruß", autoGreetHint: "Um 18:30 spricht die unter Einrichtung → Einstellungen gewählte Stimme den Text als neues Kapitel; der Gruß vom Vortag fliegt raus. Mit Live-Modus (Einstellungen der Figur) spielt er zuerst.",
    autoGreetAlias: "{n}: Gruß jeden Abend", autoGreetText: "Gute Nacht! Schlaf schön und träum etwas Schönes.", autoGreetChapter: "Gute Nacht",
    autoShuffleTitle: "Jeden Morgen mischen", autoShuffleHint: "Um 7:00 bekommen die Kapitel eine neue, zufällige Reihenfolge. Die Cloud wandelt die Figur dafür neu um; eine Box holt sie beim nächsten Auflegen.",
    autoShuffleAlias: "{n}: jeden Morgen mischen",
    autoCleanTitle: "Jede Woche aufräumen", autoCleanHint: "Sonntags um 20:00 bleiben nur die letzten 10 Kapitel. Der entfernte Ton ist weg; die Cloud behält keine Kopie.",
    autoCleanAlias: "{n}: die letzten 10 Kapitel behalten",
    autoQuietTitle: "Abends leiser", autoQuietHint: "Um 19:00 sinkt die maximale Lautstärke, um 7:00 geht sie zurück auf den jetzigen Wert. Die eigenen Grenzen der Box für die Schlafenszeit (Einstellungen) reichen vielleicht schon.",
    autoQuietAlias: "{n}: abends leiser",
    autoRepeatTitle: "Diese Figur wiederholen",
    autoRepeatHint: "Auf eine Toniebox 2 gelegt, wiederholt sich die Figur als Ganzes, bis sie abgenommen wird.",
    autoRepeatAlias: "{n} aufgelegt: wiederholen",
    autoLateTitle: "Spätabends nicht mehr",
    autoLateHint: "Zwischen 19:30 und 6:00 Uhr aufgelegt, pausiert die Toniebox 2 sofort. Die Zeiten lassen sich an den eigenen Abend anpassen.",
    autoLateAlias: "{n}: spätabends nicht mehr",
    autoTellTitle: "Hinweis, wenn sie aufgelegt wird",
    autoTellHint: "Schreibt einen Hinweis in die Benachrichtigungen von Home Assistant. Die Aktion lässt sich durch eine Nachricht ans Handy ersetzen, um unterwegs Bescheid zu bekommen.",
    autoTellAlias: "{n} aufgelegt: Hinweis",
    autoTellText: "{n} spielt auf {box}.",
    autoSleepTitle: "Schlaf-Timer jeden Abend",
    autoSleepHint: "Spielt die Box um 19:30 Uhr, schläft sie eine halbe Stunde später von selbst ein.",
    autoSleepAlias: "{n}: Schlaf-Timer jeden Abend",
    autoBatteryTitle: "Hinweis bei schwachem Akku",
    autoBatteryHint: "Schreibt einen Hinweis in die Benachrichtigungen von Home Assistant, sobald der Akku unter 20 Prozent fällt. Die Aktion lässt sich durch eine Nachricht ans Handy ersetzen.",
    autoBatteryAlias: "{n}: Akku schwach",
    autoBatteryText: "Der Akku liegt unter 20 Prozent. Zeit fürs Ladegerät.",
    grpGeneral: "Allgemein", grpLight: "Licht", grpBedtime: "In der Schlafenszeit", grpControls: "Klopfen und Kippen", grpPresence: "Im Netzwerk",
    s_presence_entity: "Anwesenheits-Entität", h_presence_entity: "Ein Device Tracker der Box (zum Beispiel aus der Integration deines Routers) oder ein Binärsensor für Konnektivität, etwa ein Ping. Leer: Die Box zeigt wie bisher keinen Status.",
    s_presence_lag: "Nachlauf, der von der Aktivzeit abgeht", h_presence_lag: "Wie lange die Box nach der letzten Nutzung noch im Netzwerk bleibt, so wie die Entität es sieht: der Standby der Box und die Verzögerung der Entität zusammen. Er wird vom Ende jeder Phase im Netzwerk abgezogen; eine Phase, die nicht länger ist, zählt nichts. Gemessen mit dem Device Tracker eines Routers: rund 20 Minuten; 0 zählt alles.",
    presenceHint: "Eine Toniebox 1 meldet der Cloud nichts live. Sieht Home Assistant die Box in deinem Netzwerk, kann die Seite zeigen, ob sie online ist, und ihre Aktivzeit mitzählen. Die Entität wird nur in Home Assistant gespeichert.",
    activeTime: "Aktivzeit der Toniebox 1", activeHelp: "Wie lange die Box im Netzwerk war, laut ihrer Anwesenheits-Entität. Das ist ein Anhaltspunkt, keine Hörzeit: Die Box bleibt nach dem letzten Ton noch einige Minuten wach und die Entität bemerkt ihr Verschwinden verzögert (dafür geht der Nachlauf aus den Einstellungen der Box ab), Zeit mit aufgelegter Figur ohne Wiedergabe zählt mit, und eine Box im Offline-Modus wird gar nicht gesehen. Sie zählt nicht zur Hörzeit oben.",
    refresh: "Aktualisieren", integration: "Integration in Home Assistant", info: "Erklärung", asOf: "Stand {t}", loading: "Lädt …",
    about: "Storybox Plus {version}", aboutCommit: "Storybox Plus {version} · Commit {commit}",
    errDetail: "Meldung",
    e_not_loaded: "Das Konto ist nicht geladen.", e_not_found: "Das gibt es inzwischen nicht mehr. Aktualisieren und erneut versuchen.",
    e_invalid_format: "Die Eingabe passt nicht.", e_unauthorized: "Dafür braucht es einen Administrator.",
    e_other: "Das hat nicht geklappt. Bitte erneut versuchen.",
    e_connection: "Home Assistant ist gerade nicht erreichbar.",
    e_cloud_error: "Die Tonie-Cloud hat nicht geantwortet oder abgelehnt.",
    e_invalid_command: "Die Box braucht dafür einen Wert.",
    e_no_favourites: "Die Figur auf der Box hat keine Favoriten.",
    e_tune_plays: "Auf der Figur liegt ein Tune; dessen Kapitel bekommen keine Sterne.",
    e_other_figure: "Auf der Box steht inzwischen eine andere Figur.",
    e_unloaded: "Storybox Plus wurde zwischendurch neu geladen. Bitte erneut versuchen.",
    e_unknown_command: "Storybox Plus ist noch nicht bereit. Bitte gleich erneut versuchen.",
    e_unknown_household: "Diesen Haushalt gibt es inzwischen nicht mehr. Aktualisieren und erneut versuchen.",
    e_unknown_chapter: "Die Kapitel haben sich zwischendurch geändert. Aktualisieren und erneut versuchen.",
    e_unknown_schedule: "Diese Schlafenszeit gibt es inzwischen nicht mehr. Aktualisieren und erneut versuchen.",
    e_unknown_file: "Die Datei ist weg; bitte noch einmal hochladen.", e_empty_file: "Die Datei ist leer.",
    e_upload_failed: "Die Datei ist nicht bei Home Assistant angekommen.",
    e_not_creative: "Nur Kreativ-Tonies nehmen eigene Kapitel.",
    e_not_lockable: "Nur gekaufte Figuren und Discs lassen sich sperren.",
    e_unknown_tune: "Diesen Tune hat das Konto nicht.", e_unsuitable_tune: "Dieser Tune passt nicht auf die Figur.",
    e_no_tune: "Auf dieser Figur liegt kein Tune.",
    e_tune_on: "Auf dieser Figur liegt ein Tune. Erst den Tune entfernen, dann Kapitel hinzufügen.",
    e_tune_not_changed: "Die Cloud hat die Tune-Änderung angenommen, zeigt sie aber noch nicht. Die Figur in einer Minute noch einmal prüfen.",
    e_chapter_missing: "Die Cloud hat geantwortet, aber das Kapitel ist nicht auf der Figur. Es wurde nichts hinzugefügt.",
    e_fetcher_missing: "Links brauchen die App Media Fetcher.",
    e_fetcher_unavailable: "Die App Media Fetcher antwortet nicht.",
    e_invalid_url: "Das ist kein Weblink.",
    e_too_long: "Das Video ist länger als die Zeit, die auf der Figur noch frei ist.",
    e_too_large: "Die Datei ist größer, als die Figur aufnehmen kann.",
    e_speech_missing: "Texte brauchen eine Stimme in Home Assistant.",
    e_speech_failed: "Die Stimme konnte den Text nicht sprechen.",
    e_alarm_due: "Ein Wecker ist gestellt; ein Schlaf-Timer würde ihn löschen.",
    e_nothing_plays: "Auf der Box steht keine Figur.", e_not_supported: "Diese Einstellung hat die Box nicht.",
    e_invalid_value: "Eine Toniebox 1 nimmt 25, 50, 75 oder 100 Prozent.",
    e_no_alarm: "Diese Box hat keine Schlafenszeiten.",
    noEntry: "Kein Konto eingerichtet.", noEntryHelp: "Unter Einstellungen → Geräte & Dienste → Integration hinzufügen → Storybox Plus hinzufügen.",
    notLoaded: "Gerade ist kein Konto geladen.", notLoadedHelp: "Home Assistant versucht es selbst erneut; seine Seite der Integration sagt, warum.",
    pushDown: "Live-Kanal nicht verbunden", pushDownHelp: "Die Zustände der Boxen kommen mit der nächsten Abfrage und können einige Minuten alt sein, bis der Live-Kanal wieder steht.",
    noBoxes: "Noch keine Box in diesem Konto.",
    online: "Online", offline: "Offline", unknown: "Unbekannt", charging: "lädt",
    sleepUntil: "Schlaf-Timer bis {t}", sleepOn: "Schlaf-Timer aktiv", firmware: "Firmware",
    h_firmware: "Die Software auf der Box; die Box aktualisiert sie selbst.",
    classicNote: "Eine Toniebox 1 meldet keine Live-Daten.", lastSeen: "Zuletzt gesehen {t}", never: "nie",
    battery: "Akku", batteryHelp: "Home Assistant zeichnet jede Entladung einer Toniebox 2 auf und rechnet daraus aus, wie lange eine volle Ladung reicht.",
    perFull: "etwa {h} h pro Ladung", perFullProjected: "voraussichtlich etwa {h} h pro Ladung",
    remaining: "reicht noch etwa {h}", charge1: "1 Ladung", chargesN: "{n} Ladungen", nowSince: "jetzt {t} seit {p} %", noCycles: "noch kein Entladezyklus erfasst",
    history: "Ladungsverlauf", colDay: "Tag", colOn: "Laufzeit", colLevel: "Ladestand", colPerFull: "Pro Ladung", batteryDetails: "Akku und Ladungsverlauf",
    playing: "Spielt", paused: "Pausiert", placed: "Figur aufgestellt", nothing: "Nichts auf der Box",
    chapter: "Kapitel", unknownFigure: "Unbekannte Figur", search: "Figuren und Kapitel suchen", kindLabel: "Art der Figur",
    kind_all: "Alle", kind_content: "Tonies", kind_creative: "Kreativ-Tonies", kind_disc: "Discs",
    kind1_creative: "Kreativ-Tonie", kind1_disc: "Disc",
    figure1: "1 Figur", figuresAll: "{n} Figuren", figuresOf: "{n} von {m} Figuren",
    noFigures: "Noch keine Figur im Haushalt.", noMatch: "Keine Figur passt.",
    chapter1: "1 Kapitel", chaptersN: "{n} Kapitel", noChapters: "Noch keine Kapitel.", chaptersFree: "Platz für {n} weitere Kapitel",
    chaptersHelp: "Bearbeiten ordnet Kapitel neu, benennt sie um und entfernt sie; neue kommen aus der Ansicht Hinzufügen.",
    onBox: "auf {box}", locked: "Gesperrt", transcoding: "wird umgewandelt", free: "Frei: {t} h",
    edit: "Bearbeiten", save: "Speichern", cancel: "Abbrechen", upload: "Hochladen", uploadFiles: "Dateien wählen", dismiss: "Schließen", add: "Hinzufügen", next: "Weiter",
    uploadLine: "Audiodateien von diesem Gerät werden Kapitel.",
    uploadHint: "Jede Datei wird ein Kapitel, benannt nach der Datei; die Cloud wandelt es um, eine Box lädt die Figur neu.",
    moveUp: "Nach oben", moveDown: "Nach unten", remove: "Entfernen", renameChapter: "Umbenennen", chapterName: "Name des Kapitels", apply: "Übernehmen",
    sortTitle: "A–Z sortieren", shuffle: "Mischen", clearAll: "Alle Kapitel entfernen",
    clearAsk1: "Wirklich alle {n} Kapitel dieser Figur entfernen?", clearYes1: "Ja, alle entfernen",
    clearAsk2: "Die Toniecloud behält keine Kopie deiner Audiodateien: Nach dem Speichern sind sie dort endgültig weg.",
    clearYes2: "Ich habe sie anderswo, alle entfernen", clearNo: "Behalten",
    editHint: "Die Änderungen gehen beim Speichern gesammelt in die Cloud. Sie wandelt die Figur danach neu um, und eine Box lädt sie neu.",
    convErrors: "Die letzte Umwandlung hat Kapitel verworfen: {r}", convErrorsHelp: "Die Cloud nimmt gängige Audioformate bis insgesamt 90 Minuten; die verworfenen Dateien in einem anderen Format erneut hochladen.",
    reason_wrongFormat: "nicht unterstütztes Format", reason_tooLong: "insgesamt mehr als 90 Minuten", reason_unknownError: "unbekannter Fehler",
    c_name: "Name der Figur", h_c_name: "So, wie die App und die Boxen sie zeigen.",
    c_live: "Live-Modus", h_c_live: "Das neueste Kapitel spielt zuerst, wie bei einer gerade aufgenommenen Nachricht.",
    liveChip: "live",
    shuffleSwap: "Neu mischen, wenn eine andere Figur sie ersetzt",
    shuffleSwapHint: "Auf einer Toniebox 2: Sobald danach eine andere Figur aufgestellt wird, bekommen die Kapitel eine neue Reihenfolge. Abnehmen und wieder aufstellen behält die Stelle. Jedes Mischen lässt die Cloud die Figur neu umwandeln.",
    lockSwitch: "Für den Haushalt gesperrt", lockHint: "Eine gesperrte Figur kann nicht in einen anderen Haushalt übernommen werden, etwa wenn sie verliehen wird.",
    figVolume: "Lautstärke dieser Figur", figVolumeBox: "Wie an der Box eingestellt", figVolumeChip: "Lautstärke {v} / 13",
    figVolumeHint: "Auf einer Toniebox 2 spielt die Figur mit dieser Stufe; abgenommen oder ersetzt, bekommt die Box ihre Stufe von vorher zurück. Die 13 Stufen teilen die maximale Lautstärke auf, die für die Box eingestellt ist: Stufe 13 ist dieses Maximum, nicht das Lauteste, was die Box kann. Eine Figur spielt also nie lauter, als das Maximum erlaubt.",
    favChip: "{n} Favoriten", favChip1: "1 Favorit", favOn: "Als Favorit markieren", favOff: "Favorit: Stern wegnehmen",
    favIs: "Favorit",
    favHint: "Ein Stern markiert ein Kapitel als Favorit. Wie die Favoriten auf einer Toniebox 2 spielen, steht fürs Konto unter Einrichtung → Einstellungen und für diese Figur allein unter Einstellungen.",
    favMode: "So spielen ihre Favoriten",
    favModeHint: "Auf einer Toniebox 2, sobald die Figur einen Stern hat. Favoriten zuerst: Aufgesetzt beginnt die Figur mit ihren Favoriten und spielt danach die übrigen Kapitel. Zufälliger Favorit zuerst: dasselbe, jedes Mal mit einem anderen Favoriten vorn. Nur Favoriten: Alle anderen Kapitel werden übersprungen, nach dem letzten Favoriten hält die Box an. Nur Favoriten zur Schlafenszeit: tagsüber Favoriten zuerst, innerhalb einer Schlafenszeit der Box nur die Favoriten. Der Anfang eines übersprungenen Kapitels kann kurz zu hören sein; ohne Internet oder Home Assistant spielt die Box wie immer.",
    favMode_account: "Wie im Konto ({m})", favMode_off: "Wie die Box spielt, Sterne bleiben", favMode_first: "Favoriten zuerst",
    favMode_random: "Zufälliger Favorit zuerst", favMode_only: "Nur Favoriten", favMode_bedtime: "Nur Favoriten zur Schlafenszeit",
    favNow_first: "Favoriten zuerst", favNow_random: "Favoriten zuerst", favNow_only: "Nur Favoriten", favNowAll: "Heute alles",
    favAll: "Heute alles", favAllOn: "Alle Kapitel spielen, bis die Figur abgenommen wird",
    favAllOff: "Alle Kapitel spielen, bis die Figur abgenommen wird. Wieder nach den Favoriten spielen",
    prefFavourites: "Favoriten", prefFavMode: "So spielen Favoriten",
    prefFavModeHint: "Auf einer Toniebox 2, für jede Figur mit Stern, die keine eigene Einstellung hat. Favoriten zuerst: Aufgesetzt beginnt eine Figur mit ihren Favoriten und spielt danach die übrigen Kapitel. Zufälliger Favorit zuerst: dasselbe, jedes Mal mit einem anderen Favoriten vorn. Nur Favoriten: Alle anderen Kapitel werden übersprungen, nach dem letzten Favoriten hält die Box an. Nur Favoriten zur Schlafenszeit: tagsüber Favoriten zuerst, innerhalb einer Schlafenszeit der Box nur die Favoriten. Dieselbe Figur, innerhalb von zwei Minuten wieder aufgesetzt, spielt dort weiter, wo sie war.",
    pgFavourites: "Favoriten", favListNone: "Noch hat kein Kapitel einen Stern. Öffne eine Figur und markiere ihre besten Kapitel, oder tippe auf den Stern des Kapitels, das gerade läuft.",
    favListHelp: "Alle Kapitel mit Stern. Ein Kapitel einer Figur, die auf einer Toniebox 2 steht, spielt mit einem Tipp.",
    favPlay: "Auf {box} spielen", favOnBox: "auf {box}",
    statFav: "Favoriten", statFavShare: "der Hörzeit entfielen auf Favoriten",
    statFavHelp: "Gezählt nach den Sternen, wie sie jetzt sind, über die Zeit, deren Kapitel bekannt ist. Kapitel von Kreativ-Tonies werden nach ihrer Position gezählt; neu angeordnet mischen sich ihre Zeiten.",
    statFavNone: "Noch hat kein Kapitel einen Stern.",
    statHidden: "Viel gehört, noch ohne Stern", statHiddenHelp: "Die Kapitel ohne Stern, die am längsten gehört wurden: Favoriten, die noch niemand markiert hat. Der Stern markiert sie.",
    statUnheard: "Sterne, kaum gehört", statUnheardHelp: "Favoriten, die in diesen Tagen weniger als eine Minute gehört wurden, von Figuren, die gehört wurden. Der Stern nimmt sie aus den Favoriten.",
    statPlays: "etwa {n}×",
    tune: "Tune", tuneOn: "Tune darauf: {t}", tuneRemove: "Tune abnehmen", tunePick: "Gekaufter Tune", tuneAssign: "Auflegen",
    tuneLeft: "noch {n}-mal", tuneHintCreative: "Die Kapitel der Figur bleiben erhalten und spielen wieder, sobald der Tune abgenommen wird.",
    tuneHint: "Die Figur spielt den Tune statt ihrer eigenen Geschichte, bis er abgenommen wird.",
    tunesTitle: "Gekaufte Tunes", tunesHelp: "Ein Tune ist gekaufter Inhalt, der statt der eigenen Geschichte auf einer passenden Figur liegt; aufgelegt wird er in der Ansicht Tune der Figur.",
    noTunes: "Noch kein Tune im Konto.", tuneOnFigure: "auf {f}", tuneInUse: "aufgelegt",
    prefVoucher: "Tunes-Gutschein", voucherCode: "Gutscheincode", voucherRedeem: "Einlösen",
    voucherDone: "Eingelöst: {n} Tunes hinzugefügt.", voucherNone: "Eingelöst, die Cloud nennt aber keinen neuen Tune.",
    voucherHint: "Ein Gutschein lässt sich einmal einlösen; die Tunes erscheinen danach bei den Figuren, zu denen sie passen.",
    fromCode: "Inhalt per Code", codePlaceholder: "Inhaltscode", codeFigure: "Kreativ-Tonie",
    codeHint: "Fertige Inhalte zu einem Code (etwa von einer Karte) kommen auf die Figur; die Cloud wandelt sie danach um.",
    codeAdded: "Der Inhalt ist auf {f} hinzugefügt.",
    fromLink: "Von YouTube", linkPlaceholder: "Link zu einem YouTube-Video",
    linkHint: "Der Ton des Videos wird ein Kapitel, benannt nach dem Video. Er wird über Home Assistant geholt.",
    linkProbe: "Liest das Video …", linkFetch: "Holt {name} …", linkFetchPct: "Holt {name} ({p} %) …",
    linkConvert: "Wandelt {name} um …", linkUpload: "Lädt {name} in die Cloud hoch …",
    fetcherMissing: "Braucht die App Media Fetcher.", fetcherHelp: "In Home Assistant unter Einstellungen → Apps installieren; sie holt den Ton eines Videos.",
    fromText: "Aus Text", textTitle: "Titel (optional)", textBody: "Text zum Vorlesen",
    textHint: "Eine Stimme von Home Assistant spricht den Text; die Aufnahme wird ein Kapitel. Mit Piper bleibt der Text im Haus; eine in den Einstellungen gewählte Stimme eines Cloud-Dienstes bekommt den Text.",
    speechMissing: "Braucht eine Stimme.", speechHelp: "In Home Assistant die Wyoming-Integration mit Piper einrichten oder unter Einrichtung → Einstellungen eine andere Sprachausgabe-Entität wählen.",
    textBusy: "Die Stimme spricht den Text, er geht in die Cloud …", textAdded: "Der gesprochene Text ist als Kapitel hinzugefügt.", linkAdded: "„{name}“ ist als Kapitel hinzugefügt.",
    uploading: "Lädt {name} hoch ({n} von {m}) …",
    range_7: "7 Tage", range_30: "30 Tage", range_365: "365 Tage", range_all: "Alles", rangeLabel: "Zeitraum",
    lastDays: "letzte {n} Tage", since: "seit {d}", sinceSetup: "seit der Einrichtung",
    total: "Hörzeit", top: "Meistgehört", topPlaced: "Am häufigsten aufgelegt", placedTimes: "{n}×", perDay: "Pro Tag", perWeek: "Pro Woche", perBox: "Hörzeit der Toniebox 2",
    weekOf: "Woche vom {d}", allBoxes: "Alle Boxen", heatBoxLabel: "Box", vsBefore: "{p} gegenüber den {n} Tagen davor",
    chartDays: "Hörzeit an {n} Tagen, zusammen {total} h; am meisten am {top} mit {v} h.",
    chartWeeks: "Hörzeit in {n} Wochen, zusammen {total} h; am meisten in der {top} mit {v} h.",
    topChapters: "Meistgehörte Kapitel", whenListened: "Wann gehört wird",
    whenHint: "Über den Zeitraum summiert, je Wochentag und Stunde; einzelne Wiedergaben werden nicht gespeichert.",
    noteLocal: "Home Assistant zählt die Hörzeit selbst mit, aus dem, was eine Toniebox 2 live meldet. Sie stammt nicht aus der Hersteller-Cloud und ist deshalb nicht vollständig: Sie beginnt mit der Einrichtung, die Toniebox 1 fehlt, und Zeiten, in denen Home Assistant nicht lief, fehlen ebenso.",
    disabled: "Das Zählen ist ausgeschaltet.", disabledHelp: "Unter Einrichtung → Einstellungen einschalten; es zählt ab dann.",
    noStats: "Noch nichts gezählt.",
    bedtimes: "Schlafenszeiten", addSchedule: "Hinzufügen", scheduleNew: "Neue Schlafenszeit", scheduleUnnamed: "Schlafenszeit",
    noSchedules: "Noch keine Schlafenszeit.", schedulesUnknown: "Die Schlafenszeiten ließen sich noch nicht lesen.",
    schedulesUnknownHelp: "Die Cloud nennt sie mit der nächsten Abfrage; in einer Minute aktualisieren.",
    everyDay: "täglich", alarmOn: "Wecker", scheduleOn: "Schlafenszeit aktiv", confirmDelete: "Die Schlafenszeit {name} löschen?",
    nextAlarm: "Nächster Wecker {t}", alarmArmed: "auf der Box gestellt", alarmPending: "wird gestellt, sobald die Box online ist",
    alarmLater: "wird am Vorabend gestellt",
    alarmHint: "Eine Schlafenszeit mit Wecker weckt das Kind an den gewählten Tagen. Home Assistant stellt den Wecker jeden Abend auf der Box, sobald sie online ist; die App stellt ihn nur einmal. Solange ein Wecker ansteht, lehnt die Integration den Schlaf-Timer und das Ausschalten der Box ab, weil die Box nur einen Timer kennt.",
    f_name: "Name", f_days: "Tage des Weckens", f_sleep_time: "Schlafenszeit", f_wakeup_time: "Wecken",
    f_enabled: "Aktiv", f_alarm_enabled: "Wecker beim Wecken", f_alarm_volume: "Lautstärke des Weckers", f_alarm_morning_light: "Sonnenaufgangs-Licht",
    deleteSchedule: "Löschen",
    wakeUpLight: "Lichtwecker", noWakeUpLight: "Kein Lichtwecker gestellt.", setWakeUpLight: "Stellen", f_at: "Datum und Uhrzeit", f_tone: "Weckton", tone1: "Morgenglanz", tone2: "Vogelgezwitscher-Rhythmus", tone3: "Klanghüpfer", tone4: "Aufwach-Ruf", tone5: "Guten-Morgen-Beat", e_alarm_too_soon: "Eine Zeit mindestens 5 Minuten ab jetzt wählen; einen näheren Wecker nimmt die Box nicht an.",
    wakeUpLightHint: "Ein Wecker zu einer eigenen Zeit, wie der Lichtwecker der App: mit Weckton, Lautstärke und Sonnenaufgangs-Licht. Er braucht eine Zeit mindestens 5 Minuten im Voraus. Home Assistant stellt ihn auf der Box, sobald er weniger als 18 Stunden entfernt ist und die Box online ist; kommt die Box erst weniger als 5 Minuten vorher online, fällt er aus. Klingelt der Wecker einer Schlafenszeit früher, wird zuerst dieser gestellt und der Lichtwecker danach. Hat er geklingelt, ist er weg.",
    headphones: "Kopfhörer", headphonesBattery: "Kopfhörer, Akku {p} %",
    repeatOff: "Wiederholen: aus", repeatAll: "Wiederholen: ganze Figur", repeatOne: "Wiederholen: dieses Kapitel",
    ctlTracks: "Kapitel", tracksTitle: "Kapitel",
    ctlPrev: "Vorheriges Kapitel", ctlNext: "Nächstes Kapitel", ctlPlay: "Abspielen", ctlPause: "Pausieren", ctlLouder: "Lauter", ctlQuieter: "Leiser",
    ctlSleep: "Schlaf-Timer {m} Min.", ctlSleepTitle: "Schlaf-Timer", sleepMin: "{m} Min.", sleepOwn: "Andere Dauer in Minuten", sleepStart: "Starten", ctlSleepOff: "Schlaf-Timer abbrechen",
    boxSettingsOf: "Einstellungen der Box", settingsPending: "Wartet auf die Box", offlineMode: "Offline-Modus",
    offlineHelp: "Die Box ist auf Betrieb ohne Cloud gestellt; Änderungen übernimmt sie erst, wenn sie wieder online ist.",
    noSettings: "Die Cloud nennt keine Einstellungen dieser Box.",
    settingsHint: "Die Box übernimmt die Einstellungen, sobald sie das nächste Mal online ist.",
    s_name: "Name", h_name: "So, wie die App und Home Assistant die Box zeigen.",
    s_max_volume: "Maximale Lautstärke", h_max_volume: "Am lautesten spielt die Box so über ihren Lautsprecher. Eine Toniebox 1 kennt 25, 50, 75 und 100 %.",
    s_max_headphone_volume: "Maximale Kopfhörer-Lautstärke", h_max_headphone_volume: "Am lautesten spielt die Box so über Kopfhörer.",
    s_lightring_brightness: "Helligkeit des Lichtrings", h_lightring_brightness: "Wie hell der Ring der Box leuchtet; 0 % ist aus.",
    s_bedtime_lightring_brightness: "Lichtring in der Schlafenszeit", h_bedtime_lightring_brightness: "Die Helligkeit des Rings, solange eine Schlafenszeit läuft.",
    s_bedtime_max_volume: "Maximale Lautstärke in der Schlafenszeit", h_bedtime_max_volume: "Am lautesten spielt der Lautsprecher so, solange eine Schlafenszeit läuft.",
    s_bedtime_max_headphone_volume: "Maximale Kopfhörer-Lautstärke in der Schlafenszeit", h_bedtime_max_headphone_volume: "Am lautesten spielen die Kopfhörer so, solange eine Schlafenszeit läuft.",
    s_skipping_enabled: "Kapitel per Klopfen überspringen", h_skipping_enabled: "Ein Klopfen auf die Seite der Box springt zum nächsten oder vorigen Kapitel.",
    s_skipping_direction: "Ohr für vorwärts", h_skipping_direction: "Welche Seite der Box beim Klopfen vorwärts springt.",
    s_scrubbing_enabled: "Spulen per Kippen", h_scrubbing_enabled: "Kippen der Box spult im Kapitel vor oder zurück.",
    s_accelerometer_enabled: "Kippen und Klopfen", h_accelerometer_enabled: "Ob die Box überhaupt auf Kippen und Klopfen reagiert.",
    s_tap_direction: "Klopfrichtung", h_tap_direction: "Welche Seite einer Toniebox 1 beim Klopfen vorwärts springt.",
    s_led_level: "LED", h_led_level: "Das Licht einer Toniebox 1: an, gedimmt oder aus.",
    s_age_mode: "Altersmodus", h_age_mode: "1+ macht eine Toniebox 2 für die Kleinsten einfacher; 3+ erlaubt alle Gesten.",
    s_language: "Sprache", h_language: "Die Sprache, in der die Box ihre eigenen Ansagen spricht.",
    v_left: "Links", v_right: "Rechts", v_on: "An", v_off: "Aus", v_dimmed: "Gedimmt", sOn: "an", sOff: "aus",
    sumVolume: "max. {v} %", volumeLevel: "Stufe {v} von {max}", sumRing: "Lichtring {v} %", sumSkip: "Überspringen an", sumLed: "LED {v}",
    sumPhones: "Kopfhörer {v} %", sumTilt: "Spulen durch Kippen",
    nightMode: "Nachtmodus des Lichtrings", nightNow: "Gerade Nacht: der Lichtring ist gedimmt", dayNow: "Gerade Tag: der Lichtring ist hell",
    nightPhaseHelp: "Home Assistant wechselt zu Beginn und am Ende der Nacht zwischen den beiden Helligkeiten.",
    nightHint: "Home Assistant dimmt den Lichtring zu Beginn und stellt ihn am Ende zurück; eine Helligkeit, die zwischendurch in der App gesetzt wird, bleibt bis zum nächsten Wechsel. Die Box übernimmt es, sobald sie online ist.",
    n_enabled: "Aktiv", h_n_enabled: "Ausgeschaltet behält der Lichtring seine Helligkeit.",
    n_start: "Von", h_n_start: "Wann die Nacht beginnt.", n_end: "Bis", h_n_end: "Wann die Nacht endet; das darf am nächsten Tag sein.",
    n_night: "Lichtring nachts", h_n_night: "Die Helligkeit in der Nacht; 0 % ist aus.",
    n_day: "Lichtring sonst", h_n_day: "Die Helligkeit, die der Ring am Ende der Nacht zurückbekommt.",
    setupTitle: "Einrichtung", setupHelp: "Die Schritte in ihrer Reihenfolge; Weiter führt zum ersten offenen.",
    stepAccount: "Konto geladen", stepHousehold: "Haushalt benannt", stepPreferences: "Einstellungen gewählt",
    stepDone: "Erledigt", stepOpen: "Offen", sOpen: "Offen",
    extrasTitle: "Optional", stepFetcher: "App Media Fetcher", stepPiper: "Stimme für Texte",
    sInstalled: "Bereit", sOptional: "Nicht eingerichtet",
    h_fetcher: "Holt den Ton eines YouTube-Videos für ein Kapitel. In Home Assistant unter Einstellungen → Apps installieren.",
    h_piper: "Spricht einen Text für ein Kapitel. In Home Assistant die Wyoming-Integration mit Piper einrichten oder in den Einstellungen eine andere Sprachausgabe-Entität wählen.",
    prefAnalyticsShort: "Zählen", prefAutoLockShort: "Sperren", prefMarkReadShort: "Als gelesen markieren",
    prefHousehold: "Haushalt", householdName: "Name des Haushalts", h_householdName: "So, wie die App ihn allen Mitgliedern zeigt.",
    noHouseholds: "Das Konto hat noch keinen Haushalt.",
    membersCount: "Mitglieder ({n})", membersUnknown: "Die Mitglieder konnten noch nicht gelesen werden.", memberYou: "Du",
    role_owner: "Besitzer", role_full: "Voller Zugriff", role_limited: "Eingeschränkter Zugriff", role_unknown: "Unbekannte Rolle",
    membersHint: "So, wie die Cloud sie diesem Konto zeigt; Mitglieder und Einladungen werden in der App verwaltet.",
    prefListening: "Hörzeit", prefAnalytics: "Hörzeit zählen",
    prefKeep: "Hörzeit aufbewahren", prefKeepHint: "Ältere Tage werden gelöscht; die Summen sind klein, alle können bleiben.",
    prefKeep_365: "1 Jahr", prefKeep_730: "2 Jahre", prefKeep_1825: "5 Jahre", prefKeep_0: "Immer",
    prefChapters: "Neue Kapitel", prefEngine: "Sprachausgabe für Texte", prefEngineHint: "Die Sprachausgabe-Entität von Home Assistant, die einen Text als Kapitel spricht. Leer: Piper, die lokale Stimme, falls eingerichtet; der Text bleibt dann im Haus. Die Stimme eines Cloud-Dienstes bekommt den Text zum Sprechen, und lange Texte können mehr sein, als er auf einmal annimmt.", prefVoice: "Stimme für Texte", prefVoiceHint: "Die Stimme, die einen Text als Kapitel spricht, in der Sprache der Seite. Eine Stimme, die Piper noch nicht hat, lädt es beim ersten Mal; das dauert einen Moment.",
    prefVoiceDefault: "Standardstimme", prefVoiceNone: "Keine Stimme eingerichtet",
    prefFetchMax: "Größte Datei aus einem Link", prefFetchMaxHint: "Liefert die App Media Fetcher eine größere Datei, wird sie abgelehnt. Eine Figur fasst 90 Minuten, als M4A etwa 90 MB. 10 bis 2000 MB.",
    prefAnalyticsHint: "Speichert Summen je Tag, Figur, Box, Kapitel und Stunde für den Bereich Hörzeit, nie einzelne Wiedergaben. Ausgeschaltet werden die Summen gelöscht.",
    prefFigures: "Figuren", prefAutoLock: "Neue Figuren und Discs für den Haushalt sperren",
    prefAutoLockHint: "Eine gekaufte Figur oder Disc, die neu im Konto ist, wird einmal gesperrt, damit sie nicht in einen anderen Haushalt übernommen werden kann. Auf ihrer Seite oder in der App entsperrt, bleibt sie entsperrt.",
    prefNotices: "Benachrichtigungen", prefMarkRead: "Benachrichtigungen nach dem Weiterreichen in der Cloud als gelesen markieren",
    prefMarkReadHint: "Die App zeigt sie dann nicht mehr. Rundrufe an alle Nutzer werden stattdessen geschlossen.",
    prefCloud: "Cloud",
    cloudUnknown: "Die Version der Cloud ist noch nicht bekannt.",
   
    cloudCheck: "Cloud-Schnittstelle testen",
    cloudFits: "Die Cloud passt zu dieser Version.",
    cloudNew: "Die Cloud wurde aktualisiert. Der Test zeigt, ob noch alles passt.",
    cloudBad: "Die Cloud antwortet anders, als diese Version erwartet. Manches funktioniert vielleicht nicht.",
    cloudDetail: "Backend-Version {v}, getestet mit {t}.",
    cloudChecked: "Zuletzt getestet am {d}.",
    cloudCheckHelp: "Aktualisiert der Hersteller seine Cloud, testet Storybox Plus von selbst, ob noch alles passt. Der Test liest nur und ändert nichts.",
   
   
   
    cloudIssue: "Auf GitHub melden",
    cloudIssueHelp: "Öffnet ein neues Issue mit dem, was der Test gefunden hat. Es nennt Abfragen, Felder und Versionen, nichts aus deinem Konto.",
   
    openFigure: "Figur öffnen",
  },
};

// The languages tonies offers figures in. English and German are above; the
// others are files of their own beside this module, fetched with its version
// when a user first needs them. Until one has arrived, and for any other
// language, the texts are English; a text missing in a language is English too.
export const LANGUAGES = ["de", "en", "es", "fr", "it", "nl", "pl", "pt-BR"];
const loading = {};
const waiting = {};
export const langKey = (lang) => {
  const code = String(lang || "en").toLowerCase();
  return LANGUAGES.find((l) => l.toLowerCase() === code) || LANGUAGES.find((l) => l === code.split(/[-_]/)[0]) || "en";
};
// The texts of a language; onLoad is called once when a language that had to be
// fetched has arrived, so the caller can draw itself again
export const textsFor = (lang, onLoad) => {
  const key = langKey(lang);
  if (TEXTS[key]) return TEXTS[key];
  if (onLoad) (waiting[key] ||= new Set()).add(onLoad);
  loading[key] ||= import(new URL(`./storybox-plus-texts-${key}.js${new URL(import.meta.url).search}`, import.meta.url).href)
    .then((module) => ({ ...TEXTS.en, ...module.default }), () => TEXTS.en)
    .then((texts) => {
      TEXTS[key] = texts;
      for (const done of waiting[key] || []) done();
      delete waiting[key];
    });
  return TEXTS.en;
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
// The times the sleep timer's dialog offers, and the longest the box takes
const SLEEP_MINUTES = [15, 30, 45, 60];
const SLEEP_MAX_MINUTES = 1092;
export const WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];
// "HH:MM" from Home Assistant's time field, which adds seconds
export const clock = (v) => (typeof v === "string" && /^\d{1,2}:\d{2}/.test(v) ? v.split(":").slice(0, 2).map((x) => x.padStart(2, "0")).join(":") : null);

// Numbers as Home Assistant writes them: the number format of the user's profile,
// by default that of the language
export const numberLocale = (hass) => {
  const format = hass?.locale?.number_format;
  if (format === "system") return undefined;
  return { comma_decimal: "en-US", decimal_comma: "de", space_comma: "fr", none: "en-US" }[format] ||
    hass?.locale?.language || hass?.language || "en";
};
// A number for reading, with d decimals
export const formatNumber = (hass, v, d = 0) => (Number.isFinite(v)
  ? v.toLocaleString(numberLocale(hass), { minimumFractionDigits: d, maximumFractionDigits: d, useGrouping: hass?.locale?.number_format !== "none" })
  : "–");
// A number in a text field, and back: typing takes a point or a comma
export const fieldNumber = (hass, v) => (Number.isFinite(v) ? v.toLocaleString(numberLocale(hass), { useGrouping: false, maximumFractionDigits: 3 }) : "");
// How the user's profile wants a time written: 12 or 24 hours (else the language's
// way) and, where the profile says so, in Home Assistant's time zone
export const timeOptions = (hass) => ({
  ...(hass?.locale?.time_format === "12" ? { hourCycle: "h12" } : hass?.locale?.time_format === "24" ? { hourCycle: "h23" } : {}),
  ...(hass?.locale?.time_zone === "server" && hass?.config?.time_zone ? { timeZone: hass.config.time_zone } : {}),
});
export const numOrNull = (v) => {
  const n = parseFloat(String(v).replace(",", "."));
  return Number.isFinite(n) && /^\s*[-+]?\d*[.,]?\d*\s*$/.test(String(v)) ? n : null;
};

// Error codes that read like a more general one
const SAME_ERROR = { unknown_entry: "not_loaded", unknown_box: "not_found", unknown_figure: "not_found" };

// What the page and the card share of their look: the base, a box's card, the
// badges; in the colours and sizes of the active theme
export const STYLE = `
/* The panel's own container has no height of its own: the page takes the window */
:host { display: block; height: 100vh; height: 100dvh; background: var(--primary-background-color); color: var(--primary-text-color);
  font-family: var(--ha-font-family-body, Roboto, Noto, sans-serif); font-size: var(--ha-font-size-m, 14px); line-height: 1.5;
  -webkit-font-smoothing: antialiased; }
* { box-sizing: border-box; }
ha-card { display: block; overflow: hidden; }
ha-card .card-header { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 0; }
/* A box's head stays one line: the name gives way, the volume, battery and cog keep their place */
ha-card .card-header:has(> .status) { flex-wrap: nowrap; }
.card-header > .box-name { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.card-header > .status { flex: none; }
/* On a phone the volume and the battery take a line of their own below the name */
@media (max-width: 450px) {
  ha-card .card-header:has(> .status) { flex-wrap: wrap; row-gap: 2px; }
  .card-header > .status { order: 1; flex-basis: 100%; margin-left: 0; }
  .card-header > .status:empty { display: none; }
  .card-header > .box-cog { margin-left: auto; }
}
.card-content { padding: 0 16px 16px; }
.card-content.bare { padding-top: 16px; }
ha-alert { display: block; }
ha-svg-icon { flex: none; }
ha-badge.chip { --ha-badge-size: 24px; --ha-badge-font-size: var(--ha-font-size-xs, 12px); --ha-badge-border-radius: 12px; white-space: nowrap; }
ha-badge.chip.ok { --badge-color: var(--success-color); color: var(--success-color); }
ha-badge.chip.warn { --badge-color: var(--warning-color); color: var(--warning-color); }
ha-badge.chip.on, ha-badge.chip.fav { --badge-color: var(--primary-color); color: var(--primary-color); }
.chips { display: inline-flex; gap: 6px; flex-wrap: wrap; align-items: center; }
.tile-title { font-weight: var(--ha-font-weight-medium, 500); margin-bottom: 4px; }
.status { display: inline-flex; align-items: center; gap: 16px; margin-left: auto; font-size: var(--ha-font-size-m, 14px);
  color: var(--secondary-text-color); font-weight: var(--ha-font-weight-normal, 400); }
.dot { width: 10px; height: 10px; border-radius: 50%; flex: none; background: var(--secondary-text-color); opacity: 0.6; }
.dot.ok { background: var(--success-color); opacity: 1; }
.dot.err { background: var(--error-color); opacity: 1; }
.card-header .dot { margin-left: 4px; }
.facts { display: flex; flex-wrap: wrap; gap: 6px 20px; margin-bottom: 12px; }
.fact { display: inline-flex; align-items: center; gap: 6px; font-variant-numeric: tabular-nums; }
.fact ha-svg-icon { --mdc-icon-size: 20px; color: var(--secondary-text-color); }
.fact.pending { opacity: .6; }
.batt-btn { cursor: pointer; border-radius: 6px; }
.batt-btn:hover { color: var(--primary-text-color); }
.batt-btn:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
.charge { display: inline-flex; align-items: center; color: var(--success-color); font-size: var(--ha-font-size-xs, 12px); }
.charge ha-svg-icon, .state ha-svg-icon { --mdc-icon-size: 16px; color: inherit; }
/* The battery drawn as large and in the colour of the icons beside it: a 20 px box like
   theirs, the body as tall as their glyphs; red only when it runs low */
.batt { position: relative; flex: none; width: 20px; height: 20px; display: inline-block; }
.batt b { position: absolute; left: 6px; top: 4px; width: 8px; height: 14px; box-sizing: border-box;
  border: 1.5px solid var(--secondary-text-color); border-radius: 2px; }
.batt b::before { content: ""; position: absolute; top: -3.5px; left: 1.5px; right: 1.5px; height: 2px; background: var(--secondary-text-color); border-radius: 1px 1px 0 0; }
.batt i { position: absolute; left: 1px; right: 1px; bottom: 1px; max-height: calc(100% - 2px); background: var(--secondary-text-color); border-radius: 0.5px; }
.batt.low i { background: var(--error-color); }
.play { display: flex; align-items: center; gap: 12px; }
.now-star { flex: none; color: var(--secondary-text-color); }
span.now-star { display: inline-flex; padding: 8px; }
.now-star.on, ha-icon-button.star.on { color: var(--state-active-color, var(--amber-color, #ffc107)); }
ha-icon-button.fav-all.on { color: var(--primary-color); }
.tracks ha-icon-button { flex: none; margin: -8px 0; --ha-icon-button-size: 36px; --mdc-icon-button-size: 36px; color: var(--secondary-text-color); }
.pic { position: relative; flex: none; width: 56px; height: 56px; border-radius: 8px; overflow: hidden;
  background: color-mix(in srgb, var(--primary-text-color) 6%, transparent); color: var(--secondary-text-color); }
.pic ha-svg-icon { position: absolute; left: 50%; top: 50%; --mdc-icon-size: 28px; transform: translate(-50%, -50%); opacity: 0.6; }
.pic img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; background: var(--card-background-color); }
.pic img.broken { display: none; }
.pic.small { width: 40px; height: 40px; border-radius: 6px; }
.pic.small ha-svg-icon { --mdc-icon-size: 20px; }
.text { display: flex; flex: 1; flex-direction: column; min-width: 0; }
.headline { line-height: 20px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fig-open { cursor: pointer; border-radius: 8px; }
.fig-open:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
.headline.fig-open:hover { text-decoration: underline; }
.pic-open { display: inline-flex; flex: none; }
.supporting { font-size: var(--ha-font-size-xs, 12px); line-height: 16px; color: var(--secondary-text-color); margin-top: 2px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.state { display: inline-flex; align-items: center; gap: 4px; }
.state.ok { color: var(--success-color); }
.state.warn { color: var(--warning-color); }
.progress { margin-top: 10px; }
.bar { position: relative; height: 6px; border-radius: 3px; background: color-mix(in srgb, var(--primary-text-color) 10%, transparent); overflow: hidden; }
.bar div { height: 100%; border-radius: 3px; background: var(--primary-color); transition: width 0.5s linear; }
.times { display: flex; justify-content: space-between; margin-top: 4px; font-size: var(--ha-font-size-xs, 12px);
  color: var(--secondary-text-color); font-variant-numeric: tabular-nums; }
.muted { color: var(--secondary-text-color); }
.small { font-size: var(--ha-font-size-xs, 12px); line-height: 16px; margin-top: 8px; }
.tracks { list-style: none; margin: 0 -12px; padding: 0 0 8px; }
.tracks li { display: flex; align-items: center; gap: 12px; padding: 10px 12px; border-radius: 12px; cursor: pointer; }
.tracks li:hover, .tracks li:focus-visible { background: var(--secondary-background-color); outline: none; }
.tracks li.current { color: var(--primary-color); font-weight: 500; }
.tracks li[aria-disabled=true] { cursor: default; opacity: 0.6; }
.tracks .rank { flex: none; width: 24px; text-align: right; color: var(--secondary-text-color); }
.tracks .name { flex: 1 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tracks .len { flex: none; color: var(--secondary-text-color); font-variant-numeric: tabular-nums; }
ha-icon-button.repeat.on { color: var(--primary-color); }
.controls { display: flex; flex-wrap: wrap; align-items: center; gap: 2px; margin: 8px 0 4px; }
.ctl-gap { width: 12px; }
.sleep-set { display: flex; flex-direction: column; gap: 16px; padding-bottom: 8px; }
.sleep-quick { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.sleep-free { display: flex; align-items: center; gap: 12px; }
.sleep-free label { display: flex; flex: 1 1 auto; align-items: center; gap: 12px; min-width: 0; }
.sleep-free span { flex: 1 1 auto; }
.sleep-own { flex: none; width: 72px; box-sizing: border-box; padding: 8px 10px; font: inherit; text-align: right; color: var(--primary-text-color);
  background: var(--secondary-background-color); border: 1px solid var(--divider-color); border-radius: 8px; }
.sleep-own:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 1px; }
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
ha-icon-button { --mdc-icon-button-size: 36px; --mdc-icon-size: 20px; color: var(--secondary-text-color); flex: none; }
.actions ha-icon-button { --mdc-icon-button-size: 48px; --mdc-icon-size: 24px; color: inherit; }
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
      // Counted, so whatever is kept per language is drawn anew with the texts
      this._textsArrived ||= () => {
        this._textsVersion = (this._textsVersion || 0) + 1;
        this._render?.();
      };
      return textsFor(this._lang, this._textsArrived);
    }

    // A number in the number format of the user's profile
    _fmt(v, d = 0) {
      return formatNumber(this._hass, Number(v), d);
    }

    // An error of a call: one line by its kind, what Home Assistant said for behind an (i)
    _error(err) {
      const t = this._t;
      const e = err && typeof err === "object" && err.error && typeof err.error === "object" ? err.error : err;
      let code = e && typeof e === "object" ? e.code : null;
      const said = typeof e === "string" ? e : typeof e?.message === "string" ? e.message : "";
      if (typeof e === "number" || [1, 2, 3].includes(code) || (!code && /connection (lost|closed)|failed to fetch|socket/i.test(said))) code = "connection";
      code = SAME_ERROR[code] || code;
      const text = (typeof code === "string" && t[`e_${code}`]) || t.e_other;
      return { text, detail: said && said !== text ? said : "" };
    }

    // The line of an error; the page adds Home Assistant's message behind an (i)
    _errHtml(e) {
      return this._alert(e.text, "error");
    }

    _relative(iso) {
      const ms = time(iso);
      if (!Number.isFinite(ms)) return this._t.never;
      const diff = (ms - Date.now()) / 1000;
      const abs = Math.abs(diff);
      const [unit, div] = abs < 60 ? ["second", 1] : abs < 3600 ? ["minute", 60] : abs < 86400 ? ["hour", 3600] : ["day", 86400];
      return new Intl.RelativeTimeFormat(this._lang, { numeric: "auto" }).format(Math.round(diff / div), unit);
    }

    // A card of Home Assistant; the title is HTML (a box's name with its badges and status)
    _card(title, body, extra = "", footer = "") {
      return `<ha-card class="${extra.trim()}">${title ? `<h1 class="card-header">${title}</h1>` : ""}` +
        `<div class="card-content${title ? "" : " bare"}">${body}</div>${footer}</ha-card>`;
    }

    // A state in a word: Home Assistant's badge
    _chip(text, kind = "") {
      return `<ha-badge class="chip ${kind}">${esc(text)}</ha-badge>`;
    }

    // kind: "info", "warning", "error", "success"
    _alert(text, kind = "info", title = "", action = "") {
      return `<ha-alert alert-type="${kind}"${title ? ` title="${esc(title)}"` : ""}>${esc(text)}${action}</ha-alert>`;
    }

    _pic(url, extra = "") {
      const src = safeUrl(url);
      return `<div class="pic${extra}">${icon("figures")}${src ? `<img src="${esc(src)}" alt="" loading="lazy">` : ""}</div>`;
    }

    // Online or offline as a small dot, the word in its tooltip and for a screen reader
    _dot(b) {
      const t = this._t;
      const [state, label] = b.online === true ? ["ok", t.online] : b.online === false ? ["err", t.offline] : ["", t.unknown];
      const seen = b.online !== true && b.last_seen ? ` · ${fill(t.lastSeen, { t: this._relative(b.last_seen) })}` : "";
      return `<span class="dot ${state}" role="img" title="${esc(label + seen)}" aria-label="${esc(label + seen)}"></span>`;
    }

    // card: the dashboard card's configuration, null on the page. The card has neither the
    // cog nor the battery's view, and leaves out each part its show_<part> turns off.
    _box(b, showHousehold, card = null) {
      const { title, body } = this._boxParts(b, showHousehold, card);
      return this._card(title, body);
    }

    // The head and the body of a box's card, for a card that draws its own frame
    _boxParts(b, showHousehold, card = null) {
      const t = this._t;
      const live = b.generation === "toniebox_2";
      const show = (part) => !card || card[`show_${part}`] !== false;
      const chips = showHousehold && b.household ? this._chip(b.household) : "";
      const pic = show("picture") ? safeUrl(b.image_url) : null;
      // Settings, night mode and bedtimes open as the box's page
      const cog = !card && (b.settings || b.bedtime) ? iconButton("cog", t.boxSettingsOf, `class="box-cog" data-act="boxset:${esc(b.id)}"`) : "";
      // The battery's level sits in the head; on the page it opens the box's battery
      // Without a level (the box has not reported one since Home Assistant started) no battery shows;
      // an offline box keeps the last level it reported
      const batt = !live || !show("battery") || !Number.isFinite(b.battery) ? "" : card
        ? `<span class="fact">${this._batteryLevel(b)}</span>`
        : b.battery_stats
          // A plain button, so it sits like the volume beside it, without a button's padding
          ? `<span class="fact batt-btn" role="button" tabindex="0" data-act="battset:${esc(b.id)}" title="${esc(t.batteryDetails)}">${this._batteryLevel(b)}</span>`
          : `<span class="fact">${this._batteryLevel(b)}</span>`;
      // The volume sits in the head beside the battery
      let vol = "";
      if ((Number.isFinite(b.volume) || Number.isFinite(b.volume_percent)) && show("volume")) {
        // The box's own percent once it reported the level; a level just sent shows as a level.
        // The dashboard card knows the percent only: the media player's volume
        const sent = this._volSent?.box === b.id;
        const level = Number.isFinite(b.volume) ? fill(t.volumeLevel, { v: this._fmt(b.volume), max: this._fmt(b.volume_max ?? 13) }) : "";
        const shown = Number.isFinite(b.volume_percent) && !sent ? `${this._fmt(b.volume_percent)} %` : level;
        vol = `<span class="fact vol${sent ? " pending" : ""}"${level ? ` title="${esc(level)}"` : ""}>${icon("volume")}${esc(shown)}</span>`;
      }
      const title = `${pic ? `<img class="box-pic" src="${esc(pic)}" alt="">` : ""}<span class="box-name">${esc(b.name || b.id)}</span>${this._dot(b)}` +
        `<span class="chips">${chips}</span><span class="status">${vol}${batt}</span>${cog}`;
      const facts = [];
      if (b.headphones?.connected && show("headphones")) {
        const hp = Number.isFinite(b.headphones.battery) ? fill(t.headphonesBattery, { p: this._fmt(b.headphones.battery) }) : t.headphones;
        facts.push(`<span class="fact">${icon("headphones")}${esc(hp)}</span>`);
      }
      const sleep = this._sleep(b.sleep_timer);
      if (sleep && show("sleep_timer")) facts.push(`<span class="fact">${icon("sleep")}${esc(sleep)}</span>`);
      // The next alarm and a night mode at work stay on the card; the rest is behind the cog
      const next = b.bedtime?.next_alarm;
      if (next && show("next_alarm")) {
        const when = new Date(time(next.at)).toLocaleString(this._lang, { weekday: "short", hour: "2-digit", minute: "2-digit", ...timeOptions(this._hass) });
        facts.push(`<span class="fact">${icon("alarm")}${esc(fill(t.nextAlarm, { t: when }))}</span>`);
      }
      if (b.night?.mode?.enabled && b.night.phase === "night" && show("night_mode")) facts.push(this._chip(t.nightMode, "on"));
      let body = facts.length ? `<div class="facts">${facts.join("")}</div>` : "";
      if (live) {
        // In parts the dashboard card can lay out side by side when it is wide
        // The dashboard card says in Home Assistant's word that a box is switched off
        // The star of the chapter that plays marks it, on the page and on the dashboard card
        const now = show("playback")
          ? `<div class="now">${this._playback(b.playback, b.online === false && b.word ? b.word : undefined, b.online === true ? `star:${b.id}` : "",
            // On the page the figure's picture and name lead to the figure; the dashboard card has no such page
            // nor has a figure the account does not know
            card || !b.playback?.tonie_name ? "" : b.playback.tonie_id || "")}</div>` : "";
        // Repeat and "everything today" are the page's
        const ctl = show("controls") ? this._controls(b, !card) : "";
        body = `<div class="box-body">${body}${now}${ctl ? `<div class="ctl">${ctl}</div>` : ""}</div>`;
      } else body += `<div class="muted">${esc(t.classicNote)}</div>`;
      const notes = [];
      if (!live && b.last_seen) notes.push(fill(t.lastSeen, { t: this._relative(b.last_seen) }));
      if (notes.length) body += `<div class="muted small">${esc(notes.join(" · "))}</div>`;
      return { title, body };
    }

    // Play, pause, chapters, volume and the sleep timer of a Toniebox 2 that is online
    _controls(b, page = false) {
      const t = this._t;
      if (b.online !== true) return "";
      const p = b.playback;
      const placed = !!p?.tonie_id;
      const vol = Number.isFinite(b.volume) ? b.volume : null;
      const max = b.volume_max ?? 13;
      const step = vol === null && Number.isFinite(b.volume_percent);
      const busy = this._ctlBusy === b.id;
      const alarm = b.bedtime?.next_alarm?.due;
      const timerOn = !!this._sleep(b.sleep_timer);
      const btn = (cmd, ic, label, disabled, value = "") =>
        iconButton(ic, label, `data-act="ctl:${esc(b.id)}:${cmd}${value !== "" ? `:${value}` : ""}"${disabled || busy ? " disabled" : ""}`);
      let html = `<div class="controls">` +
        btn("previous", "prev", t.ctlPrev, !placed) +
        (p?.playing ? btn("pause", "pause", t.ctlPause, !placed) : btn("play", "play", t.ctlPlay, !placed)) +
        btn("next", "next", t.ctlNext, !placed) +
        (p?.chapter_list?.length > 1 ? iconButton("tracks", t.ctlTracks, `data-act="tracks:${esc(b.id)}"`) : "") +
        (page ? this._repeatButton(b, placed, busy) + this._everythingButton(b, busy) : "") +
        `<span class="ctl-gap"></span>` +
        // Without a level (the dashboard card) the buttons are the media player's steps
        (step
          ? btn("volume_down", "minus", t.ctlQuieter, b.volume_percent <= 0) + btn("volume_up", "plus", t.ctlLouder, b.volume_percent >= 100)
          : btn("volume", "minus", t.ctlQuieter, vol === null || vol <= 0, vol === null ? "" : vol - 1) +
            btn("volume", "plus", t.ctlLouder, vol === null || vol >= max, vol === null ? "" : vol + 1)) +
        `<span class="ctl-gap"></span>`;
      // The alarm of a bedtime uses the same timer; the timer stays out of its way
      if (!alarm) {
        html += timerOn
          ? btn("sleep_clear", "sleepOff", t.ctlSleepOff, false)
          // How long is chosen in a small dialog
          : iconButton("sleep", t.ctlSleepTitle, `class="sleep-open" data-act="sleepset:${esc(b.id)}"${busy ? " disabled" : ""}`);
      }
      html += `</div>`;
      if (this._ctlError?.id === b.id) html += this._errHtml(this._error(this._ctlError.err));
      return html;
    }

    // One button through the three states, as Home Assistant's media player has it:
    // off, the whole figure, one chapter; the next press leads to the state it names
    _repeatButton(b, placed, busy) {
      const t = this._t;
      const [ic, label, next] = b.repeat === "all" ? ["repeat", t.repeatAll, "one"] : b.repeat === "one" ? ["repeatOne", t.repeatOne, "off"] : ["repeat", t.repeatOff, "all"];
      return iconButton(ic, label, `class="repeat${b.repeat ? " on" : ""}" aria-pressed="${b.repeat ? "true" : "false"}" data-act="repeat:${esc(b.id)}:${next}"${!placed || busy ? " disabled" : ""}`);
    }

    // The chapters of what is on a box, in Home Assistant's dialog inside `host`: a chapter
    // chosen there plays, its star marks it. The dialog stays while its list is drawn
    // anew; this._tracks names the box whose list is open. busy: a command is on its
    // way, nothing more is taken; error: what the last star or chapter ran into
    _renderTracks(host, b, { busy = false, error = null } = {}) {
      if (!host) return;
      const t = this._t;
      const p = b?.playback;
      // The title says how the favourites steer the figure, while they do (the page knows it)
      const steering = p?.favourites?.suspended ? t.favNowAll : p?.favourites?.mode ? t[`favNow_${p.favourites.mode}`] : "";
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
      dialog.headerSubtitle = `${p.tonie_name || t.unknownFigure} · ${b.name || b.id}${steering ? ` · ${steering}` : ""}`;
      const off = busy ? " disabled" : "";
      const html = (error ? this._errHtml(error) : "") + `<ol class="tracks">${p.chapter_list.map((c, i) => {
        const now = i === p.chapter;
        const title = c.title || `${t.chapter} ${i + 1}`;
        return `<li role="button" tabindex="0" data-act="jump:${esc(b.id)}:${i}"${now ? ' class="current" aria-current="true"' : ""}${busy ? ' aria-disabled="true" disabled' : ""}>` +
          `<span class="rank">${i + 1}</span><span class="name">${esc(title)}</span>` +
          `${Number.isFinite(c.seconds) ? `<span class="len">${esc(mmss(c.seconds))}</span>` : ""}` +
          // The star marks the chapter; the list stays open. No star while which chapters
          // have one is not known (a Tune lies on the figure)
          (typeof c.favourite === "boolean" ? iconButton(c.favourite ? "star" : "starOff", `${c.favourite ? t.favOff : t.favOn}: ${title}`,
            `class="star${c.favourite ? " on" : ""}" data-act="starch:${esc(b.id)}:${i}" aria-pressed="${c.favourite}"${off}`) : "") + `</li>`;
      }).join("")}</ol>`;
      if (html !== this._overlayHtml) {
        this._overlayHtml = html;
        dialog.innerHTML = html;
      }
      dialog.open = true;
    }

    // How long until a box falls asleep, in Home Assistant's dialog inside `host`: a few
    // usual times and a field for any other. this._sleepFor names the box it is open for
    _renderSleep(host, b) {
      if (!host) return;
      const t = this._t;
      let dialog = host.firstElementChild;
      // Gone with the box, with a timer set meanwhile, or with an alarm that needs the timer
      if (!b || b.online !== true || this._sleep(b.sleep_timer) || b.bedtime?.next_alarm?.due) {
        this._sleepFor = null;
        if (dialog) dialog.open = false;
        return;
      }
      if (!dialog) {
        dialog = document.createElement("ha-dialog");
        this._sleepHtml = null;
        dialog.addEventListener("closed", () => {
          this._sleepFor = null;
          dialog.remove();
        });
        // Enter in the field starts the timer
        dialog.addEventListener("keydown", (e) => {
          if (e.key === "Enter" && e.target?.classList?.contains("sleep-own")) dialog.querySelector(".sleep-start")?.click();
        });
        host.append(dialog);
      }
      dialog.width = "small";
      dialog.headerTitle = t.ctlSleepTitle;
      dialog.headerSubtitle = b.name || b.id;
      const html = `<div class="sleep-set"><div class="sleep-quick">${SLEEP_MINUTES.map((m) =>
        `<ha-button appearance="filled" data-act="ctl:${esc(b.id)}:sleep:${m}" title="${esc(fill(t.ctlSleep, { m: this._fmt(m) }))}">` +
        `${esc(fill(t.sleepMin, { m: this._fmt(m) }))}</ha-button>`).join("")}</div>` +
        `<div class="sleep-free"><label><span>${esc(t.sleepOwn)}</span>` +
        `<input class="sleep-own" type="number" inputmode="numeric" min="1" max="${SLEEP_MAX_MINUTES}" step="1" required></label>` +
        `<ha-button class="sleep-start" data-act="sleepown:${esc(b.id)}">${esc(t.sleepStart)}</ha-button></div></div>`;
      if (html !== this._sleepHtml) {
        this._sleepHtml = html;
        dialog.innerHTML = html;
      }
      dialog.open = true;
    }

    // The minutes typed into the dialog's field; null (and the browser's own hint) when
    // they are no whole number the box takes
    _sleepOwn(host) {
      const input = host?.querySelector(".sleep-own");
      if (!input) return null;
      if (!input.reportValidity()) return null;
      return Number(input.value);
    }

    // While the favourites steer the figure on the box: a button that lets it play
    // everything until it is taken off, and back
    _everythingButton(b, busy) {
      const t = this._t;
      const fav = b.playback?.favourites;
      if (!fav || (!fav.mode && !fav.suspended)) return "";
      const on = !!fav.suspended;
      return iconButton("playAll", `${t.favAll}: ${on ? t.favAllOff : t.favAllOn}`,
        `class="fav-all${on ? " on" : ""}" aria-pressed="${on}" data-act="favall:${esc(b.id)}:${on ? 0 : 1}"${busy ? " disabled" : ""}`);
    }

    // The timer counts as set unless its state says otherwise; a timer that ends
    // with an alarm is the bedtime's, shown there
    _sleep(timer) {
      if (!timer?.state || timer.alarm || /^(off|inactive|disabled|stopped|finished|none|idle)$/i.test(timer.state)) return null;
      const until = time(timer.until);
      if (!Number.isFinite(until)) return this._t.sleepOn;
      return fill(this._t.sleepUntil, { t: new Date(until).toLocaleTimeString(this._lang, { hour: "2-digit", minute: "2-digit", ...timeOptions(this._hass) }) });
    }

    // The level with its little battery, the drawing hidden from a screen reader;
    // nothing is known while the box is switched off
    _batteryLevel(b) {
      const t = this._t;
      // On the battery's own page, while no level is known
      if (!Number.isFinite(b.battery)) return "–";
      const low = b.battery < 20 && !b.charging;
      return `<span class="batt${low ? " low" : ""}" aria-hidden="true"><b><i style="height:${Math.max(0, Math.min(100, b.battery))}%"></i></b></span>` +
        `${this._fmt(b.battery)} %${b.charging ? `<span class="charge">${icon("flash")}${esc(t.charging)}</span>` : ""}`;
    }

    // star: the action of the star beside the chapter that plays; without it a favourite shows its star only
    // figure: the ID of the figure its picture and name open, on the page
    _playback(p, nothing = this._t.nothing, star = "", figure = "") {
      const t = this._t;
      if (!p) return `<div class="play">${this._pic(null)}<div class="text"><span class="headline muted">${esc(nothing)}</span></div></div>`;
      // The dashboard card brings the state in Home Assistant's own word
      const [state, kind, ic] = p.playing ? [p.state_text || t.playing, "ok", "play"] : p.paused ? [p.state_text || t.paused, "warn", "pause"] : [t.placed, "", ""];
      let chapter = "";
      if (p.chapter != null) {
        chapter = `${esc(t.chapter)} ${p.chapter + 1}${Number.isFinite(p.chapters) ? ` / ${p.chapters}` : ""}` +
          (p.chapter_title ? ` · ${esc(p.chapter_title)}` : "");
      } else if (Number.isFinite(p.chapters)) chapter = esc(fill(p.chapters === 1 ? t.chapter1 : t.chaptersN, { n: this._fmt(p.chapters) }));
      // Whether the chapter that plays is a favourite: the dashboard card reads it from the
      // media player, the page from the chapter list
      const fav = p.chapter == null ? null
        : typeof p.favourite === "boolean" ? p.favourite
          : typeof p.chapter_list?.[p.chapter]?.favourite === "boolean" ? p.chapter_list[p.chapter].favourite : null;
      const starHtml = fav === null ? ""
        : star ? iconButton(fav ? "star" : "starOff", fav ? t.favOff : t.favOn, `class="star now-star${fav ? " on" : ""}" data-act="${esc(star)}" data-i="${p.chapter}" aria-pressed="${fav}"`)
          : fav ? `<span class="now-star on" role="img" aria-label="${esc(t.favIs)}" title="${esc(t.favIs)}">${icon("star")}</span>` : "";
      // How the favourites steer the figure right now (the page knows it)
      const steering = p.favourites?.suspended ? t.favNowAll : p.favourites?.mode ? t[`favNow_${p.favourites.mode}`] : "";
      // Picture and name are one way each to the figure's own page: for the mouse and the keyboard
      const open = figure ? ` role="button" tabindex="0" data-act="openfig" data-key="${esc(figure)}" title="${esc(t.openFigure)}"` : "";
      const pic = figure ? `<span class="fig-open pic-open"${open} aria-label="${esc(t.openFigure)}">${this._pic(p.image_url)}</span>` : this._pic(p.image_url);
      let html = `<div class="play">${pic}<div class="text"><span class="headline${figure ? " fig-open" : ""}"${open}>${esc(p.tonie_name || t.unknownFigure)}</span>` +
        `${chapter ? `<span class="supporting">${chapter}</span>` : ""}` +
        `<span class="supporting state ${kind}">${ic ? icon(ic) : ""}${esc(state)}${steering ? ` · ${esc(steering)}` : ""}</span></div>${starHtml}</div>`;
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
