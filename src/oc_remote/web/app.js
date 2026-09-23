"use strict";

const labels = {
  ar: {
    title: "التحكم في Open Camera", subtitle: "تحكم في التسجيل من الكمبيوتر باستخدام أزرار المتصفح المعتادة.",
    language: "اللغة", cameraHeading: "التسجيل", verificationHeading: "الفحص واستعمال الهاتف",
    verificationHelp: "أوقف الفحص قبل استعمال الهاتف بنفسك. يمكنك تشغيله بعدها لقراءة الحالة من جديد.",
    cameraHint: "الأزرار متاحة بعد التحقق من حالة Open Camera.",
    videosHeading: "الفيديوهات المكتملة", phoneFolderLabel: "مجلد Open Camera على الهاتف",
    refreshVideos: "عرض الفيديوهات", selectAll: "تحديد الكل", clearSelection: "إلغاء التحديد",
    videosHint: "اختر الملفات بمربعات الاختيار. ستظهر أوامر النسخ والإدارة هنا.",
    noVideos: "لا توجد فيديوهات في هذا المجلد.", videosError: "تعذرت قراءة فيديوهات الهاتف.", bytes: "بايت",
    transferHeading: "نسخ الفيديوهات إلى الكمبيوتر", pcFolderLabel: "مجلد الحفظ على الكمبيوتر", copy: "نسخ المحدد",
    transferPending: "جارٍ نسخ الملفات", transferFinished: "اكتملت المجموعة", transferError: "تعذر قراءة تقدم النسخ",
    transferCount: "ملفات مكتملة", stages: { waiting: "بانتظار النسخ", copying: "جارٍ النسخ", hashing: "جارٍ فحص البصمة", verified: "نسخة مؤكدة", failed: "فشل النسخ", uncertain: "نتيجة النقل غير مؤكدة" },
    uncertainMoveDetail: "نسخة الكمبيوتر مؤكدة؛ حذف الأصل من الهاتف غير مؤكد. افحص الملفين قبل أي إجراء آخر.",
    failedCopyDetail: "تعذر تأكيد النسخة. راجع الاتصال والمساحة ثم حاول من جديد.",
    manageHeading: "إدارة الفيديوهات المحددة", manageHint: "حدد فيديوهات مكتملة بعد إنهاء التسجيل والتحقق من حالته.",
    move: "نقل المحدد إلى الكمبيوتر", newStemLabel: "الاسم الجديد من دون الامتداد", rename: "إعادة التسمية",
    delete: "حذف المحدد", confirmDelete: "تأكيد الحذف", cancelDelete: "إلغاء الحذف",
    deletingChecking: "جارٍ الحذف والتحقق", deleteProgressLabel: "تقدم حذف الملفات",
    deleteProgressText: (percent, completed, total, verified, uncertain) =>
      `${percent}٪ — اكتمل فحص ${completed} من ${total}. تأكد حذف ${verified}، ونتيجة ${uncertain} غير مؤكدة.`,
    deleteStages: {
      checking: "جارٍ فحص الفيديو المحدد", deleting: "جارٍ حذفه من الهاتف",
      verifying: "جارٍ فحص الملف وفهرس Android", verified: "اكتمل الحذف والتحقق",
      uncertain: "نتيجة الحذف غير مؤكدة؛ افحص الهاتف"
    },
    deleteQuestion: "تأكيد حذف الفيديوهات التالية نهائيًا من الهاتف:", deleteCancelled: "أُلغي الحذف.",
    deleted: "تم حذف الفيديو والتحقق من فهرس Android.", renamed: "تغير الاسم وتم التحقق من فهرس Android.",
    moveStarted: "بدأ نقل الفيديو. ستظهر النتيجة في قسم النسخ.",
    invalidInput: "تحقق من الاسم أو اختيار الملف ثم حاول من جديد.",
    operationConflict: "لا يمكن تنفيذ العملية الآن؛ تحقق من حالة التسجيل والملف.",
    operationFailed: "تعذرت العملية؛ افحص الهاتف والاتصال ثم حدّث القائمة.",
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
      "Camera result uncertain; check the phone, then verify again": "نتيجة الأمر غير مؤكدة؛ تحقق من الهاتف ثم شغّل الفحص من جديد.",
      "Recording ended, but a finalized video could not be confirmed": "انتهى التصوير لكن تعذر تأكيد اكتمال ملف الفيديو. افحص الهاتف."
    }
  },
  en: {
    title: "Open Camera Remote", subtitle: "Control recording from your computer with ordinary browser buttons.",
    language: "Language", cameraHeading: "Recording", verificationHeading: "Verification and phone use",
    verificationHelp: "Stop verification before using the phone yourself. Start it again to read the current state.",
    cameraHint: "Recording buttons are available after Open Camera state is verified.",
    videosHeading: "Completed videos", phoneFolderLabel: "Open Camera folder on phone",
    refreshVideos: "Show videos", selectAll: "Select all", clearSelection: "Clear selection",
    videosHint: "Select files with checkboxes. Copy and management commands will appear here.",
    noVideos: "No videos in this folder.", videosError: "Could not read phone videos.", bytes: "bytes",
    transferHeading: "Copy videos to PC", pcFolderLabel: "PC destination folder", copy: "Copy selected",
    transferPending: "Copying files", transferFinished: "Batch complete", transferError: "Could not read transfer progress",
    transferCount: "files complete", stages: { waiting: "Waiting", copying: "Copying", hashing: "Checking SHA-256", verified: "Verified copy", failed: "Copy failed", uncertain: "Uncertain move" },
    uncertainMoveDetail: "The PC copy is verified; phone source removal is uncertain. Check both files before another action.",
    failedCopyDetail: "The copy could not be verified. Check the connection and free space, then retry.",
    manageHeading: "Manage selected videos", manageHint: "Select completed videos after recording has stopped and its state is verified.",
    move: "Move selected to PC", newStemLabel: "New name without extension", rename: "Rename",
    delete: "Delete selected", confirmDelete: "Confirm deletion", cancelDelete: "Cancel deletion",
    deletingChecking: "Deleting and checking", deleteProgressLabel: "File deletion progress",
    deleteProgressText: (percent, completed, total, verified, uncertain) =>
      `${percent}% — ${completed} of ${total} checked. ${verified} verified deleted; ${uncertain} uncertain.`,
    deleteStages: {
      checking: "Checking the selected video", deleting: "Deleting from the phone",
      verifying: "Checking the file and Android media index", verified: "Deletion verified",
      uncertain: "Deletion result uncertain; inspect the phone"
    },
    deleteQuestion: "Confirm permanent deletion of these videos from the phone:", deleteCancelled: "Deletion cancelled.",
    deleted: "Video removed and Android media index verified.", renamed: "Name changed and Android media index verified.",
    moveStarted: "Video move started. Its result will appear in the transfer section.",
    invalidInput: "Check the name or selected video and try again.",
    operationConflict: "This action is unavailable now; verify recording state and the selected file.",
    operationFailed: "Action failed; check the phone and connection, then refresh the list.",
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
      "Camera result uncertain; check the phone, then verify again": "Camera result uncertain; check the phone, then verify again",
      "Recording ended, but a finalized video could not be confirmed": "Recording ended, but a finalized video could not be confirmed"
    }
  }
};

