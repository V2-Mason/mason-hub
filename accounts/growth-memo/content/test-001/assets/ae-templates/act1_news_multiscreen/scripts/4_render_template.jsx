// 4_render_template.jsx
// Render the filled multiscreen template to mp4
//
// Purpose: Add the "Render" comp to AE's render queue with H.264 settings
//          and start rendering. Two modes:
//            - test mode: render only first 1 second (fast verification)
//            - full mode: render the entire 18 seconds
//
// Usage:
//   1. Open "Multiscreen Intro filled v1.aep" (the FILLED template)
//   2. File -> Scripts -> Run Script File... -> select 4_render_template.jsx
//   3. A dialog asks: Test (1 sec) or Full (18 sec)?
//   4. Output mp4 lands in: act1_news_multiscreen/output/
//
// Notes:
//   - Output module: H.264 - Match Render Settings - 15 Mbps
//     If your AE installation does not have this preset, the script falls
//     back to the first H.264 preset it can find, then logs a warning.
//   - The script does NOT block AE while rendering. After clicking OK,
//     AE switches to the Render Queue panel and starts rendering. You can
//     watch progress there. CPU will spike to 100% during render - normal.
//   - To cancel mid-render: Render Queue panel -> Stop button.
//   - The output filename includes a timestamp so reruns don't overwrite.

