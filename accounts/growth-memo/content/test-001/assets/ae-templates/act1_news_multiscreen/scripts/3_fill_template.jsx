// 3_fill_template.jsx
// Multiscreen template filler
//
// Purpose: Read 2_mapping.json next to this script. For each panel mapping
//          (e.g. "Media 01" -> "clips/01_en_C4_amzn_10000.mp4"):
//            1. Find the target Media XX comp
//            2. Import the clip into the project (or reuse if already imported)
//            3. Add the footage as a new layer at the top of the comp
//            4. Scale the new layer to fit the comp
//            5. Disable the original "Placeholder XX" TextLayer
//          When done, Save As to the filename specified in mapping.save_as.
//
// Usage:
//   1. Open the original .aep template in After Effects
//   2. Save it once so app.project.file is set
//   3. File -> Scripts -> Run Script File... -> select 3_fill_template.jsx
//
// Notes:
//   - Pure ExtendScript ES3, no external dependencies
//   - Idempotent for re-runs: skips importing if a footage with the same name
//     is already in the project, and removes any previously-added "[FILLED]"
//     layer from the target comp before adding the new one
//   - All operations wrapped in app.beginUndoGroup so a single Ctrl+Z reverts

(function fillTemplate() {

    // ---- Step 0: locate this script's directory and the JSON mapping ----
    var scriptFile = File($.fileName);
    var scriptDir = scriptFile.parent;
    var mappingFile = new File(scriptDir.fsName + "/2_mapping.json");

    if (!mappingFile.exists) {
        alert("mapping.json not found at:\n" + mappingFile.fsName);
        return;
    }

    // ---- Step 1: load and parse mapping JSON ----
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

    // ---- Step 2: project sanity check ----
    if (!app.project || !app.project.file) {
        alert("Please open and save the .aep template first.");
        return;
    }

    // The clip paths in mapping.json are relative to the template root
    // (one level up from the scripts/ folder)
    var templateRoot = scriptDir.parent;

    // ---- Step 3: build a name -> CompItem index for fast lookup ----
    var compIndex = {};
    for (var i = 1; i <= app.project.numItems; i++) {
        var item = app.project.item(i);
        if (item instanceof CompItem) {
            compIndex[item.name] = item;
        }
    }

    // ---- Step 4: log buffer ----
    var logLines = [];
    function log(s) { logLines.push(s); }
    log("=== Fill Template Run ===");
    log("Started: " + new Date().toString());
    log("Mapping file: " + mappingFile.fsName);
    log("Template root: " + templateRoot.fsName);
    log("Total panels to fill: " + mapping.panel_mappings.length);
    log("");

    // ---- Step 5: do the work in one undo group ----
    var success = 0;
    var failed = 0;

    app.beginUndoGroup("Fill Multiscreen Template");

    for (var p = 0; p < mapping.panel_mappings.length; p++) {
        var pm = mapping.panel_mappings[p];
        var compName = pm.comp_name;
        var clipRel = pm.clip_path;
        var tier = pm.tier || "?";

        var prefix = "[" + (p + 1) + "/" + mapping.panel_mappings.length + "] " +
                     compName + " <- " + clipRel + " (" + tier + ")";

        try {
            // 5a. Find target comp
            var targetComp = compIndex[compName];
            if (!targetComp) {
                throw new Error("Comp not found: " + compName);
            }

            // 5b. Resolve clip absolute path
            var clipFile = new File(templateRoot.fsName + "/" + clipRel);
            if (!clipFile.exists) {
                throw new Error("Clip file not found: " + clipFile.fsName);
            }

            // 5c. Import (or reuse existing footage with same file path)
            var footage = findExistingFootage(clipFile);
            if (!footage) {
                var importOptions = new ImportOptions(clipFile);
                footage = app.project.importFile(importOptions);
            }

            // 5d. Remove any previously-added [FILLED] layer in this comp
            //     (so re-running the script is idempotent)
            for (var L = targetComp.numLayers; L >= 1; L--) {
                var existing = targetComp.layer(L);
                if (existing.name.indexOf("[FILLED]") === 0) {
                    existing.remove();
                }
            }

            // 5e. Add new footage layer at the top of the comp
            var newLayer = targetComp.layers.add(footage);
            newLayer.name = "[FILLED] " + footage.name;
            newLayer.moveToBeginning();

            // 5f. Scale to fit the comp (cover, not letterbox)
            scaleLayerToFitComp(newLayer, targetComp);

            // 5g. Disable original placeholder text layer
            //     The placeholder name pattern is "Placeholder XX" where XX
            //     is the same 2-digit number as the comp name "Media XX"
            var num = compName.replace("Media ", "");
            var placeholderName = "Placeholder " + num;
            try {
                var ph = targetComp.layer(placeholderName);
                if (ph) ph.enabled = false;
            } catch (eP) {
                // placeholder not found, log but don't fail
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

    // ---- Step 6: Save As ----
    var saveAsName = mapping.save_as || "Multiscreen Intro filled v1.aep";
    var saveAsFile = new File(templateRoot.fsName + "/" + saveAsName);
    try {
        app.project.save(saveAsFile);
        log("");
        log("Saved as: " + saveAsFile.fsName);
    } catch (eSave) {
        log("");
        log("SAVE FAILED: " + eSave.toString());
    }

    // ---- Step 7: write log file ----
    var logFile = new File(scriptDir.fsName + "/3_fill_log.txt");
    if (logFile.open("w")) {
        logFile.encoding = "UTF-8";
        logFile.write(logLines.join("\n"));
        logFile.close();
    }

    alert("Fill complete!\n\n" +
          "Success: " + success + "\n" +
          "Failed:  " + failed + "\n\n" +
          "Saved as: " + saveAsName + "\n\n" +
          "Log: " + logFile.fsName);

    // ---- Helpers ----

    function parseJSON(s) {
        if (typeof JSON !== "undefined" && JSON.parse) {
            return JSON.parse(s);
        }
        // strip BOM if present
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
        // Cover-style fit: scale up so the layer fully covers the comp,
        // cropping any overflow
        var src = layer.source;
        if (!src || !src.width || !src.height) return;

        var sx = (comp.width / src.width) * 100;
        var sy = (comp.height / src.height) * 100;
        var s = Math.max(sx, sy);  // cover, not letterbox

        try {
            layer.property("Transform").property("Scale").setValue([s, s]);
            // Center the layer in the comp
            layer.property("Transform").property("Position").setValue([comp.width / 2, comp.height / 2]);
            // Anchor point at source center
            layer.property("Transform").property("Anchor Point").setValue([src.width / 2, src.height / 2]);
        } catch (eS) {
            // ignore transform errors
        }
    }

})();
