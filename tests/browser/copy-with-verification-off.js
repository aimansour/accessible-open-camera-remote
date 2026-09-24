(() => {
  const folder = document.getElementById("phoneFolder");
  folder.value = "/sdcard/DCIM/OpenCamera";
  currentVideosFolder = folder.value;
  currentVideos = [{ name: "completed.mp4", size: 20, modified: 1 }];
  if (typeof currentCopyableNames !== "undefined") {
    currentCopyableNames = new Set(["completed.mp4"]);
  }
  current = { state: "unknown", confirmed_state: "unknown",
    verification_enabled: false, busy: false, message: "Verification stopped", generation: 1 };
  renderVideos(currentVideos);
  document.querySelector('#videos input[value="completed.mp4"]').checked = true;
  updateMutationAvailability();
  if (document.getElementById("copy").hidden) {
    throw new Error("Verified completed video cannot be copied while verification is off");
  }
  if (!document.getElementById("delete").hidden) {
    throw new Error("Delete was exposed while verification is off");
  }
  return "copy available, mutations hidden";
})()
