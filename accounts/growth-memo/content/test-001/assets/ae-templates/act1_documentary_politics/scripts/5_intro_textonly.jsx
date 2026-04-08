// 5_intro_textonly.jsx
// Documentary Politics template - TEXT-ONLY intro renderer
//
// Strategy:
//   - We use Scene 1-5 only (disable Scene 6-17 in *RENDER ME)
//   - Inside each Scene 1-5, we disable all PlaceHolder_N layers
//     (no videos in intro - this template is text-first)
//   - We update TextHolder_1..5 with Mason's narrative text
//   - We set the *RENDER ME work area to 0.00-17.56s so
//     a render will only export the first 5 scenes
//
// Idempotent: safe to re-run.
//
// Usage:
//   1. Open "Documental Political FullHD (converted).aep" in AE
//   2. Ctrl+S once
//   3. File -> Scripts -> Run Script File... -> select this file

(function introTextOnly() {

    var scriptFile = File($.fileName);
    var scriptDir = scriptFile.parent;
    var mappingFile = new File(scriptDir.fsName + "/5_intro_text_mapping.json");

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
    log("=== Intro Text-Only Run ===");
    log("Started: " + new Date().toString());
    log("Mapping: " + mappingFile.fsName);
    log("");

    app.beginUndoGroup("Intro Text-Only");

    var textOk = 0, textFail = 0;
    var phDisabled = 0;
    var sceneDisabled = 0;

    // ---- Step 1: update TextHolder comps ----
    log("--- Step 1: Update TextHolders ---");
    if (mapping.text_holders) {
        for (var t = 0; t < mapping.text_holders.length; t++) {
            var th = mapping.text_holders[t];
            var thComp = compIndex[th.comp_name];
            if (!thComp) {
                log("  FAIL: " + th.comp_name + " not found");
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
                log("  OK " + th.comp_name + ": \"" + (th.text_1 || "") + "\" / \"" + (th.text_2 || "") + "\"");
                textOk++;
            } catch (eT) {
                log("  FAIL " + th.comp_name + ": " + eT.toString());
                textFail++;
            }
        }
    }

    // ---- Step 2: disable PlaceHolder layers inside each used Scene ----
    log("");
    log("--- Step 2: Disable PlaceHolders in Scene 1-5 ---");
    if (mapping.disable_placeholders_in_scenes) {
        for (var s = 0; s < mapping.disable_placeholders_in_scenes.length; s++) {
            var sceneName = mapping.disable_placeholders_in_scenes[s];
            var sceneComp = compIndex[sceneName];
            if (!sceneComp) {
                log("  WARN: " + sceneName + " not found");
                continue;
            }
            var disabledCount = 0;
            for (var L = 1; L <= sceneComp.numLayers; L++) {
                var lyr = sceneComp.layer(L);
                // Match layer name starting with "PlaceHolder_"
                if (lyr.name && lyr.name.indexOf("PlaceHolder_") === 0) {
                    lyr.enabled = false;
                    disabledCount++;
                }
            }
            log("  " + sceneName + ": disabled " + disabledCount + " PlaceHolder layer(s)");
            phDisabled += disabledCount;
        }
    }

    // ---- Step 3: disable unused scenes in *RENDER ME ----
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

    // ---- Step 4: set work area on *RENDER ME so export covers only the intro ----
    log("");
    log("--- Step 4: Set *RENDER ME work area ---");
    if (renderComp && mapping.render_work_area) {
        var waStart = mapping.render_work_area.start || 0;
        var waEnd = mapping.render_work_area.end || renderComp.duration;
        try {
            renderComp.workAreaStart = waStart;
            renderComp.workAreaDuration = Math.max(0.1, waEnd - waStart);
            log("  Work area: " + waStart.toFixed(2) + "s - " + waEnd.toFixed(2) + "s (duration " + renderComp.workAreaDuration.toFixed(2) + "s)");
        } catch (eWA) {
            log("  WARN set work area failed: " + eWA.toString());
        }
    }

    app.endUndoGroup();

    // ---- Save As ----
    var saveAsRel = mapping.save_as || "Documental Political FullHD/intro_textonly_v1.aep";
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
    var logFile = new File(scriptDir.fsName + "/5_intro_log.txt");
    if (logFile.open("w")) {
        logFile.encoding = "UTF-8";
        logFile.write(logLines.join("\n"));
        logFile.close();
    }

    alert("Intro text-only build complete!\n\n" +
          "TextHolders updated: " + textOk + "/" + (textOk + textFail) + "\n" +
          "PlaceHolder layers disabled: " + phDisabled + "\n" +
          "Scenes disabled in *RENDER ME: " + sceneDisabled + "\n\n" +
          "Saved as: " + saveAsRel + "\n\n" +
          "Next steps:\n" +
          "1. Double-click *RENDER ME to preview (check Chinese font!)\n" +
          "2. If font looks wrong, open TextHolder_N, change font manually\n" +
          "3. Composition -> Add to Render Queue -> export intro_v1.mp4");

    // ---- Helpers ----

    function parseJSON(s) {
        if (typeof JSON !== "undefined" && JSON.parse) {
            return JSON.parse(s);
        }
        if (s.charCodeAt(0) === 0xFEFF) s = s.substring(1);
        return eval("(" + s + ")");
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

})();
