"use strict";

const labels = {
  ar: {
    title: "التحكم في Open Camera", subtitle: "تحكم في التسجيل من الكمبيوتر باستخدام أزرار المتصفح المعتادة.",
    language: "اللغة", cameraHeading: "التسجيل", verificationHeading: "الفحص واستعمال الهاتف",
    verificationHelp: "أوقف الفحص قبل استعمال الهاتف بنفسك. يمكنك تشغيله بعدها لقراءة الحالة من جديد.",
    cameraHint: "الأزرار متاحة بعد التحقق من حالة Open Camera.",
    videosHeading: "الفيديوهات المكتملة", phoneFolderLabel: "مجلد Open Camera على الهاتف",
    refreshVideos: "عرض الفيديوهات", videosHint: "اختر الملفات بمربعات الاختيار. ستظهر أوامر النسخ والإدارة هنا.",
    noVideos: "لا توجد فيديوهات في هذا المجلد.", videosError: "تعذرت قراءة فيديوهات الهاتف.", bytes: "بايت",
    start: "بدء التسجيل", stop: "إنهاء التسجيل", pause: "إيقاف مؤقت", resume: "استئناف",
    unknown: "حالة التسجيل غير معروفة", idle: "جاهز للتسجيل", recording: "جارٍ التسجيل", paused: "التسجيل متوقف مؤقتًا",
    verificationOn: "إيقاف الفحص", verificationOff: "تشغيل الفحص", pending: "جارٍ التحقق من النتيجة",
    disconnected: "تعذر الاتصال بالخدمة المحلية", verificationDisabled: "الفحص متوقف. أزرار التسجيل معطلة مؤقتًا.",
    messages: {
      "Waiting for a fresh phone state": "بانتظار قراءة حالة الهاتف",
      "Reading Open Camera state": "جارٍ قراءة حالة Open Camera",
      "Open Camera is in photo mode or its recording state could not be recognized": "وضع التصوير غير معروف؛ افتح وضع الفيديو في Open Camera ثم شغّل الفحص.",
      "Camera state verified": "تم التحقق من حالة الكاميرا",
      "Could not read Open Camera; check the phone and connection": "تعذرت قراءة Open Camera؛ تحقق من الهاتف والاتصال.",
      "Verification is off; phone camera controls are disabled": "الفحص متوقف وأزرار التصوير معطلة.",
      "Sending command and checking its result": "أُرسل الأمر ويجري التحقق من نتيجته",
      "Unlock the phone and bring Open Camera to the foreground": "افتح قفل الهاتف واجعل Open Camera في المقدمة.",
      "Command sent, but the camera state could not be confirmed": "أُرسل الأمر لكن لم يمكن تأكيد حالة الكاميرا.",
      "Verification stopped": "توقف الفحص",
      "Camera result uncertain; check the phone, then verify again": "نتيجة الأمر غير مؤكدة؛ تحقق من الهاتف ثم شغّل الفحص من جديد."
    }
  },
  en: {
    title: "Open Camera Remote", subtitle: "Control recording from your computer with ordinary browser buttons.",
    language: "Language", cameraHeading: "Recording", verificationHeading: "Verification and phone use",
    verificationHelp: "Stop verification before using the phone yourself. Start it again to read the current state.",
    cameraHint: "Recording buttons are available after Open Camera state is verified.",
    videosHeading: "Completed videos", phoneFolderLabel: "Open Camera folder on phone",
    refreshVideos: "Show videos", videosHint: "Select files with checkboxes. Copy and management commands will appear here.",
    noVideos: "No videos in this folder.", videosError: "Could not read phone videos.", bytes: "bytes",
    start: "Start recording", stop: "Stop recording", pause: "Pause", resume: "Resume",
    unknown: "Recording state unknown", idle: "Ready to record", recording: "Recording", paused: "Recording paused",
    verificationOn: "Stop verification", verificationOff: "Start verification", pending: "Checking the result",
    disconnected: "Cannot reach the local service", verificationDisabled: "Verification is off. Recording controls are temporarily unavailable.",
    messages: {
      "Waiting for a fresh phone state": "Waiting for a fresh phone state",
      "Reading Open Camera state": "Reading Open Camera state",
      "Open Camera is in photo mode or its recording state could not be recognized": "Open Camera is in photo mode or its recording state could not be recognized",
      "Camera state verified": "Camera state verified",
      "Could not read Open Camera; check the phone and connection": "Could not read Open Camera; check the phone and connection",
      "Verification is off; phone camera controls are disabled": "Verification is off; phone camera controls are disabled",
      "Sending command and checking its result": "Sending command and checking its result",
      "Unlock the phone and bring Open Camera to the foreground": "Unlock the phone and bring Open Camera to the foreground",
      "Command sent, but the camera state could not be confirmed": "Command sent, but the camera state could not be confirmed",
      "Verification stopped": "Verification stopped",
      "Camera result uncertain; check the phone, then verify again": "Camera result uncertain; check the phone, then verify again"
    }
  }
};

