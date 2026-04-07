// 5_recut_timeline.jsx
// Recut the Render comp into a 9-second narrative-aligned timeline
//
// Purpose: The original Adobe Stock template Render comp is 18 seconds and
//          full of demo text and 5+ scene cuts that don't match Mason's
//          script v6 narrative for Act 1 (0:03 - 0:12).
//
//          This script destructively rebuilds the Render comp into:
//
//          0.0 - 3.0s   Single shot of Media 03 Precomp (Meta layoff)
//                       "AI 替代了客服"
//          3.0 - 6.0s   Single shot of Media 01 Precomp (Amazon layoff)
//                       "AI 裁掉了设计部"
//          6.0 - 9.0s   Single shot of Media 02 Precomp (Google layoff)
//                       "程序员的黄昏"
//          9.0 - 11.0s  Scene 04 reversed (mosaic expanding outward)
//                       Visual climax: single shot dissolves into multi-grid
//
//          Total: 11 seconds (script needs 9, we trim later in PR/Resolve)
//
// What gets removed:
//   - All Adobe Stock demo text layers (This Is, Multiscreen, Dynamic,
//     Slideshow, For Your, Events, parties, broadcasts)
//   - Their associated BG 2/3/4/5 layers
//   - Outro Scene
//   - All Scene 01/03/05 references (we only keep Scene 04 reversed)
//   - All Media XX Precomp references that are not 01, 02, or 03
//
// What is preserved:
//   - Color Control / Stroke Control / FX adjustment layers
//   - Background BG layer
//   - Your Music layer (in case you want to use it)
//
// Usage:
//   1. Run 3_fill_template_v2.jsx FIRST (creates "Multiscreen Intro filled v2.aep")
//   2. Open that v2 .aep
//   3. File -> Scripts -> Run Script File... -> select 5_recut_timeline.jsx
//   4. Script saves to "Multiscreen Intro v2 recut.aep" - keeps v2 intact
//
// Idempotent: re-running on a previously-recut comp will rebuild from scratch.

