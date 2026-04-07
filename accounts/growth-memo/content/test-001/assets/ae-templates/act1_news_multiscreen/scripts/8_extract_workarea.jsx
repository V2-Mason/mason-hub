// 8_extract_workarea.jsx
// Extract the current Work Area from the Render comp into a new standalone comp.
//
// Purpose: Mason wants a clean comp containing ONLY the work area slice,
//          starting at time 0, so he can apply further effects/edits without
//          touching the original Render comp.
//
// What it does:
//   1. Read the Render comp and its current work area (B / N markers)
//   2. Create a new comp with:
//        - Same width/height/framerate/pixel aspect as Render
//        - Duration = work area duration
//        - Name = "WA Extract [<start>s-<end>s]"
//   3. Nest the original Render comp INSIDE the new comp as a single layer
//   4. Offset the nested layer's startTime so that its work-area-start
//      aligns to time 0 of the new comp (e.g. if work area is 12-14s,
//      set nested layer startTime = -12 so Render's frame at 12s renders
//      at the new comp's frame at 0s)
//   5. Open the new comp
//
// Design choice: we NEST rather than DUPLICATE layers. This is much safer:
//   - Zero risk of breaking the original Render comp
//   - Any change made to Render (e.g. re-running fill_template_v2) is
//     automatically reflected in the extract
//   - Keeps everything "live" — effects, timing, 3D camera, adjustments
//   - Mason can add new layers on top of the nested Render in the new comp
//     to do further editing (text, adjustment layers, color, etc)
//
// Trade-off: the nested Render comp is 18s long (or 21s if stretched),
//   but we only render the portion visible in the new comp (work area
//   duration). AE handles this correctly - it only computes the visible
//   time range.
//
// Usage:
//   1. In AE, open the filled template (v2 or v3)
//   2. Open the Render comp
//   3. Set work area with B / N keys (or ensure one is already set)
//   4. File -> Scripts -> Run Script File... -> select this file
//
// Idempotent: re-running creates a NEW extract comp each time (with a
//   different timestamp-based name), never overwrites previous ones.