(function renderTemplate() {

    // ---- Step 0: sanity check ----
    if (!app.project || !app.project.file) {
        alert("Please open the filled .aep first.");
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
        alert("Could not find a comp named 'Render'.");
        return;
    }

    // ---- Step 2: ask user: test or full mode ----
    var modeWindow = new Window("dialog", "Render Mode");
    modeWindow.orientation = "column";
    modeWindow.alignChildren = "fill";
    modeWindow.spacing = 10;
    modeWindow.margins = 16;

    // Read current work area from the comp so we can show it in the dialog
    var waStart = renderComp.workAreaStart;
    var waDur = renderComp.workAreaDuration;
    var waEnd = waStart + waDur;

    var label = modeWindow.add("statictext", undefined,
        "Choose render mode:\n\n" +
        "WorkArea: render the work area you set in the timeline\n" +
        "  current: " + waStart.toFixed(2) + "s -> " + waEnd.toFixed(2) + "s (" + waDur.toFixed(2) + "s)\n\n" +
        "Test   (1 sec, starts at 12s): sanity check\n" +
        "Climax (12s -> end of close-ups + mosaic + outro)\n" +
        "Full   (entire comp): everything",
        { multiline: true });
    label.preferredSize.width = 460;

    var btnGroup = modeWindow.add("group");
    btnGroup.alignment = "center";
    var workAreaBtn = btnGroup.add("button", undefined, "WorkArea");
    var testBtn = btnGroup.add("button", undefined, "Test 1s");
    var climaxBtn = btnGroup.add("button", undefined, "Climax");
    var fullBtn = btnGroup.add("button", undefined, "Full");
    var cancelBtn = btnGroup.add("button", undefined, "Cancel");

    var mode = null;
    workAreaBtn.onClick = function() { mode = "workarea"; modeWindow.close(); };
    testBtn.onClick = function() { mode = "test"; modeWindow.close(); };
    climaxBtn.onClick = function() { mode = "climax"; modeWindow.close(); };
    fullBtn.onClick = function() { mode = "full"; modeWindow.close(); };
    cancelBtn.onClick = function() { mode = null; modeWindow.close(); };

    modeWindow.show();
    if (!mode) return;

    // ---- Step 3: prepare output path ----
    var scriptFile = File($.fileName);
    var scriptDir = scriptFile.parent;
    var templateRoot = scriptDir.parent;
    var outputDir = new Folder(templateRoot.fsName + "/output");
    if (!outputDir.exists) outputDir.create();

    var ts = timestamp();
    var nameSuffix = "";
    if (mode === "workarea") {
        // Include the work area time range in the filename for easy identification
        nameSuffix = "_" + waStart.toFixed(1) + "-" + waEnd.toFixed(1) + "s";
    }
    var outputName = "act1_mosaic_" + mode + nameSuffix + "_" + ts + ".mp4";
    var outputFile = new File(outputDir.fsName + "/" + outputName);

    // ---- Step 4: add to render queue ----
    var rqItem;
    try {
        rqItem = app.project.renderQueue.items.add(renderComp);
    } catch (eAdd) {
        alert("Failed to add Render comp to render queue:\n" + eAdd.toString());
        return;
    }

    // ---- Step 5: configure work area based on mode ----
    // NOTE: Climax duration depends on whether 6_stretch_closeups.jsx has been
    // applied. We detect this by reading the comp duration:
    //   - 18s (untouched) -> climax renders 12-18 (6 sec)
    //   - ~21s (stretched) -> climax renders 12-21 (9 sec) to cover all 4
    //     stretched close-ups + Scene 05 + start of outro
    var isStretched = (renderComp.duration > 19.0);
    var climaxStart = 12.0;
    var climaxDuration = isStretched ? (renderComp.duration - 12.0) : 6.0;

    if (mode === "test") {
        // Test: 1 second starting at 12.0s (the start of the close-up sequence)
        try {
            rqItem.timeSpanStart = 12.0;
            rqItem.timeSpanDuration = 1.0;
        } catch (eTime) {}
    } else if (mode === "climax") {
        try {
            rqItem.timeSpanStart = climaxStart;
            rqItem.timeSpanDuration = climaxDuration;
        } catch (eTime) {}
    } else if (mode === "workarea") {
        // Use whatever work area Mason set in the timeline (B / N keys)
        try {
            rqItem.timeSpanStart = renderComp.workAreaStart;
            rqItem.timeSpanDuration = renderComp.workAreaDuration;
        } catch (eTime) {}
    }
    // full mode: leave defaults (renders the entire comp)

    // ---- Step 6: choose H.264 output module preset ----
    var om = rqItem.outputModule(1);
    var presetUsed = "<unknown>";
    var fallback = false;

    var preferredPresets = [
        "H.264 - Match Render Settings - 15 Mbps",
        "H.264 - Match Render Settings - 5 Mbps",
        "H.264",
        "H.264 - High",
        "H.264 - Medium"
    ];

    var availablePresets = [];
    try {
        availablePresets = om.templates;
    } catch (eT) {}

    var picked = null;
    for (var p = 0; p < preferredPresets.length; p++) {
        if (containsString(availablePresets, preferredPresets[p])) {
            picked = preferredPresets[p];
            break;
        }
    }

    // Last resort: any template name containing "H.264"
    if (!picked) {
        for (var q = 0; q < availablePresets.length; q++) {
            if (availablePresets[q].toString().indexOf("H.264") >= 0) {
                picked = availablePresets[q];
                fallback = true;
                break;
            }
        }
    }

    if (picked) {
        try {
            om.applyTemplate(picked);
            presetUsed = picked;
        } catch (eApply) {
            // Continue with whatever default the template uses
            presetUsed = "<failed to apply: " + eApply.toString() + ">";
        }
    } else {
        // No H.264 found - use whatever default and warn user
        presetUsed = "<no H.264 preset found, using default>";
        fallback = true;
    }

    // ---- Step 7: set output file path ----
    try {
        om.file = outputFile;
    } catch (eFile) {
        alert("Failed to set output file:\n" + eFile.toString());
        return;
    }

    // ---- Step 8: tell user, start render ----
    var msg = "Render queue ready.\n\n" +
              "Mode:    " + mode + (mode === "test" ? " (1 sec)" : " (18 sec)") + "\n" +
              "Preset:  " + presetUsed + "\n" +
              "Output:  " + outputFile.fsName + "\n\n";

    if (fallback) {
        msg += "WARNING: preferred H.264 preset not found.\n" +
               "Render will use a fallback preset.\n\n";
    }

    msg += "Click OK to start rendering.\n" +
           "AE will switch to Render Queue panel.\n" +
           "CPU will spike to 100% during render - this is normal.";

    var go = confirm(msg);
    if (!go) {
        // User changed their mind - remove the queue item
        try { rqItem.remove(); } catch (eR) {}
        return;
    }

    // Switch UI focus to render queue
    try { app.executeCommand(2904); } catch (eUI) {}  // Window > Render Queue

    // Start the render
    try {
        app.project.renderQueue.render();
    } catch (eRender) {
        alert("Render failed to start:\n" + eRender.toString());
        return;
    }

    // ---- Step 9: render finished, show result ----
    var elapsed = "";
    try {
        var status = rqItem.status;
        var statusText = "Status: " + status;
        if (status === RQItemStatus.DONE) statusText = "DONE";
        else if (status === RQItemStatus.ERR_STOPPED) statusText = "ERROR / STOPPED";
        else if (status === RQItemStatus.USER_STOPPED) statusText = "USER STOPPED";
        elapsed = "\n\n" + statusText;
    } catch (eS) {}

    var existsMsg = outputFile.exists ?
        ("\n\nOutput file: " + outputFile.fsName + "\nSize: " + (outputFile.length / 1024 / 1024).toFixed(2) + " MB") :
        ("\n\nWARNING: output file not found at expected path:\n" + outputFile.fsName);

    alert("Render finished." + elapsed + existsMsg);

    // ---- Helpers ----

    function containsString(arr, target) {
        for (var i = 0; i < arr.length; i++) {
            if (arr[i].toString() === target) return true;
        }
        return false;
    }

    function timestamp() {
        var d = new Date();
        var pad = function(n) { return (n < 10 ? "0" : "") + n; };
        return d.getFullYear() +
               pad(d.getMonth() + 1) +
               pad(d.getDate()) + "_" +
               pad(d.getHours()) +
               pad(d.getMinutes()) +
               pad(d.getSeconds());
    }

})();
