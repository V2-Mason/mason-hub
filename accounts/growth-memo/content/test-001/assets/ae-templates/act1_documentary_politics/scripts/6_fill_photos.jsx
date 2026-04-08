// 6_fill_photos.jsx
// Documentary Politics template - PHOTO FILL + TEXT CAPTION
//
// Correct usage per Help PDF:
//   - PlaceHolder_N = empty comp where you drop your main image
//   - TextHolder_N = caption overlay on top of the image
//   - Scene N internally references PlaceHolder + TextHolder with various
//     position/mask animations (camera pan, fade, multi-window mosaic)
//   - "Brightness Control" in each Scene darkens the image so it matches
//     the archive/documentary look
//
// This script:
//   1. Imports 5 JPG stills and adds each as a layer inside PlaceHolder_1..5
//   2. Updates TextHolder_1..5 with "The X / Y" captions
//   3. Disables Scene 6..17 in *RENDER ME (we only use 5 scenes)
//   4. Sets *RENDER ME work area to 0.00-17.56s (first 5 scenes only)
//   5. Saves as filled_photos_v1.aep
//
// Idempotent: safe to re-run. Removes previous [FILLED] layers first.
//
// Usage:
//   1. Open "Documental Political FullHD (converted).aep" (CLEAN version, not filled_*)
//   2. Ctrl+S once
//   3. File -> Scripts -> Run Script File... -> select this file