const cameraButton = document.getElementById("camera");
const pauseButton = document.getElementById("pause");
const verificationButton = document.getElementById("verification");
const languageSelect = document.getElementById("language");
const token = document.querySelector('meta[name="session-token"]').content;
let language = "ar";
let current = { state: "unknown", verification_enabled: true, busy: false, message: "" };
let currentVideos = null;

function renderCamera(status) {
  const words = labels[language];
  const primary = status.state === "unknown" ? "unknown" : status.state === "idle" ? "start" : "stop";
  const secondary = status.state === "paused" ? "resume" : "pause";
  cameraButton.textContent = words[primary];
  pauseButton.textContent = words[secondary];
  cameraButton.setAttribute("aria-disabled", String(status.busy || !status.verification_enabled || status.state === "unknown"));
  pauseButton.setAttribute("aria-disabled", String(status.busy || !status.verification_enabled || status.state === "idle" || status.state === "unknown"));
  verificationButton.textContent = words[status.verification_enabled ? "verificationOn" : "verificationOff"];
  document.getElementById("stateText").textContent = words[status.state] || words.unknown;
  document.getElementById("messageText").textContent = status.message === "__disconnected__" ? words.disconnected
    : !status.verification_enabled ? words.verificationDisabled
    : status.busy ? words.pending : (words.messages[status.message] || status.message);
}

function render() {
  const words = labels[language];
  document.documentElement.lang = language;
  document.documentElement.dir = language === "ar" ? "rtl" : "ltr";
  document.title = words.title;
  for (const id of ["title", "subtitle", "cameraHeading", "verificationHeading", "verificationHelp", "cameraHint", "videosHeading", "videosHint", "refreshVideos", "phoneFolderLabel"]) {
    document.getElementById(id).textContent = words[id];
  }
  document.getElementById("languageLabel").textContent = words.language;
  renderCamera(current);
  if (currentVideos !== null) renderVideos(currentVideos);
}

function renderVideos(entries) {
  const list = document.getElementById("videos");
  const selected = new Set([...list.querySelectorAll('input:checked')].map(box => box.value));
  list.replaceChildren();
  const words = labels[language];
  document.getElementById("videosMessage").textContent = entries.length ? "" : words.noVideos;
  for (const entry of entries) {
    const item = document.createElement("li");
    const label = document.createElement("label");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.value = entry.name;
    checkbox.checked = selected.has(entry.name);
    const date = new Intl.DateTimeFormat(language, { dateStyle: "medium", timeStyle: "short" }).format(new Date(entry.modified * 1000));
    const size = new Intl.NumberFormat(language).format(entry.size);
    label.append(checkbox, document.createTextNode(`${entry.name} — ${size} ${words.bytes} — ${date}`));
    item.append(label);
    list.append(item);
  }
}

async function refreshVideos() {
  const folder = document.getElementById("phoneFolder").value;
  try {
    const response = await fetch(`/api/videos?folder=${encodeURIComponent(folder)}`, { cache: "no-store" });
    if (!response.ok) throw new Error("videos request failed");
    const payload = await response.json();
    currentVideos = payload.videos;
    renderVideos(currentVideos);
  } catch (_) {
    document.getElementById("videosMessage").textContent = labels[language].videosError;
  }
}

async function refresh() {
  try {
    const response = await fetch("/api/status", { cache: "no-store" });
    if (!response.ok) throw new Error("status request failed");
    current = await response.json();
  } catch (_) {
    current = { state: "unknown", verification_enabled: false, busy: false, message: "__disconnected__" };
  }
  renderCamera(current);
}

async function command(action) {
  try {
    const response = await fetch("/api/camera", {
      method: "POST", headers: { "Content-Type": "application/json", "X-Session-Token": token },
      body: JSON.stringify({ action })
    });
    if (!response.ok) throw new Error(await response.text());
    await refresh();
  } catch (error) {
    document.getElementById("messageText").textContent = error.message;
  }
}

cameraButton.addEventListener("click", () => {
  if (cameraButton.getAttribute("aria-disabled") === "true") return;
  command(current.state === "idle" ? "start" : "stop");
});
pauseButton.addEventListener("click", () => {
  if (pauseButton.getAttribute("aria-disabled") === "true") return;
  command(current.state === "paused" ? "resume" : "pause");
});
verificationButton.addEventListener("click", async () => {
  try {
    const response = await fetch("/api/verification", {
      method: "POST", headers: { "Content-Type": "application/json", "X-Session-Token": token },
      body: JSON.stringify({ enabled: !current.verification_enabled })
    });
    if (!response.ok) throw new Error(await response.text());
    await refresh();
  } catch (error) {
    document.getElementById("messageText").textContent = error.message;
  }
});
languageSelect.addEventListener("change", () => { language = languageSelect.value; render(); });
document.getElementById("refreshVideos").addEventListener("click", refreshVideos);
refresh();
refreshVideos();
setInterval(refresh, 1000);