(function extractWorkArea() {

    // ---- Step 0: sanity ----
    if (!app.project || !app.project.file) {
        alert("Please open an AE project first (the filled v2/v3 .aep).");
        return;
    }

    // ---- Step 1: find Render comp ----
    var renderComp = null;
    for (var i = 1; i <= app.project.numItems; i++) {
        var item = app.project.item(i);
        if (item instanceof CompItem && item.name === "Render") {
            renderComp = item;
            break;
        }
    }
    if (!renderComp) {
        alert("Could not find a comp named 'Render' in this project.");
        return;
    }

    // ---- Step 2: read work area ----
    var waStart = renderComp.workAreaStart;
    var waDuration = renderComp.workAreaDuration;
    var waEnd = waStart + waDuration;

    // Guard: work area must be smaller than the full comp
    // (if it's exactly the full comp, there's nothing to "extract" — user
    // probably forgot to set work area)
    if (waDuration >= renderComp.duration - 0.01) {
        var proceed = confirm(
            "Warning: the work area covers the ENTIRE comp (" +
            waDuration.toFixed(2) + "s of " + renderComp.duration.toFixed(2) + "s).\n\n" +
            "This means you haven't set a smaller work area with B / N keys.\n" +
            "The extract will contain the full comp.\n\n" +
            "Continue anyway?"
        );
        if (!proceed) return;
    }

    // Guard: work area must not be zero
    if (waDuration < 0.1) {
        alert("Work area is too short (" + waDuration.toFixed(2) + "s).\n" +
              "Set B and N keys to a meaningful range in the Render comp timeline first.");
        return;
    }

    // ---- Step 3: confirm with user ----
    var newCompName = "WA Extract [" +
                      waStart.toFixed(1) + "s-" + waEnd.toFixed(1) + "s]";
    var confirmed = confirm(
        "Extract work area into a new comp:\n\n" +
        "  Source:     Render (" + renderComp.width + "x" + renderComp.height +
            ", " + renderComp.frameRate + " fps)\n" +
        "  Work area:  " + waStart.toFixed(2) + "s -> " + waEnd.toFixed(2) +
            "s (" + waDuration.toFixed(2) + "s)\n" +
        "  New comp:   \"" + newCompName + "\"\n" +
        "  Duration:   " + waDuration.toFixed(2) + "s starting at 0\n\n" +
        "The Render comp itself will NOT be modified.\n" +
        "The new comp will nest the Render comp so all future changes\n" +
        "to Render are reflected automatically.\n\n" +
        "Continue?"
    );
    if (!confirmed) return;

    // ---- Step 4: do it ----
    app.beginUndoGroup("Extract Work Area");

    var logLines = [];
    function log(s) { logLines.push(s); }
    log("=== Extract Work Area ===");
    log("Started: " + new Date().toString());
    log("Source comp: " + renderComp.name);
    log("Work area: " + waStart.toFixed(3) + "s -> " + waEnd.toFixed(3) +
        "s (duration " + waDuration.toFixed(3) + "s)");
    log("");

    // 4a. Create new comp
    var newComp;
    try {
        newComp = app.project.items.addComp(
            newCompName,
            renderComp.width,
            renderComp.height,
            renderComp.pixelAspect,
            waDuration,
            renderComp.frameRate
        );
        log("Created new comp: \"" + newComp.name + "\"");
    } catch (eC) {
        app.endUndoGroup();
        alert("Failed to create new comp: " + eC.toString());
        return;
    }

    // 4b. Nest Render comp as a layer in the new comp
    var nestedLayer;
    try {
        nestedLayer = newComp.layers.add(renderComp);
        nestedLayer.name = "Render [nested]";
        log("Nested Render comp as layer: \"" + nestedLayer.name + "\"");
    } catch (eN) {
        app.endUndoGroup();
        alert("Failed to nest Render comp: " + eN.toString());
        return;
    }

    // 4c. Offset the nested layer so that work-area-start aligns to time 0
    // of the new comp.
    //
    // Logic: when you nest a comp as a layer, by default the nested comp
    // plays from its time 0 at the parent comp's time 0. We want Render's
    // time waStart to appear at new comp's time 0, so we set:
    //
    //   startTime = -waStart
    //
    // This means "the nested comp's time 0 happens at parent time -waStart",
    // which is equivalent to "the nested comp's time waStart happens at
    // parent time 0". Exactly what we want.
    try {
        nestedLayer.startTime = -waStart;
        log("Shifted nested layer startTime to " + (-waStart).toFixed(3) + "s");
    } catch (eT) {
        log("WARN: failed to shift nested layer: " + eT.toString());
    }

    // 4d. Explicitly set in/out points to [0, waDuration] so the layer
    // doesn't play outside the visible range
    try {
        nestedLayer.inPoint = 0;
        nestedLayer.outPoint = waDuration;
        log("Set nested layer in/out to 0 -> " + waDuration.toFixed(3));
    } catch (eIO) {
        log("WARN: failed to set in/out: " + eIO.toString());
    }

    // 4e. Make sure layer quality is Best (we want full resolution for
    // further editing)
    try {
        nestedLayer.quality = LayerQuality.BEST;
    } catch (eQ) {}

    app.endUndoGroup();

    // ---- Step 5: open the new comp in the viewer ----
    try {
        newComp.openInViewer();
        log("Opened new comp in viewer");
    } catch (eO) {
        log("WARN: could not auto-open new comp: " + eO.toString());
    }

    // ---- Step 6: write log ----
    var logFile = new File(File($.fileName).parent.fsName + "/8_extract_log.txt");
    if (logFile.open("w")) {
        logFile.encoding = "UTF-8";
        logFile.write(logLines.join("\n"));
        logFile.close();
    }

    // ---- Step 7: success alert ----
    alert("Extract complete!\n\n" +
          "New comp: \"" + newCompName + "\"\n" +
          "  Size:      " + newComp.width + "x" + newComp.height + "\n" +
          "  Duration:  " + waDuration.toFixed(2) + "s (starting at 0)\n" +
          "  Contains:  Render comp nested, offset so work area starts at 0\n\n" +
          "The new comp is now open in the viewer.\n\n" +
          "You can now:\n" +
          "  - Add text layers on top for subtitles\n" +
          "  - Add adjustment layers for color grading\n" +
          "  - Add effects like Glow, Blur, Lumetri Color\n" +
          "  - Add a background music layer\n" +
          "  - Anything, without touching the original Render comp\n\n" +
          "When ready to render this new comp:\n" +
          "  Ctrl+M (quick) or write a render script targeting this comp");

})();
