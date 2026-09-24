(() => {
  const folder = document.getElementById("phoneFolder");
  folder.value = "/sdcard/DCIM/OpenCamera";
  currentVideos = [{ name: "clip.mp4", size: 10, modified: 1 }];
  renderVideos(currentVideos);
  document.querySelector('#videos input[value="clip.mp4"]').checked = true;
  updateMutationAvailability();
  folder.value = "/sdcard/DCIM/Other";
  folder.dispatchEvent(new Event("input", { bubbles: true }));
  if (document.querySelector('#videos input:checked')) {
    throw new Error("Selected file from the previous folder remains actionable");
  }
  if (!document.getElementById("delete").hidden) {
    throw new Error("Delete remains visible after changing the phone folder");
  }
  return "folder selection invalidated";
})()