const cameraButton = document.getElementById("camera");
const pauseButton = document.getElementById("pause");
const verificationButton = document.getElementById("verification");
const copyButton = document.getElementById("copy");
const selectAllButton = document.getElementById("selectAll");
const moveButton = document.getElementById("move");
const renameButton = document.getElementById("rename");
const deleteButton = document.getElementById("delete");
const confirmDeleteButton = document.getElementById("confirmDelete");
const languageSelect = document.getElementById("language");
const token = document.querySelector('meta[name="session-token"]').content;
let language = "ar";
let current = { state: "unknown", confirmed_state: "unknown", verification_enabled: true, busy: false, generation: 0, message: "" };
let pendingCamera = 0;
let cameraRequests = Promise.resolve();
let commandEpoch = 0;
let currentVideos = null;
let transferJob = null;
let fileOperation = null;
let handledFileJobId = null;
let lastFileOperationJson = null;
let lastTransferJson = null;
let pendingDeleteNames = null;
let fileBusy = false;
let activeDeleteJobId = null;
let seenVerifiedDeleteNames = new Set();
let videoRevision = 0;
let fileOperationRefreshInFlight = false;

function renderCamera(status) {
  const words = labels[language];
  const primary = status.state === "unknown" ? "unknown" : status.state === "idle" ? "start" : "stop";
  const secondary = status.state === "paused" ? "resume" : "pause";
  cameraButton.textContent = words[primary];
  pauseButton.textContent = words[secondary];
  cameraButton.hidden = pendingCamera >= 8 || !status.verification_enabled || status.state === "unknown";
  pauseButton.hidden = pendingCamera >= 8 || !status.verification_enabled || status.state === "idle" || status.state === "unknown";
  verificationButton.textContent = words[status.verification_enabled ? "verificationOn" : "verificationOff"];
  document.getElementById("stateText").textContent = words[status.state] || words.unknown;
  document.getElementById("messageText").textContent = status.message === "__disconnected__" ? words.disconnected
    : !status.verification_enabled ? words.verificationDisabled
    : status.busy ? words.pending : (words.messages[status.message] || status.message);
  updateMutationAvailability();
}

