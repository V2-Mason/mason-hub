// diagnose_filled_layers.jsx
// Quality diagnostic for [FILLED] layers
//
// Purpose: For every Media XX comp, find the [FILLED] xxx.mp4 layer added
//          by 3_fill_template.jsx and report:
//            - source file
//            - source true resolution (width x height)
//            - comp size
//            - current Scale value (X, Y)
//            - effective display ratio (scale * source / comp)
//            - layer quality setting
//            - enabled state
//          The output is a single text file you can paste back to Claude.
//
// Usage:
//   1. Open the FILLED .aep ("Multiscreen Intro filled v1.aep")
//   2. File -> Scripts -> Run Script File... -> select this file
//   3. Find diagnose_output.txt next to the .aep
//
// Output format: one row per filled layer, sorted by "Display %" descending
//                so the biggest blur risks float to the top.

(function diagnose() {

    if (!app.project || !app.project.file) {
        alert("Please open the filled .aep first.");
        return;
    }

    var projectDir = app.project.file.parent;
    var outputFile = new File(projectDir.fsName + "/diagnose_output.txt");

    var lines = [];
    function out(s) { lines.push(s); }

    out("=== Filled Layer Diagnostic Report ===");
    out("Generated: " + new Date().toString());
    out("Project: " + app.project.file.fsName);
    out("");

    // Collect all Media XX comps and their [FILLED] layers
    var rows = [];

    for (var i = 1; i <= app.project.numItems; i++) {
        var item = app.project.item(i);
        if (!(item instanceof CompItem)) continue;
        if (item.name.indexOf("Media ") !== 0) continue;
        // Skip "Media XX Precomp" - we want the inner "Media XX" only
        if (item.name.indexOf("Precomp") >= 0) continue;

        for (var L = 1; L <= item.numLayers; L++) {
            var layer = item.layer(L);
            if (layer.name.indexOf("[FILLED]") !== 0) continue;
            if (!(layer instanceof AVLayer)) continue;

            var src = layer.source;
            if (!src) continue;

            var srcW = src.width || 0;
            var srcH = src.height || 0;
            var compW = item.width;
            var compH = item.height;

            // Read scale safely
            var scaleX = 100, scaleY = 100;
            try {
                var scaleProp = layer.property("Transform").property("Scale").value;
                scaleX = scaleProp[0];
                scaleY = scaleProp[1];
            } catch (eS) {}

            // Effective displayed pixels = source * (scale/100)
            // Display ratio = displayed / comp (how much of comp it fills)
            // For "blur judgement" we want: displayed pixels per comp pixel
            // displayPct = (scale/100) * (source / comp)
            // - 100% = 1:1, sharpest possible
            // - >100% = upscaled = blurry
            // - <100% = downscaled = sharp but wasted resolution
            var displayPctX = (scaleX / 100) * (srcW / compW) * 100;
            var displayPctY = (scaleY / 100) * (srcH / compH) * 100;
            var displayPct = Math.min(displayPctX, displayPctY);

            // Effective rendered pixels (the smaller dimension matters most)
            var effW = srcW * (scaleX / 100);
            var effH = srcH * (scaleY / 100);

            // Quality (Best/Draft/Wireframe)
            var quality = "?";
            try {
                if (layer.quality === LayerQuality.BEST) quality = "Best";
                else if (layer.quality === LayerQuality.DRAFT) quality = "Draft";
                else if (layer.quality === LayerQuality.WIREFRAME) quality = "Wireframe";
            } catch (eQ) {}

            // Source filename
            var srcName = src.name;
            var srcFile = "";
            try { if (src.file) srcFile = src.file.name; } catch (eF) {}

            rows.push({
                comp: item.name,
                layer: layer.name,
                srcName: srcName,
                srcFile: srcFile,
                srcW: srcW,
                srcH: srcH,
                compW: compW,
                compH: compH,
                scaleX: scaleX,
                scaleY: scaleY,
                effW: Math.round(effW),
                effH: Math.round(effH),
                displayPct: displayPct,
                quality: quality,
                enabled: layer.enabled
            });
        }
    }

    if (rows.length === 0) {
        out("(no [FILLED] layers found - did you run 3_fill_template.jsx first?)");
    } else {
        // Sort by display% ascending so worst (smallest = most upscaled) on top
        // Wait - actually we want most upscaled on top.
        // Display% < 100 means source is bigger than comp, downscaled = SHARP
        // Display% > 100 means source pixels stretched to fill comp = BLURRY? No.
        //
        // Re-think: scale=100, src=1920x1080, comp=1920x1080
        //   displayPct = 1.0 * 1.0 * 100 = 100 -> 1:1 perfect
        // scale=200, src=1920x1080, comp=1920x1080
        //   displayPct = 2.0 * 1.0 * 100 = 200 -> source pixels stretched 2x = BLURRY
        //   effW = 3840 (we draw 3840 pixels worth into a 1920 frame)
        // scale=100, src=960x540, comp=1920x1080
        //   displayPct = 1.0 * 0.5 * 100 = 50 -> source covers half the comp = small
        //
        // OK so for "fit to comp" semantics, what matters is:
        //   "for every pixel of the COMP, how many SOURCE pixels are available?"
        //   ratio = (source * scale/100) / comp
        //   < 1.0 -> upscaled, blurry
        //   = 1.0 -> 1:1
        //   > 1.0 -> downscaled, sharp
        //
        // displayPct above = effW/compW * 100 which is exactly this ratio * 100.
        // So:
        //   displayPct < 100 = upscaled = BLUR RISK
        //   displayPct >= 100 = sharp
        //
        // Sort so blur risks (smallest displayPct) appear at the TOP.
        rows.sort(function(a, b) { return a.displayPct - b.displayPct; });

        out("Total filled layers: " + rows.length);
        out("");
        out("Legend:");
        out("  Display% = (source * scale) / comp");
        out("    < 100 = source upscaled to fit comp = BLUR RISK");
        out("    = 100 = 1:1 pixel match = sharpest possible");
        out("    > 100 = source downscaled = sharp, full quality used");
        out("");
        out("Sorted by Display% ascending (worst first)");
        out("");

        // Header
        out(padRight("Comp", 12) + " | " +
            padRight("Source File", 42) + " | " +
            padRight("SrcRes", 11) + " | " +
            padRight("CompRes", 11) + " | " +
            padRight("Scale", 12) + " | " +
            padRight("Effective", 11) + " | " +
            padRight("Disp%", 7) + " | " +
            padRight("Q", 5) + " | " +
            "On");
        out(repeat("-", 130));

        for (var r = 0; r < rows.length; r++) {
            var row = rows[r];
            out(padRight(row.comp, 12) + " | " +
                padRight(row.srcFile || row.srcName, 42) + " | " +
                padRight(row.srcW + "x" + row.srcH, 11) + " | " +
                padRight(row.compW + "x" + row.compH, 11) + " | " +
                padRight(row.scaleX.toFixed(1) + "," + row.scaleY.toFixed(1), 12) + " | " +
                padRight(row.effW + "x" + row.effH, 11) + " | " +
                padRight(row.displayPct.toFixed(1), 7) + " | " +
                padRight(row.quality, 5) + " | " +
                (row.enabled ? "Y" : "N"));
        }

        out("");
        out("=== Summary ===");
        var blurRisk = 0, ok = 0, oversized = 0;
        for (var s = 0; s < rows.length; s++) {
            var d = rows[s].displayPct;
            if (d < 90) blurRisk++;
            else if (d < 110) ok++;
            else oversized++;
        }
        out("Blur risk (Display% < 90):    " + blurRisk + " layers");
        out("OK (90 <= Display% < 110):    " + ok + " layers");
        out("Downscaled (Display% >= 110): " + oversized + " layers");
    }

    // Write file
    if (outputFile.open("w")) {
        outputFile.encoding = "UTF-8";
        outputFile.lineFeed = "Unix";
        outputFile.write(lines.join("\n"));
        outputFile.close();
    }

    alert("Diagnostic complete!\n\n" +
          "Layers found: " + rows.length + "\n" +
          "Output: " + outputFile.fsName + "\n\n" +
          "Send the txt content back to Claude.");

    function padRight(s, w) {
        s = String(s);
        while (s.length < w) s = s + " ";
        if (s.length > w) s = s.substring(0, w);
        return s;
    }
    function repeat(s, n) {
        var out = "";
        for (var i = 0; i < n; i++) out += s;
        return out;
    }

})();
