// 6_stretch_closeups.jsx
// Extend the 4 close-up shots in the Render comp to 1.2s each,
// shift everything after them backward to keep Scene 05 + Outro intact.
//
// Context: Adobe Stock template originally has 4 close-ups at 12.00-13.75s,
//          each ~0.42s long. Mason's feedback: too fast, cannot even speak a
//          full narration line per shot. So we stretch each close-up to 1.2s.
//
// What it does:
//   1. Find the 4 close-up layers in Render comp: Media 05/08/07/09 Precomp
//      (in timeline order: 05 first at 12.00, then 08, then 07, then 09)
//   2. Set each one to exactly 1.2s duration, chained back-to-back starting
//      at 12.00s
//   3. Shift every OTHER layer that starts at >= 13.75s backward by 3.05s
//      (so Scene 05, Outro, and all trailing elements stay intact, just
//      delayed by the amount the close-ups grew)
//   4. Extend comp duration from 18s to 21.05s
//   5. Update work area to cover full new duration
//   6. Save as "Multiscreen Intro filled v3.aep"
//
// Usage:
//   1. Open "Multiscreen Intro filled v2.aep" (run fill v2 first to get clean state)
//   2. File -> Scripts -> Run Script File... -> select this file
//
// Idempotent: checks if already stretched, refuses to re-apply.