function render() {
  const words = labels[language];
  document.documentElement.lang = language;
  document.documentElement.dir = language === "ar" ? "rtl" : "ltr";
  document.title = words.title;
  for (const id of ["title", "subtitle", "cameraHeading", "verificationHeading", "verificationHelp", "cameraHint", "videosHeading", "videosHint", "refreshVideos", "selectAll", "phoneFolderLabel", "transferHeading", "pcFolderLabel", "copy", "manageHeading", "manageHint", "move", "newStemLabel", "rename", "delete", "confirmDelete", "cancelDelete"]) {
    document.getElementById(id).textContent = words[id];
  }
  document.getElementById("languageLabel").textContent = words.language;
  document.getElementById("deleteProgressLabel").textContent = words.deleteProgressLabel;
  renderCamera(current);
  if (currentVideos !== null) renderVideos(currentVideos);
  if (transferJob !== null) renderTransfers(transferJob);
  if (fileOperation !== null) renderFileOperation(fileOperation);
  if (pendingDeleteNames !== null) {
    document.getElementById("deleteConfirmation").textContent = words.deleteQuestion;
  }
  updateSelectAll();
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
  updateCopyAvailability();
  updateMutationAvailability();
  updateSelectAll();
}

function updateSelectAll() {
  const boxes = [...document.querySelectorAll('#videos input[type="checkbox"]')];
  const allSelected = boxes.length > 0 && boxes.every(box => box.checked);
  selectAllButton.textContent = labels[language][allSelected ? "clearSelection" : "selectAll"];
  selectAllButton.hidden = boxes.length === 0;
}

function selectedNames() {
  return [...document.querySelectorAll('#videos input:checked')].map(box => box.value);
}

function updateCopyAvailability() {
  copyButton.hidden = selectedNames().length === 0 || current.confirmed_state !== "idle"
    || !current.verification_enabled || current.busy || fileBusy
    || (fileOperation && fileOperation.running) || (transferJob && transferJob.running);
}

function updateMutationAvailability() {
  const count = selectedNames().length;
  const allowed = current.confirmed_state === "idle" && current.verification_enabled && !current.busy && !fileBusy
    && !(fileOperation && fileOperation.running) && !(transferJob && transferJob.running);
  moveButton.hidden = !allowed || count === 0;
  deleteButton.hidden = !allowed || count === 0;
  document.getElementById("renameControls").hidden = !allowed || count !== 1;
  updateCopyAvailability();
}

