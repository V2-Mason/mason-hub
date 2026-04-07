// 1_inspect_template.jsx
// AE Template Inspector
//
// Purpose: Walk every composition and layer in the currently open project,
//          and write a readable structure dump to inspect_output.txt next to
//          the .aep file. The dump is the input for designing the panel->clip
//          mapping in step 2.
//
// Usage:
//   1. Open the .aep template in After Effects
//   2. Save it once (Ctrl+S) so app.project.file exists
//   3. File -> Scripts -> Run Script File... -> select this file
//   4. Find inspect_output.txt next to your .aep
//
// Notes:
//   - Pure ExtendScript ES3, no external dependencies
//   - Safe to re-run; overwrites the output file each time
//   - Errors on missing layers/sources are caught and labeled <error>

(function inspectTemplate() {

    // ---- Step 1: sanity check ----
    if (!app.project) {
        alert("No project is open. Please open the .aep template first.");
        return;
    }
    if (!app.project.file) {
        alert("Project has not been saved yet.\n\n" +
              "Please Save As the project into:\n" +
              "accounts/growth-memo/.../ae-templates/act1_news_multiscreen/\n" +
              "then run this script again.");
        return;
    }

    var projectFile = app.project.file;
    var projectDir = projectFile.parent;
    var outputFile = new File(projectDir.fsName + "/inspect_output.txt");

    if (!outputFile.open("w")) {
        alert("Failed to open output file for writing:\n" + outputFile.fsName);
        return;
    }
    outputFile.encoding = "UTF-8";
    outputFile.lineFeed = "Unix";

    // ---- Step 2: collect output lines in memory, write at the end ----
    var lines = [];
    function out(s) { lines.push(s); }

    out("=== AE Template Inspection Report ===");
    out("Generated: " + new Date().toString());
    out("Project file: " + projectFile.fsName);
    out("");

    // ---- Step 3: bucket project items by type ----
    var allComps = [];
    var allFootage = [];
    var allFolders = [];
    for (var i = 1; i <= app.project.numItems; i++) {
        var item = app.project.item(i);
        if (item instanceof CompItem) {
            allComps.push(item);
        } else if (item instanceof FootageItem) {
            allFootage.push(item);
        } else if (item instanceof FolderItem) {
            allFolders.push(item);
        }
    }

    out("=== Project Summary ===");
    out("Total items:    " + app.project.numItems);
    out("- Compositions: " + allComps.length);
    out("- Footage items:" + allFootage.length);
    out("- Folders:      " + allFolders.length);
    out("");

    // ---- Step 4: per-comp detail ----
    out("=== Compositions Detail ===");
    out("");

    for (var c = 0; c < allComps.length; c++) {
        var comp = allComps[c];

        out("--- Comp " + (c + 1) + ": \"" + comp.name + "\" ---");
        out("  Duration:   " + comp.duration.toFixed(2) + "s");
        out("  Frame rate: " + comp.frameRate + " fps");
        out("  Resolution: " + comp.width + "x" + comp.height);
        out("  Layers:     " + comp.numLayers);
        out("");

        for (var l = 1; l <= comp.numLayers; l++) {
            var layer = comp.layer(l);
            var line = "  [" + padLeft(l, 3) + "] \"" + layer.name + "\"";
            line += " | " + describeLayer(layer);
            line += " | in=" + layer.inPoint.toFixed(2) + "s out=" + layer.outPoint.toFixed(2) + "s";
            line += " enabled=" + layer.enabled;
            out(line);
        }
        out("");
    }

    // ---- Step 5: footage list (so we can see what placeholders/solids exist) ----
    out("=== Footage Items ===");
    if (allFootage.length === 0) {
        out("  (none)");
    } else {
        for (var f = 0; f < allFootage.length; f++) {
            out("  - " + describeFootage(allFootage[f]));
        }
    }
    out("");

    // ---- Step 6: write file + summary ----
    outputFile.write(lines.join("\n"));
    outputFile.close();

    alert("Inspection complete!\n\n" +
          "Output written to:\n" + outputFile.fsName + "\n\n" +
          "Compositions: " + allComps.length + "\n" +
          "Footage items: " + allFootage.length + "\n\n" +
          "Send the txt file content back to Claude.");

    // ---- Helpers ----

    function describeLayer(layer) {
        try {
            if (layer instanceof TextLayer) {
                var txt = "<error>";
                try {
                    txt = layer.property("Source Text").value.text;
                    if (txt.length > 60) txt = txt.substring(0, 57) + "...";
                    txt = txt.replace(/[\r\n]+/g, " ");
                } catch (e1) {}
                return "TextLayer text=\"" + txt + "\"";
            }
            if (typeof ShapeLayer !== "undefined" && layer instanceof ShapeLayer) {
                return "ShapeLayer";
            }
            if (typeof CameraLayer !== "undefined" && layer instanceof CameraLayer) {
                return "CameraLayer";
            }
            if (typeof LightLayer !== "undefined" && layer instanceof LightLayer) {
                return "LightLayer";
            }
            if (layer instanceof AVLayer) {
                if (!layer.source) return "AVLayer source=null";
                var src = layer.source;
                if (src instanceof CompItem) {
                    return "AVLayer source=PreComp \"" + src.name + "\"";
                }
                if (src instanceof FootageItem) {
                    return "AVLayer source=" + describeFootage(src);
                }
                return "AVLayer source=Unknown";
            }
            return "UnknownLayer";
        } catch (e) {
            return "<describe error: " + e.toString() + ">";
        }
    }

    function describeFootage(fitem) {
        var label = "\"" + fitem.name + "\" ";
        try {
            var ms = fitem.mainSource;
            if (typeof SolidSource !== "undefined" && ms instanceof SolidSource) {
                return label + "[Solid color=" + ms.color + "]";
            }
            if (typeof FileSource !== "undefined" && ms instanceof FileSource) {
                var fname = "(no file)";
                if (fitem.file) fname = fitem.file.name;
                return label + "[File=" + fname + "]";
            }
            if (typeof PlaceholderSource !== "undefined" && ms instanceof PlaceholderSource) {
                return label + "[Placeholder]";
            }
            return label + "[UnknownSource]";
        } catch (e) {
            return label + "[<describe error>]";
        }
    }

    function padLeft(num, width) {
        var s = String(num);
        while (s.length < width) s = " " + s;
        return s;
    }

})();