(function fillPhotos() {

    var scriptFile = File($.fileName);
    var scriptDir = scriptFile.parent;
    var mappingFile = new File(scriptDir.fsName + "/6_fill_photos_mapping.json");

    if (!mappingFile.exists) {
        alert("mapping not found at:\n" + mappingFile.fsName);
        return;
    }
    if (!mappingFile.open("r")) {
        alert("Failed to open mapping");
        return;
    }
    mappingFile.encoding = "UTF-8";
    var jsonText = mappingFile.read();
    mappingFile.close();

    var mapping;
    try {
        mapping = parseJSON(jsonText);
    } catch (e) {
        alert("Failed to parse mapping:\n" + e.toString());
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
    log("=== Fill Photos (Documentary Politics) ===");
    log("Started: " + new Date().toString());
    log("Mapping: " + mappingFile.fsName);
    log("");

    app.beginUndoGroup("Fill Photos Documentary");

    var photoOk = 0, photoFail = 0;
    var textOk = 0, textFail = 0;
    var sceneDisabled = 0;

    // ---- Step 1: Fill PlaceHolder comps with photos ----
    log("--- Step 1: Fill PlaceHolders with hero stills ---");
    if (mapping.placeholders) {
        for (var p = 0; p < mapping.placeholders.length; p++) {
            var ph = mapping.placeholders[p];
            var phComp = compIndex[ph.comp_name];
            var prefix = "  " + ph.comp_name + " <- " + ph.photo_path;

            if (!phComp) {
                log(prefix + " FAIL: comp not found");
                photoFail++;
                continue;
            }

            try {
                var photoFile = new File(templateRoot.fsName + "/" + ph.photo_path);
                if (!photoFile.exists) {
                    throw new Error("photo file not found: " + photoFile.fsName);
                }

                var footage = findExistingFootage(photoFile);
                if (!footage) {
                    var importOptions = new ImportOptions(photoFile);
                    footage = app.project.importFile(importOptions);
                }

                // Remove any previously-added [FILLED] layer (idempotent re-run)
                for (var L = phComp.numLayers; L >= 1; L--) {
                    var existing = phComp.layer(L);
                    if (existing.name.indexOf("[FILLED]") === 0) {
                        existing.remove();
                    }
                }

                var newLayer = phComp.layers.add(footage);
                newLayer.name = "[FILLED] " + footage.name;
                newLayer.moveToBeginning();

                newLayer.startTime = 0;
                newLayer.inPoint = 0;
                // Photos have no outPoint issue - they are still images

                scaleLayerToFitComp(newLayer, phComp);

                try {
                    newLayer.quality = LayerQuality.BEST;
                } catch (eQ) {}

                log(prefix + " OK");
                photoOk++;
            } catch (eP) {
                log(prefix + " FAIL: " + eP.toString());
                photoFail++;
            }
        }
    }

    // ---- Step 2: Update TextHolders ----
    log("");
    log("--- Step 2: Update TextHolders (D1 captions) ---");
    if (mapping.text_holders) {
        for (var t = 0; t < mapping.text_holders.length; t++) {
            var th = mapping.text_holders[t];
            var thComp = compIndex[th.comp_name];
            var tprefix = "  " + th.comp_name;

            if (!thComp) {
                log(tprefix + " FAIL: comp not found");
                textFail++;
                continue;
            }
            try {
                var t1Layer = findLayerByName(thComp, "text 1");
                var t2Layer = findLayerByName(thComp, "text 2");
                if (t1Layer && t1Layer instanceof TextLayer) {
                    setTextContent(t1Layer, th.text_1 || "");
                }
                if (t2Layer && t2Layer instanceof TextLayer) {
                    setTextContent(t2Layer, th.text_2 || "");
                }
                log(tprefix + " OK: \"" + (th.text_1 || "") + "\" / \"" + (th.text_2 || "") + "\"");
                textOk++;
            } catch (eT) {
                log(tprefix + " FAIL: " + eT.toString());
                textFail++;
            }
        }
    }

    // ---- Step 3: Disable Scene 6-17 in *RENDER ME ----
    log("");
    log("--- Step 3: Disable Scene 6-17 in *RENDER ME ---");
    var renderComp = compIndex["*RENDER ME"];
    if (!renderComp) {
        log("  ERROR: '*RENDER ME' not found");
    } else if (mapping.disable_scenes_in_render) {
        for (var d = 0; d < mapping.disable_scenes_in_render.length; d++) {
            var dname = mapping.disable_scenes_in_render[d];
            var found = false;
            for (var L2 = 1; L2 <= renderComp.numLayers; L2++) {
                var sl = renderComp.layer(L2);
                if (sl.name === dname) {
                    sl.enabled = false;
                    found = true;
                    sceneDisabled++;
                    break;
                }
            }
            if (found) {
                log("  DISABLED: " + dname);
            } else {
                log("  WARN not found: " + dname);
            }
        }
    }

    // ---- Step 4: Set work area ----
    log("");
    log("--- Step 4: Set *RENDER ME work area ---");
    if (renderComp && mapping.render_work_area) {
        var waStart = mapping.render_work_area.start || 0;
        var waEnd = mapping.render_work_area.end || renderComp.duration;
        try {
            renderComp.workAreaStart = waStart;
            renderComp.workAreaDuration = Math.max(0.1, waEnd - waStart);
            log("  Work area: " + waStart.toFixed(2) + "s - " + waEnd.toFixed(2) + "s");
        } catch (eWA) {
            log("  WARN set work area failed: " + eWA.toString());
        }
    }

    app.endUndoGroup();

    // ---- Save As ----
    var saveAsRel = mapping.save_as || "Documental Political FullHD/filled_photos_v1.aep";
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
    var logFile = new File(scriptDir.fsName + "/6_fill_photos_log.txt");
    if (logFile.open("w")) {
        logFile.encoding = "UTF-8";
        logFile.write(logLines.join("\n"));
        logFile.close();
    }

    alert("Fill Photos complete!\n\n" +
          "Photos filled: " + photoOk + "/" + (photoOk + photoFail) + "\n" +
          "Captions updated: " + textOk + "/" + (textOk + textFail) + "\n" +
          "Scenes disabled: " + sceneDisabled + "\n\n" +
          "Saved as: " + saveAsRel + "\n\n" +
          "Next: double-click *RENDER ME and preview the first 17.56s\n" +
          "Then Composition -> Add to Render Queue");

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

    function findLayerByName(comp, name) {
        for (var i = 1; i <= comp.numLayers; i++) {
            if (comp.layer(i).name === name) return comp.layer(i);
        }
        return null;
    }

    function setTextContent(textLayer, newText) {
        var srcProp = textLayer.property("Source Text");
        var td = srcProp.value;
        td.text = newText;
        srcProp.setValue(td);
    }

    function scaleLayerToFitComp(layer, comp) {
        var src = layer.source;
        if (!src || !src.width || !src.height) return;

        var sx = (comp.width / src.width) * 100;
        var sy = (comp.height / src.height) * 100;
        var s = Math.max(sx, sy);  // cover-fit

        try {
            layer.property("Transform").property("Scale").setValue([s, s]);
            layer.property("Transform").property("Position").setValue([comp.width / 2, comp.height / 2]);
            layer.property("Transform").property("Anchor Point").setValue([src.width / 2, src.height / 2]);
        } catch (eS) {}
    }

})();