async function mutationRequest(endpoint, payload) {
  const response = await fetch(endpoint, {
    method: "POST", headers: { "Content-Type": "application/json", "X-Session-Token": token },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    const words = labels[language];
    throw new Error(response.status === 400 ? words.invalidInput
      : response.status === 409 ? words.operationConflict : words.operationFailed);
  }
  return response.json();
}

async function runMutation(action) {
  const names = selectedNames();
  if (!names.length || (action === "rename" && names.length !== 1) || fileBusy) return;
  fileBusy = true;
  updateMutationAvailability();
  const words = labels[language];
  const folder = document.getElementById("phoneFolder").value;
  if (action === "delete") {
    confirmDeleteButton.hidden = true;
    document.getElementById("cancelDelete").hidden = true;
    document.getElementById("manageResult").textContent = words.deletingChecking;
  }
  try {
    if (action === "move") {
      await mutationRequest("/api/move", { folder, names, destination: document.getElementById("pcFolder").value });
      document.getElementById("manageResult").textContent = words.moveStarted;
      await refreshTransfers();
    } else if (action === "rename") {
      await mutationRequest("/api/rename", { folder, name: names[0], new_stem: document.getElementById("newStem").value });
      document.getElementById("manageResult").textContent = words.renamed;
      document.getElementById("newStem").value = "";
      await refreshVideos();
    } else if (action === "delete") {
      const accepted = await mutationRequest("/api/delete", { folder, names, confirmed_names: pendingDeleteNames });
      activeDeleteJobId = accepted.id;
      seenVerifiedDeleteNames = new Set();
      fileOperation = { id: accepted.id, kind: "delete", stage: "checking", running: true,
        outcome: null, total: names.length, completed: 0, stages: Object.fromEntries(names.map(name => [name, "waiting"])) };
      renderFileOperation(fileOperation);
      await refreshFileOperation(true);
    }
  } catch (error) {
    document.getElementById("manageResult").textContent = error.message;
    if (action === "delete" && !(fileOperation && fileOperation.running)) {
      confirmDeleteButton.hidden = false;
      document.getElementById("cancelDelete").hidden = false;
    }
  } finally {
    fileBusy = false;
    updateMutationAvailability();
  }
}

function renderFileOperation(job) {
  if (!job.id || job.kind !== "delete") return;
  const words = labels[language];
  if (job.running && activeDeleteJobId === null) {
    activeDeleteJobId = job.id;
    seenVerifiedDeleteNames = new Set();
  }
  const stages = Object.entries(job.stages || {});
  const verifiedNames = stages.filter(([, stage]) => stage === "verified").map(([name]) => name);
  const uncertainCount = stages.filter(([, stage]) => stage === "uncertain").length;
  const percent = job.total ? Math.floor(100 * job.completed / job.total) : 0;
  const progressBox = document.getElementById("deleteProgressBox");
  progressBox.hidden = false;
  document.getElementById("deleteProgress").value = percent;
  document.getElementById("deleteProgressText").textContent =
    words.deleteProgressText(percent, job.completed, job.total, verifiedNames.length, uncertainCount);
  document.getElementById("manageResult").textContent =
    `${words.deleteStages[job.stage] || words.deletingChecking}: ${job.completed}/${job.total}`;
  const results = document.getElementById("deleteResults");
  const existing = new Map([...results.children].map(item => [item.dataset.name, item]));
  for (const [name, stage] of stages) {
    let item = existing.get(name);
    if (!item) {
      item = document.createElement("li");
      item.dataset.name = name;
      results.append(item);
    }
    const description = `${name} — ${words.deleteStages[stage] || stage}`;
    if (item.textContent !== description) item.textContent = description;
    existing.delete(name);
  }
  for (const item of existing.values()) item.remove();
  if (job.id === activeDeleteJobId) {
    const deleted = new Set(verifiedNames);
    const newlyVerified = verifiedNames.filter(name => !seenVerifiedDeleteNames.has(name));
    if (newlyVerified.length) {
      for (const name of newlyVerified) seenVerifiedDeleteNames.add(name);
      videoRevision++;
    }
    if (currentVideos !== null) {
      currentVideos = currentVideos.filter(entry => !deleted.has(entry.name));
    }
    const list = document.getElementById("videos");
    for (const box of list.querySelectorAll('input[type="checkbox"]')) {
      if (deleted.has(box.value)) box.closest("li").remove();
    }
    document.getElementById("videosMessage").textContent = list.children.length ? "" : words.noVideos;
    updateSelectAll();
  }
  if (!job.running && job.id !== handledFileJobId) {
    handledFileJobId = job.id;
    activeDeleteJobId = null;
    seenVerifiedDeleteNames = new Set();
    pendingDeleteNames = null;
    document.getElementById("confirmationBox").hidden = true;
    refreshVideos();
  }
  updateMutationAvailability();
}

async function refreshFileOperation(force = false) {
  if ((fileBusy && !force) || fileOperationRefreshInFlight) return;
  fileOperationRefreshInFlight = true;
  try {
    const response = await fetch("/api/file-operation", { cache: "no-store" });
    if (!response.ok) throw new Error("file operation request failed");
    const job = await response.json();
    if (!job.id) return;
    const json = JSON.stringify(job);
    if (json === lastFileOperationJson) return;
    lastFileOperationJson = json;
    fileOperation = job;
    renderFileOperation(job);
  } catch (_) {
    if (fileOperation && fileOperation.running) {
      document.getElementById("manageResult").textContent = labels[language].operationFailed;
    }
  } finally {
    fileOperationRefreshInFlight = false;
  }
}

function renderTransfers(job) {
  const words = labels[language];
  const list = document.getElementById("transferResults");
  list.replaceChildren();
  document.getElementById("transferSummary").textContent = job.total ?
    `${job.running ? words.transferPending : words.transferFinished}: ${job.completed}/${job.total} ${words.transferCount}` : "";
  for (const [name, stage] of Object.entries(job.stages)) {
    const result = job.results.find(item => item.name === name);
    const item = document.createElement("li");
    const detail = result?.outcome === "uncertain" ? words.uncertainMoveDetail
      : result?.outcome === "failed" ? words.failedCopyDetail : "";
    item.textContent = `${name} — ${words.stages[stage] || stage}${detail ? ` — ${detail}` : ""}`;
    list.append(item);
  }
  updateCopyAvailability();
}

async function refreshTransfers() {
  try {
    const response = await fetch("/api/transfers", { cache: "no-store" });
    if (!response.ok) throw new Error("transfer status request failed");
    const job = await response.json();
    const json = JSON.stringify(job);
    if (json !== lastTransferJson) {
      transferJob = job;
      lastTransferJson = json;
      renderTransfers(job);
    }
  } catch (_) {
    document.getElementById("transferSummary").textContent = labels[language].transferError;
  }
}

async function refreshVideos() {
  const folder = document.getElementById("phoneFolder").value;
  const revision = videoRevision;
  try {
    const response = await fetch(`/api/videos?folder=${encodeURIComponent(folder)}`, { cache: "no-store" });
    if (!response.ok) throw new Error("videos request failed");
    const payload = await response.json();
    if (revision !== videoRevision || folder !== document.getElementById("phoneFolder").value) return;
    currentVideos = payload.videos;
    renderVideos(currentVideos);
  } catch (_) {
    document.getElementById("videosMessage").textContent = labels[language].videosError;
  }
}

function acceptCameraStatus(status, force = false) {
  if (!force && (pendingCamera > 0 || (status.generation ?? 0) < (current.generation ?? 0))) return;
  current = status;
  renderCamera(current);
}

async function refresh(force = false) {
  try {
    const response = await fetch("/api/status", { cache: "no-store" });
    if (!response.ok) throw new Error("status request failed");
    acceptCameraStatus(await response.json(), force);
  } catch (_) {
    if (force || pendingCamera === 0) {
      current = { state: "unknown", confirmed_state: "unknown", verification_enabled: false,
        busy: false, generation: current.generation, message: "__disconnected__" };
      renderCamera(current);
    }
  }
}

function command(action) {
  const nextState = { start: "recording", stop: "idle", pause: "paused", resume: "recording" }[action];
  pendingCamera++;
  current = { ...current, state: nextState, busy: true, generation: (current.generation ?? 0) + 1,
    message: "Sending command and checking its result" };
  renderCamera(current);
  const epoch = commandEpoch;
  cameraRequests = cameraRequests.then(async () => {
    if (epoch !== commandEpoch) return;
    const response = await fetch("/api/camera", {
      method: "POST", headers: { "Content-Type": "application/json", "X-Session-Token": token },
      body: JSON.stringify({ action })
    });
    if (!response.ok) throw new Error(await response.text());
    const status = await response.json();
    pendingCamera--;
    acceptCameraStatus(status);
  }).catch(async error => {
    if (epoch !== commandEpoch) return;
    commandEpoch++;
    pendingCamera = 0;
    await refresh(true);
    document.getElementById("messageText").textContent = error.message;
  });
}

cameraButton.addEventListener("click", () => {
  if (cameraButton.hidden) return;
  command(current.state === "idle" ? "start" : "stop");
});
pauseButton.addEventListener("click", () => {
  if (pauseButton.hidden) return;
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
selectAllButton.addEventListener("click", () => {
  if (selectAllButton.hidden) return;
  const boxes = [...document.querySelectorAll('#videos input[type="checkbox"]')];
  const allSelected = boxes.every(box => box.checked);
  for (const box of boxes) box.checked = !allSelected;
  updateSelectAll();
  updateCopyAvailability();
  updateMutationAvailability();
  pendingDeleteNames = null;
  document.getElementById("confirmationBox").hidden = true;
});
document.getElementById("videos").addEventListener("change", () => {
  updateSelectAll();
  updateCopyAvailability();
  updateMutationAvailability();
  pendingDeleteNames = null;
  document.getElementById("confirmationBox").hidden = true;
});
copyButton.addEventListener("click", async () => {
  if (copyButton.hidden) return;
  try {
    const response = await fetch("/api/copy", {
      method: "POST", headers: { "Content-Type": "application/json", "X-Session-Token": token },
      body: JSON.stringify({ names: selectedNames(), folder: document.getElementById("phoneFolder").value,
        destination: document.getElementById("pcFolder").value })
    });
    if (!response.ok) throw new Error(await response.text());
    await refreshTransfers();
  } catch (error) {
    document.getElementById("transferSummary").textContent = error.message;
  }
});
moveButton.addEventListener("click", () => {
  if (!moveButton.hidden) runMutation("move");
});
renameButton.addEventListener("click", () => {
  if (!document.getElementById("renameControls").hidden) runMutation("rename");
});
deleteButton.addEventListener("click", () => {
  if (deleteButton.hidden) return;
  fileOperation = null;
  pendingDeleteNames = selectedNames();
  document.getElementById("deleteConfirmation").textContent = labels[language].deleteQuestion;
  const list = document.getElementById("deleteNames");
  list.replaceChildren();
  for (const name of pendingDeleteNames) {
    const item = document.createElement("li");
    item.textContent = name;
    list.append(item);
  }
  confirmDeleteButton.hidden = false;
  document.getElementById("cancelDelete").hidden = false;
  document.getElementById("confirmationBox").hidden = false;
});
confirmDeleteButton.addEventListener("click", () => {
  if (confirmDeleteButton.hidden || JSON.stringify(pendingDeleteNames) !== JSON.stringify(selectedNames())) return;
  runMutation("delete");
});
document.getElementById("cancelDelete").addEventListener("click", () => {
  if (pendingDeleteNames === null) {
    document.getElementById("confirmationBox").hidden = true;
    return;
  }
  pendingDeleteNames = null;
  confirmDeleteButton.hidden = true;
  document.getElementById("cancelDelete").hidden = true;
  document.getElementById("confirmationBox").hidden = true;
  document.getElementById("manageResult").textContent = labels[language].deleteCancelled;
});
refresh();
refreshVideos();
refreshTransfers();
refreshFileOperation();
setInterval(refresh, 1000);
setInterval(refreshTransfers, 1000);
setInterval(() => { if (fileOperation?.running) refreshFileOperation(); }, 250);
setInterval(() => { if (!fileOperation?.running) refreshFileOperation(); }, 1000);
