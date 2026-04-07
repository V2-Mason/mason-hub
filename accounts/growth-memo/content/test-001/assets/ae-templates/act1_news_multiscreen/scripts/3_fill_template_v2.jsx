// 3_fill_template_v2.jsx
// Multiscreen template filler - v2 (mute audio + unify color)
//
// Same as 3_fill_template.jsx but with two additional behaviors:
//   1. AUDIO MUTE: every [FILLED] layer has audioEnabled = false
//      (avoids 22 overlapping news broadcasts)
//   2. COLOR UNIFY: every [FILLED] layer gets a Hue/Saturation effect
//      with Master Saturation = -50, pulling 22 different sources
//      toward a unified cool/desaturated tone
//
// Idempotent - safe to re-run. Removes previous [FILLED] layers and
// re-creates them with the new settings.

(function fillTemplateV2() {

    var scriptFile = File($.fileName);
    var scriptDir = scriptFile.parent;
    var mappingFile = new File(scriptDir.fsName + "/2_mapping.json");

    if (!mappingFile.exists) {
        alert("mapping.json not found at:\n" + mappingFile.fsName);
        return;
    }

    if (!mappingFile.open("r")) {
        alert("Failed to open mapping.json");
        return;
    }
    mappingFile.encoding = "UTF-8";
    var jsonText = mappingFile.read();
    mappingFile.close();

    var mapping;
    try {
        mapping = parseJSON(jsonText);
    } catch (e) {
        alert("Failed to parse mapping.json:\n" + e.toString());
        return;
    }

    if (!mapping.panel_mappings || mapping.panel_mappings.length === 0) {
        alert("mapping.json has no panel_mappings");
        return;
    }

    if (!app.project || !app.project.file) {
        alert("Please open and save the .aep template first.");
        return;
    }

    var templateRoot = scriptDir.parent;

    // Build name -> CompItem index
    var compIndex = {};
    for (var i = 1; i <= app.project.numItems; i++) {
        var item = app.project.item(i);
        if (item instanceof CompItem) {
            compIndex[item.name] = item;
        }
    }

    var logLines = [];
    function log(s) { logLines.push(s); }
    log("=== Fill Template Run (v2: mute + desaturate) ===");
    log("Started: " + new Date().toString());
    log("Mapping file: " + mappingFile.fsName);
    log("Template root: " + templateRoot.fsName);
    log("Total panels to fill: " + mapping.panel_mappings.length);
    log("");

    var success = 0;
    var failed = 0;

    app.beginUndoGroup("Fill Multiscreen Template v2");

    for (var p = 0; p < mapping.panel_mappings.length; p++) {
        var pm = mapping.panel_mappings[p];
        var compName = pm.comp_name;
        var clipRel = pm.clip_path;
        var tier = pm.tier || "?";

        var prefix = "[" + (p + 1) + "/" + mapping.panel_mappings.length + "] " +
                     compName + " <- " + clipRel + " (" + tier + ")";

        try {
            var targetComp = compIndex[compName];
            if (!targetComp) {
                throw new Error("Comp not found: " + compName);
            }

            var clipFile = new File(templateRoot.fsName + "/" + clipRel);
            if (!clipFile.exists) {
                throw new Error("Clip file not found: " + clipFile.fsName);
            }

            var footage = findExistingFootage(clipFile);
            if (!footage) {
                var importOptions = new ImportOptions(clipFile);
                footage = app.project.importFile(importOptions);
            }

            // Remove any previously-added [FILLED] layer
            for (var L = targetComp.numLayers; L >= 1; L--) {
                var existing = targetComp.layer(L);
                if (existing.name.indexOf("[FILLED]") === 0) {
                    existing.remove();
                }
            }

            // Add new footage layer
            var newLayer = targetComp.layers.add(footage);
            newLayer.name = "[FILLED] " + footage.name;
            newLayer.moveToBeginning();

            // Cover-fit scale
            scaleLayerToFitComp(newLayer, targetComp);

            // V4 NEW: apply clip_start offset from mapping
            // This makes the footage play starting from a specific time
            // inside the source mp4 (rather than from 0), so hero clips
            // show their most impactful moment instead of the intro/filler.
            //
            // Mechanism: set layer startTime to -clip_start, so that the
            // source mp4's time = clip_start aligns to the comp's time 0.
            // Then clamp inPoint to 0 so the layer is visible from comp start.
            if (typeof pm.clip_start === "number" && pm.clip_start > 0) {
                try {
                    newLayer.startTime = -pm.clip_start;
                    newLayer.inPoint = 0;
                    // outPoint stays at the comp's end (default)
                    log(prefix + " clip_start=" + pm.clip_start + "s");
                } catch (eCS) {
                    log(prefix + " WARN: failed to apply clip_start: " + eCS.toString());
                }
            }

            // V3 CHANGE: audio NO LONGER muted per Mason feedback
            // Previously v2 set newLayer.audioEnabled = false to prevent
            // 22 simultaneous news broadcasts. With WA Extract approach
            // we now want the original audio so it can be heard in the
            // close-up sequence. If you need to mute, run 7_mute_everything.jsx

            // V3 CHANGE: Hue/Sat removed per Mason feedback ("need original colors")
            // Previously this block applied ADBE HUE SATURATION with Master Saturation -50.
            // Removed so the filled layers keep the original footage colors.

            // V2 NEW #3: force layer quality to Best
            try {
                newLayer.quality = LayerQuality.BEST;
            } catch (eQ) {}

            // Disable original placeholder
            var num = compName.replace("Media ", "");
            var placeholderName = "Placeholder " + num;
            try {
                var ph = targetComp.layer(placeholderName);
                if (ph) ph.enabled = false;
            } catch (eP) {
                log(prefix + " WARN: placeholder \"" + placeholderName + "\" not found");
            }

            log(prefix + " OK");
            success++;
        } catch (e) {
            log(prefix + " FAIL: " + e.toString());
            failed++;
        }
    }

    app.endUndoGroup();

    // Save As
    var saveAsName = mapping.save_as || "Multiscreen Intro filled v1.aep";
    // For v2 we save to a different file name to keep v1 intact
    saveAsName = "Multiscreen Intro filled v2.aep";
    var saveAsFile = new File(templateRoot.fsName + "/" + saveAsName);
    try {
        app.project.save(saveAsFile);
        log("");
        log("Saved as: " + saveAsFile.fsName);
    } catch (eSave) {
        log("");
        log("SAVE FAILED: " + eSave.toString());
    }

    // Write log
    var logFile = new File(scriptDir.fsName + "/3_fill_v2_log.txt");
    if (logFile.open("w")) {
        logFile.encoding = "UTF-8";
        logFile.write(logLines.join("\n"));
        logFile.close();
    }

    alert("Fill v2 complete!\n\n" +
          "Success: " + success + "\n" +
          "Failed:  " + failed + "\n\n" +
          "Audio: ENABLED (original audio kept)\n" +
          "Color: ORIGINAL (no Hue/Sat applied)\n\n" +
          "Saved as: " + saveAsName + "\n\n" +
          "Log: " + logFile.fsName);

    // ---- Helpers ----

    function parseJSON(s) {
        if (typeof JSON !== "undefined" && JSON.parse) {
            return JSON.parse(s);
        }
        if (s.charCodeAt(0) === 0xFEFF) s = s.substring(1);
        return eval("(" + s + ")");
    }

    function findExistingFootage(file) {
        for (var k = 1; k <= app.project.numItems; k++) {
            var item = app.project.item(k);
            if (item instanceof FootageItem && item.file && item.file.fsName === file.fsName) {
                return item;
            }
        }
        return null;
    }

    function scaleLayerToFitComp(layer, comp) {
        var src = layer.source;
        if (!src || !src.width || !src.height) return;

        var sx = (comp.width / src.width) * 100;
        var sy = (comp.height / src.height) * 100;
        var s = Math.max(sx, sy);

        try {
            layer.property("Transform").property("Scale").setValue([s, s]);
            layer.property("Transform").property("Position").setValue([comp.width / 2, comp.height / 2]);
            layer.property("Transform").property("Anchor Point").setValue([src.width / 2, src.height / 2]);
        } catch (eS) {}
    }

})();
