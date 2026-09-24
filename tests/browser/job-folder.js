(() => {
  const folder = document.getElementById("phoneFolder");
  folder.value = "/sdcard/DCIM/Other";
  currentVideosFolder = folder.value;
  currentVideos = [{ name: "clip.mp4", size: 20, modified: 2 }];
  renderVideos(currentVideos);
  document.querySelector('#videos input[value="clip.mp4"]').checked = true;
  activeMoveJobId = "old-folder-job";
  renderTransfers({
    id: "old-folder-job", kind: "move", folder: "/sdcard/DCIM/OpenCamera",
    running: true, total: 1, completed: 1,
    stages: { "clip.mp4": "verified" },
    results: [{ name: "clip.mp4", outcome: "verified", destination: "C:\\Videos\\clip.mp4" }]
  });
  const box = document.querySelector('#videos input[value="clip.mp4"]');
  if (!box || !box.checked) throw new Error("Old job removed a same-named file in another folder");
  return "old-folder job kept the new folder selection";
})()