(function stretchCloseups() {

    // ---- Sanity check ----
    if (!app.project || !app.project.file) {
        alert("Please open the v2 .aep first.");
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
        alert("Could not find 'Render' comp in the project.");
        return;
    }

    // ---- Step 2: detect if already stretched ----
    // We look at the current layer at position 23 (Media 01 Precomp in original).
    // In original template, layers 20-23 are Media 04/03/02/01 Precomp between
    // 6.50s and 8.20s. If the SECOND group of close-ups (layers 7-10) still sits
    // at 12.00-13.75s, it is original state. If it is already at 12.00-16.80s,
    // we have already stretched.
    //
    // Simpler detection: check if comp duration is 18s (untouched) or ~21s (done)
    if (renderComp.duration > 19.0) {
        alert("This project appears to already be stretched " +
              "(comp duration = " + renderComp.duration.toFixed(2) + "s).\n\n" +
              "If you want to re-stretch, re-run 3_fill_template_v2.jsx first " +
              "to get a clean v2 state.");
        return;
    }

    // ---- Step 3: find the 4 close-up layers ----
    // These are layers in Render comp whose source is one of:
    //   Media 05 Precomp, Media 07 Precomp, Media 08 Precomp, Media 09 Precomp
    // AND whose inPoint is between 12.0s and 13.75s (the close-up section,
    // NOT the Scene 05 precomp layers which also reference these names
    // indirectly through Line_Vert)
    //
    // From the inspect report, in Render comp the relevant layers are:
    //   Layer index 7:  "Media 09 Precomp" in=13.25 out=13.75 (4th close-up)
    //   Layer index 8:  "Media 07 Precomp" in=12.83 out=13.25 (3rd close-up)
    //   Layer index 9:  "Media 08 Precomp" in=12.42 out=12.83 (2nd close-up)
    //   Layer index 10: "Media 05 Precomp" in=12.00 out=12.42 (1st close-up)

    var closeups = []; // {layer, order, origIn, origOut}
    for (var L = 1; L <= renderComp.numLayers; L++) {
        var lay = renderComp.layer(L);
        if (!(lay instanceof AVLayer)) continue;
        if (!lay.source) continue;

        var srcName = lay.source.name;
        var isTarget = (srcName === "Media 05 Precomp" ||
                        srcName === "Media 07 Precomp" ||
                        srcName === "Media 08 Precomp" ||
                        srcName === "Media 09 Precomp");
        if (!isTarget) continue;

        // Must be in close-up time region (not the sparse ones used in Scene 05)
        if (lay.inPoint < 11.5 || lay.inPoint > 13.8) continue;

        // Determine order by inPoint
        var order;
        if      (srcName === "Media 05 Precomp") order = 1; // 12.00
        else if (srcName === "Media 08 Precomp") order = 2; // 12.42
        else if (srcName === "Media 07 Precomp") order = 3; // 12.83
        else if (srcName === "Media 09 Precomp") order = 4; // 13.25

        closeups.push({
            layer: lay,
            order: order,
            srcName: srcName,
            origIn: lay.inPoint,
            origOut: lay.outPoint,
            origStart: lay.startTime
        });
    }

    if (closeups.length !== 4) {
        alert("Expected 4 close-up layers (Media 05/07/08/09 Precomp at 12-13.75s),\n" +
              "but found " + closeups.length + ".\n\n" +
              "Found:\n" + closeups.map(function(c) {
                  return "  " + c.srcName + " at " + c.origIn.toFixed(2);
              }).join("\n") +
              "\n\nAborting to avoid damage.");
        return;
    }

    // Sort by desired order (1=Meta, 2=Amazon, 3=Google, 4=Chegg)
    closeups.sort(function(a, b) { return a.order - b.order; });

    // ---- Step 4: calculate timing for 2-clip mode (Meta + Amazon only) ----
    // v5 CHANGE: Only Media 05 (Meta) and Media 08 (Amazon) are hero clips.
    // Media 07 and Media 09 are now filled with fill content (not heroes),
    // so we DISABLE them in the close-up sequence to avoid jarring 0.4s
    // interruptions between Meta and Amazon.
    //
    // New timing:
    //   Media 05 (Meta)    : 12.00 - 17.61s  (5.61s, full clip)
    //   Media 08 (Amazon)  : 17.61 - 21.61s  (4.00s, full clip)
    //   Media 07 / 09      : disabled
    //
    // Old total (4 close-ups) = 1.75s
    // New total (2 close-ups) = 5.61 + 4.00 = 9.61s
    // Delta = 9.61 - 1.75 = 7.86s
    var META_DURATION = 5.00;
    var AMZN_DURATION = 3.54;
    var OLD_START = 12.00;
    var OLD_END = 13.75;
    var OLD_TOTAL = OLD_END - OLD_START; // 1.75s
    var NEW_TOTAL = META_DURATION + AMZN_DURATION; // 9.61s
    var DELTA = NEW_TOTAL - OLD_TOTAL; // 7.86s

    // ---- Step 5: confirm with user ----
    var confirmed = confirm(
        "Stretch 2 close-ups (Meta + Amazon only):\n\n" +
        "  [1] Meta    (Media 05)  12.00 -> 17.00s  (5.00s)\n" +
        "  [2] Amazon  (Media 08)  17.00 -> 20.54s  (3.54s)\n" +
        "  [x] Media 07 & 09: DISABLED (not heroes anymore)\n\n" +
        "Scene 05 + Outro + everything after will shift back by " +
        DELTA.toFixed(2) + "s\n\n" +
        "Save as: Multiscreen Intro filled v3.aep\n\n" +
        "Continue?"
    );
    if (!confirmed) return;

    // ---- Step 6: do the work in one undo group ----
    app.beginUndoGroup("Stretch Close-ups to 2.5s");

    var logLines = [];
    function log(s) { logLines.push(s); }
    log("=== Stretch Close-ups ===");
    log("Started: " + new Date().toString());
    log("");

    // ---- Step 6a: extend comp duration FIRST (needed before moving layers) ----
    var newCompDuration = renderComp.duration + DELTA;
    try {
        renderComp.duration = newCompDuration;
        log("Comp duration: " + (renderComp.duration - DELTA).toFixed(2) + "s -> " +
            renderComp.duration.toFixed(2) + "s");
    } catch (eD) {
        log("WARN: failed to extend duration: " + eD.toString());
    }

    // ---- Step 6b: shift all non-closeup layers that start AFTER the closeup zone ----
    // Any layer with startTime >= 13.75s (or close enough, allow 0.1 tolerance)
    // should shift by +DELTA.
    //
    // EXCLUSIONS:
    //   - The 4 closeup layers themselves (we handle them separately)
    //   - Layers that span ACROSS the closeup zone (e.g. BG, Color Control etc
    //     which go from 0 to 18s) — we extend those instead of shifting
    //
    // LAYERS TO SHIFT: layers whose startTime >= 13.65 AND whose inPoint >= 13.65
    // LAYERS TO EXTEND: layers whose startTime < 13.65 AND outPoint >= 13.65
    //                   (they straddle the stretch boundary — we grow their out)

    var closeupLayerSet = {};
    for (var c = 0; c < closeups.length; c++) {
        closeupLayerSet[closeups[c].layer.index] = true;
    }

    var SHIFT_THRESHOLD = 13.65; // slightly before 13.75 to catch borderline
    var shiftCount = 0, extendCount = 0, unchangedCount = 0;

    // Iterate in reverse so we can safely change layers without index issues
    // (though we are not adding/removing layers, only modifying times)
    for (var L2 = 1; L2 <= renderComp.numLayers; L2++) {
        var lay2 = renderComp.layer(L2);
        if (closeupLayerSet[lay2.index]) continue; // skip closeups

        var lStart = lay2.startTime;
        var lOut = lay2.outPoint;

        if (lStart >= SHIFT_THRESHOLD) {
            // Shift this layer backward in time
            try {
                lay2.startTime = lStart + DELTA;
                shiftCount++;
                log("SHIFT: [" + lay2.index + "] \"" + lay2.name + "\" " +
                    lStart.toFixed(2) + " -> " + (lStart + DELTA).toFixed(2));
            } catch (eSh) {
                log("WARN: failed to shift layer " + lay2.name + ": " + eSh.toString());
            }
        } else if (lOut >= SHIFT_THRESHOLD) {
            // This layer STRADDLES the stretch boundary (e.g. BG 0-18, FX 0-18)
            // We need to extend its outPoint by DELTA so it keeps covering
            // the full (new) comp length
            try {
                lay2.outPoint = lOut + DELTA;
                extendCount++;
                log("EXTEND: [" + lay2.index + "] \"" + lay2.name + "\" out " +
                    lOut.toFixed(2) + " -> " + (lOut + DELTA).toFixed(2));
            } catch (eEx) {
                log("WARN: failed to extend layer " + lay2.name + ": " + eEx.toString());
            }
        } else {
            unchangedCount++;
        }
    }

    log("");
    log("Shifted: " + shiftCount + " layers");
    log("Extended: " + extendCount + " layers");
    log("Unchanged: " + unchangedCount + " layers");
    log("");

    // ---- Step 6c: stretch Meta + Amazon, disable Media 07 & 09 ----
    // v5: 2-clip mode (Meta + Amazon only)
    //
    // Meta    (Media 05) : 12.00 -> 17.61s  (5.61s, full clip)
    // Amazon  (Media 08) : 17.61 -> 21.61s  (4.00s, full clip)
    // Media 07 & 09      : disabled (hidden from timeline)

    for (var k = 0; k < closeups.length; k++) {
        var co = closeups[k];
        var newIn, newOut, duration;

        if (co.srcName === "Media 05 Precomp") {
            // Meta
            newIn = OLD_START;
            duration = META_DURATION;
            newOut = newIn + duration;
        } else if (co.srcName === "Media 08 Precomp") {
            // Amazon (starts right after Meta ends)
            newIn = OLD_START + META_DURATION;
            duration = AMZN_DURATION;
            newOut = newIn + duration;
        } else {
            // Media 07 / 09: disable these layers (not heroes anymore)
            try {
                co.layer.enabled = false;
                log("DISABLED: " + co.srcName + " (now a fill, not a hero)");
            } catch (eD) {
                log("WARN: failed to disable " + co.srcName + ": " + eD.toString());
            }
            continue;
        }

        try {
            co.layer.startTime = newIn;
            co.layer.inPoint = newIn;
            co.layer.outPoint = newOut;

            log("STRETCH: " + co.srcName + " " +
                co.origIn.toFixed(2) + "-" + co.origOut.toFixed(2) +
                " (" + (co.origOut - co.origIn).toFixed(2) + "s) -> " +
                newIn.toFixed(2) + "-" + newOut.toFixed(2) +
                " (" + duration.toFixed(2) + "s)");
        } catch (eSt) {
            log("WARN: failed to stretch " + co.srcName + ": " + eSt.toString());
        }
    }

    // ---- Step 6d: update work area to cover full new duration ----
    try {
        renderComp.workAreaStart = 0;
        renderComp.workAreaDuration = newCompDuration;
        log("");
        log("Work area: 0 - " + newCompDuration.toFixed(2) + "s");
    } catch (eW) {
        log("WARN: failed to set work area: " + eW.toString());
    }

    app.endUndoGroup();

    // ---- Step 7: Save As ----
    var saveAsFile = new File(app.project.file.parent.fsName + "/Multiscreen Intro filled v3.aep");
    try {
        app.project.save(saveAsFile);
        log("");
        log("Saved as: " + saveAsFile.fsName);
    } catch (eSave) {
        log("");
        log("SAVE FAILED: " + eSave.toString());
    }

    // ---- Step 8: write log + alert ----
    var logFile = new File(File($.fileName).parent.fsName + "/6_stretch_log.txt");
    if (logFile.open("w")) {
        logFile.encoding = "UTF-8";
        logFile.write(logLines.join("\n"));
        logFile.close();
    }

    alert("Stretch complete!\n\n" +
          "4 close-ups now at 1.2s each:\n" +
          "  12.00-13.20s  Meta\n" +
          "  13.20-14.40s  Amazon\n" +
          "  14.40-15.60s  Google\n" +
          "  15.60-16.80s  Chegg\n\n" +
          "Scene 05 now starts at 16.80s (was 13.75s)\n" +
          "Comp duration: " + newCompDuration.toFixed(2) + "s (was 18s)\n\n" +
          "Layers shifted: " + shiftCount + "\n" +
          "Layers extended: " + extendCount + "\n\n" +
          "Saved as: Multiscreen Intro filled v3.aep\n\n" +
          "Next: run 4_render_template.jsx and choose Climax mode\n" +
          "(Climax now renders 12-18s which covers the 4 stretched close-ups)\n\n" +
          "Log: " + logFile.fsName);

})();
