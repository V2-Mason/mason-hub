// 7_mute_everything.jsx
// Brute-force mute EVERY layer in EVERY composition in the project.
//
// Purpose: Catch any audio sources we might have missed. Some templates
//          hide audio inside pre-comps, in footage items, or in BGM layers
//          that the main fill script doesn't touch.
//
// Usage:
//   1. Open your .aep (v1, v2, or v3 - any version)
//   2. File -> Scripts -> Run Script File... -> select this file
//   3. Save the project (Ctrl+S) if you want the change to persist
//
// Safe: only toggles audioEnabled = false, does not delete anything.
//       To undo: Ctrl+Z (one step) or re-run a fill script.

(function muteEverything() {

    if (!app.project) {
        alert("No project open.");
        return;
    }

    var logLines = [];
    function log(s) { logLines.push(s); }
    log("=== Brute-force Mute All ===");
    log("Started: " + new Date().toString());
    log("");

    var totalComps = 0;
    var totalLayers = 0;
    var mutedLayers = 0;
    var alreadyMuted = 0;

    app.beginUndoGroup("Mute Everything");

    // Walk every composition in the project
    for (var i = 1; i <= app.project.numItems; i++) {
        var item = app.project.item(i);
        if (!(item instanceof CompItem)) continue;

        totalComps++;
        log("Comp: \"" + item.name + "\" (" + item.numLayers + " layers)");

        for (var L = 1; L <= item.numLayers; L++) {
            var layer = item.layer(L);
            totalLayers++;

            // Only AVLayers have audioEnabled
            if (!(layer instanceof AVLayer)) continue;

            // Check if layer has audio at all (some don't - text, shape, etc)
            var hasAudio = false;
            try {
                hasAudio = layer.hasAudio;
            } catch (eH) {
                hasAudio = true; // assume yes if we can't check
            }

            if (!hasAudio) continue;

            // Check current state
            var wasEnabled = true;
            try {
                wasEnabled = layer.audioEnabled;
            } catch (eE) {}

            if (!wasEnabled) {
                alreadyMuted++;
                continue;
            }

            // Mute it
            try {
                layer.audioEnabled = false;
                mutedLayers++;
                log("  MUTED: [" + layer.index + "] \"" + layer.name + "\"");
            } catch (eM) {
                log("  FAIL:  [" + layer.index + "] \"" + layer.name + "\" - " + eM.toString());
            }
        }
    }

    app.endUndoGroup();

    log("");
    log("=== Summary ===");
    log("Compositions walked: " + totalComps);
    log("Layers inspected:    " + totalLayers);
    log("Newly muted:         " + mutedLayers);
    log("Already muted:       " + alreadyMuted);

    // Write log
    var scriptDir = File($.fileName).parent;
    var logFile = new File(scriptDir.fsName + "/7_mute_log.txt");
    if (logFile.open("w")) {
        logFile.encoding = "UTF-8";
        logFile.write(logLines.join("\n"));
        logFile.close();
    }

    alert("Mute complete!\n\n" +
          "Compositions: " + totalComps + "\n" +
          "Layers walked: " + totalLayers + "\n" +
          "Newly muted: " + mutedLayers + "\n" +
          "Already muted: " + alreadyMuted + "\n\n" +
          "Press Ctrl+S to save the project.\n\n" +
          "Log: " + logFile.fsName);

})();
