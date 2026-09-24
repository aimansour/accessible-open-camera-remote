(() => {
  const languageSelect = document.getElementById("language");
  languageSelect.value = "en";
  languageSelect.dispatchEvent(new Event("change", { bubbles: true }));
  renderTransfers({
    id: "unverified-copy", kind: "move", folder: "/sdcard/DCIM/OpenCamera",
    running: true, total: 1, completed: 1,
    stages: { "clip.mp4": "uncertain" },
    results: [{ name: "clip.mp4", outcome: "uncertain", destination: null,
      message: "Move result uncertain; inspect phone and PC" }]
  });
  const message = document.getElementById("transferResults").textContent;
  if (message.includes("PC copy is verified")) {
    throw new Error("Unverified PC copy was described as verified");
  }
  return "uncertain move makes no unsupported copy claim";
})()