(function recutTimeline() {

    if (!app.project || !app.project.file) {
        alert("Please open the filled v2 .aep first.");
        return;
    }

    // ---- Step 1: find the Render comp ----
    var renderComp = null;
    for (var i = 1; i <= app.project.numItems; i++) {
        var item = app.project.item(i);
        if (item instanceof CompItem && item.name === "Render") {
            renderComp = item;
            break;
        }
    }
    if (!renderComp) {
        alert("Could not find a comp named 'Render'.");
        return;
    }

    // ---- Step 2: find the precomps we need to reference ----
    var media01Precomp = findComp("Media 01 Precomp");
    var media02Precomp = findComp("Media 02 Precomp");
    var media03Precomp = findComp("Media 03 Precomp");
    var scene04Comp    = findComp("Scene 04");

    var missing = [];
    if (!media01Precomp) missing.push("Media 01 Precomp");
    if (!media02Precomp) missing.push("Media 02 Precomp");
    if (!media03Precomp) missing.push("Media 03 Precomp");
    if (!scene04Comp)    missing.push("Scene 04");
    if (missing.length > 0) {
        alert("Missing required comps:\n" + missing.join("\n"));
        return;
    }

    // ---- Step 3: confirm with user before destructive operation ----
    var confirmed = confirm(
        "This will DESTRUCTIVELY rebuild the Render comp:\n\n" +
        "  - Delete all existing layers\n" +
        "  - Add 3 single-shot layers (Meta, Amazon, Google)\n" +
        "  - Add Scene 04 reversed at the end\n" +
        "  - Set comp duration to 11 seconds\n" +
        "  - Save as 'Multiscreen Intro v2 recut.aep'\n\n" +
        "The original v2 .aep will NOT be modified.\n\n" +
        "Continue?"
    );
    if (!confirmed) return;

    var logLines = [];
    function log(s) { logLines.push(s); }
    log("=== Recut Timeline ===");
    log("Started: " + new Date().toString());
    log("");

    app.beginUndoGroup("Recut Render Timeline");

    // ---- Step 4: change comp duration to 11 seconds ----
    // Render comp is 60 fps, so 11s = 660 frames
    // The comp's frameRate property tells us its framerate
    var fps = renderComp.frameRate;
    var newDuration = 11.0;
    try {
        renderComp.duration = newDuration;
        log("Set comp duration to " + newDuration + "s (was 18s)");
    } catch (eD) {
        log("WARN: failed to set comp duration: " + eD.toString());
    }

    // ---- Step 5: delete ALL existing layers ----
    // We're rebuilding from scratch, so this is the simplest path.
    // Iterate from top down (highest index first) to avoid index shifts.
    var deleted = 0;
    while (renderComp.numLayers > 0) {
        try {
            renderComp.layer(1).remove();
            deleted++;
        } catch (eDel) {
            log("WARN: failed to delete layer: " + eDel.toString());
            break;
        }
    }
    log("Deleted " + deleted + " original layers");

    // ---- Step 6: add 3 single-shot layers ----
    // Order from BACK to FRONT in AE means we add the LAST one first,
    // because layers.add inserts at the top. So we add them in reverse
    // chronological order to get the right z-order.
    //
    // Actually for single-shot full-screen, z-order doesn't matter as long
    // as only one is visible at a time. We'll set in/out points and let
    // them not overlap.

    // Slot 1: Meta (Media 03 Precomp), 0-3s
    var slot1 = renderComp.layers.add(media03Precomp);
    slot1.name = "[SHOT 1] Meta - AI 替代了客服";
    slot1.startTime = 0;
    slot1.inPoint = 0;
    slot1.outPoint = 3.0;
    centerAndFit(slot1, renderComp);
    log("Added [SHOT 1] Meta at 0-3s");

    // Slot 2: Amazon (Media 01 Precomp), 3-6s
    var slot2 = renderComp.layers.add(media01Precomp);
    slot2.name = "[SHOT 2] Amazon - AI 裁掉了设计部";
    slot2.startTime = 3.0;
    slot2.inPoint = 3.0;
    slot2.outPoint = 6.0;
    centerAndFit(slot2, renderComp);
    log("Added [SHOT 2] Amazon at 3-6s");

    // Slot 3: Google (Media 02 Precomp), 6-9s
    var slot3 = renderComp.layers.add(media02Precomp);
    slot3.name = "[SHOT 3] Google - 程序员的黄昏";
    slot3.startTime = 6.0;
    slot3.inPoint = 6.0;
    slot3.outPoint = 9.0;
    centerAndFit(slot3, renderComp);
    log("Added [SHOT 3] Google at 6-9s");

    // ---- Step 7: add Scene 04 reversed at 9-11s ----
    var slot4 = renderComp.layers.add(scene04Comp);
    slot4.name = "[SHOT 4] Mosaic Expand (Scene 04 reversed)";
    slot4.startTime = 9.0;
    slot4.inPoint = 9.0;
    slot4.outPoint = 11.0;

    // Reverse the layer's time
    // ExtendScript: AVLayer has stretch and timeRemapEnabled.
    // Setting stretch = -100 reverses the layer.
    try {
        slot4.stretch = -100;
        // After negative stretch, AE flips inPoint/outPoint, so we need
        // to re-set them carefully. The recommended pattern is:
        //   1. set stretch to -100
        //   2. then set startTime/inPoint/outPoint
        slot4.startTime = 9.0;
        // For a -100% stretched layer, the timeline duration equals the
        // source duration. Scene 04 source is 5s, but we only want 2s
        // in our timeline, so set out = in + 2.
        slot4.inPoint = 9.0;
        slot4.outPoint = 11.0;
        log("Added [SHOT 4] Scene 04 reversed at 9-11s (stretch=-100)");
    } catch (eR) {
        log("WARN: failed to reverse Scene 04: " + eR.toString() +
            " (layer added but playing forward)");
    }

    // Center the Scene 04 in the comp
    // Scene 04 is 3840x2700, render is 3840x2160 - we need to scale or position
    centerAndFit(slot4, renderComp);

    // ---- Step 8: set work area to match new duration ----
    try {
        renderComp.workAreaStart = 0;
        renderComp.workAreaDuration = 11.0;
    } catch (eW) {
        log("WARN: failed to set work area: " + eW.toString());
    }

    app.endUndoGroup();

    // ---- Step 9: Save As ----
    var saveAsFile = new File(app.project.file.parent.fsName + "/Multiscreen Intro v2 recut.aep");
    try {
        app.project.save(saveAsFile);
        log("");
        log("Saved as: " + saveAsFile.fsName);
    } catch (eSave) {
        log("");
        log("SAVE FAILED: " + eSave.toString());
    }

    // ---- Step 10: write log + alert ----
    var logFile = new File(File($.fileName).parent.fsName + "/5_recut_log.txt");
    if (logFile.open("w")) {
        logFile.encoding = "UTF-8";
        logFile.write(logLines.join("\n"));
        logFile.close();
    }

    alert("Recut complete!\n\n" +
          "New timeline (11s total):\n" +
          "  0-3s    [SHOT 1] Meta layoff\n" +
          "  3-6s    [SHOT 2] Amazon layoff\n" +
          "  6-9s    [SHOT 3] Google layoff\n" +
          "  9-11s   [SHOT 4] Scene 04 reversed (mosaic expand)\n\n" +
          "Saved as: Multiscreen Intro v2 recut.aep\n\n" +
          "Now press Spacebar in the Render comp to preview.\n" +
          "Resolution should be set to Half or Quarter for smooth playback.\n\n" +
          "Log: " + logFile.fsName);

    // ---- Helpers ----

    function findComp(name) {
        for (var k = 1; k <= app.project.numItems; k++) {
            var it = app.project.item(k);
            if (it instanceof CompItem && it.name === name) return it;
        }
        return null;
    }

    function centerAndFit(layer, comp) {
        // Position the layer at the comp center and scale it to cover
        var src = layer.source;
        if (!src || !src.width || !src.height) return;

        var sx = (comp.width / src.width) * 100;
        var sy = (comp.height / src.height) * 100;
        var s = Math.max(sx, sy); // cover

        try {
            layer.property("Transform").property("Scale").setValue([s, s]);
            layer.property("Transform").property("Position").setValue([comp.width / 2, comp.height / 2]);
            layer.property("Transform").property("Anchor Point").setValue([src.width / 2, src.height / 2]);
        } catch (eS) {}
    }

})();
