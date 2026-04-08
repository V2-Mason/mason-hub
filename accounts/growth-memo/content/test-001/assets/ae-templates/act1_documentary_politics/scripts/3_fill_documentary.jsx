// 3_fill_documentary.jsx
// Documentary Politics template filler
//
// Pipeline:
//   1. Read 2_mapping.json next to this script
//   2. For each panel_mapping, import the clip and add it as a layer
//      inside the target PlaceHolder_N precomp (empty comp -> gets 1 footage layer)
//   3. Disable listed Scene layers in the main "*RENDER ME" comp
//   4. Save as filled_v1.aep
//
// Idempotent: removes any previous [FILLED] layers before re-adding.
//
// Usage:
//   1. Open "Documental Political FullHD (converted).aep" in AE
//   2. Ctrl+S once
//   3. File -> Scripts -> Run Script File... -> select this file

(function fillDocumentary() {

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

    // templateRoot = parent of scripts/  (i.e. act1_documentary_politics/)
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
    log("=== Fill Documentary Template ===");
    log("Started: " + new Date().toString());
    log("Mapping file: " + mappingFile.fsName);
    log("Template root: " + templateRoot.fsName);
    log("Panels to fill: " + mapping.panel_mappings.length);
    log("Scenes to disable: " + (mapping.disable_scenes ? mapping.disable_scenes.length : 0));
    log("");

    var success = 0;
    var failed = 0;

    app.beginUndoGroup("Fill Documentary Template");

    // ---- Step 1: fill placeholder comps ----
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

            // Remove any previously-added [FILLED] layer (idempotent re-run)
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

            // Align layer to comp start time 0
            newLayer.startTime = 0;
            newLayer.inPoint = 0;

            // Scale to cover the comp (1920x1080 -> 1920x1080, no-op but safe)
            scaleLayerToFitComp(newLayer, targetComp);

            // Force best quality
            try {
                newLayer.quality = LayerQuality.BEST;
            } catch (eQ) {}

            log(prefix + " OK  (duration=" + footage.duration.toFixed(3) + "s)");
            success++;
        } catch (e) {
            log(prefix + " FAIL: " + e.toString());
            failed++;
        }
    }

    // ---- Step 2: disable unused scenes in *RENDER ME ----
    var renderComp = compIndex["*RENDER ME"];
    if (!renderComp) {
        log("");
        log("ERROR: Comp '*RENDER ME' not found - cannot disable scenes");
    } else if (mapping.disable_scenes && mapping.disable_scenes.length > 0) {
        log("");
        log("--- Disabling unused scenes in *RENDER ME ---");
        for (var d = 0; d < mapping.disable_scenes.length; d++) {
            var sceneName = mapping.disable_scenes[d];
            var found = false;
            for (var L2 = 1; L2 <= renderComp.numLayers; L2++) {
                var sceneLayer = renderComp.layer(L2);
                if (sceneLayer.name === sceneName) {
                    sceneLayer.enabled = false;
                    log("  DISABLED: " + sceneName);
                    found = true;
                    break;
                }
            }
            if (!found) {
                log("  WARN not found: " + sceneName);
            }
        }
    }

    app.endUndoGroup();

    // ---- Step 3: Save As ----
    var saveAsRel = mapping.save_as || "Documental Political FullHD/filled_v1.aep";
    var saveAsFile = new File(templateRoot.fsName + "/" + saveAsRel);
    try {
        app.project.save(saveAsFile);
        log("");
        log("Saved as: " + saveAsFile.fsName);
    } catch (eSave) {
        log("");
        log("SAVE FAILED: " + eSave.toString());
    }

    // Write log
    var logFile = new File(scriptDir.fsName + "/3_fill_log.txt");
    if (logFile.open("w")) {
        logFile.encoding = "UTF-8";
        logFile.write(logLines.join("\n"));
        logFile.close();
    }

    alert("Fill Documentary complete!\n\n" +
          "Placeholders filled: " + success + "/" + mapping.panel_mappings.length + "\n" +
          "Failed: " + failed + "\n" +
          "Scenes disabled: " + (mapping.disable_scenes ? mapping.disable_scenes.length : 0) + "\n\n" +
          "Saved as: " + saveAsRel + "\n\n" +
          "Next: open *RENDER ME and preview, then Composition -> Add to Render Queue.");

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
