function report = matlab_plot_from_spec(specPath, outputDirectory)
%MATLAB_PLOT_FROM_SPEC Render traceable CUMCM figures from CSV and JSON.
% The renderer never creates random data, fits models, computes correlations,
% removes points, or changes axis limits to amplify a result.

arguments
    specPath (1,1) string
    outputDirectory (1,1) string
end

specPath = string(java.io.File(char(specPath)).getCanonicalPath());
if ~isfile(specPath), error("Spec file does not exist: %s", specPath); end
spec = jsondecode(fileread(specPath));
if isfield(spec, "title") && strlength(string(spec.title)) > 0
    error("Paper figures must use the LaTeX caption rather than an internal title.");
end

sourcePath = string(spec.source_csv);
if ~isfile(sourcePath)
    sourcePath = fullfile(fileparts(specPath), sourcePath);
end
sourcePath = string(java.io.File(char(sourcePath)).getCanonicalPath());
if ~isfile(sourcePath), error("Source CSV does not exist: %s", sourcePath); end

if ~isfolder(outputDirectory), mkdir(outputDirectory); end
outputDirectory = string(java.io.File(char(outputDirectory)).getCanonicalPath());
T = readtable(sourcePath, "VariableNamingRule", "preserve");
chartType = lower(string(spec.chart_type));
xName = string(spec.x);
yNames = string(spec.y);
if isscalar(yNames), yNames = yNames(:); end
requireColumns(T, [xName; yNames(:)]);

profile = getField(spec, "style_profile", "cumcm-vivid");
allowedProfiles = ["cumcm-clean","cumcm-highlight","cumcm-data-dense","cumcm-vivid"];
if ~ismember(string(profile), allowedProfiles)
    error("Unknown style_profile: %s", string(profile));
end
style = cumcm_plot_style(profile);
reportedPalette = compose("#%02X%02X%02X", round(style.palette(:,1)*255), ...
    round(style.palette(:,2)*255), round(style.palette(:,3)*255));
labels = yNames;
if isfield(spec, "series_labels")
    labels = string(spec.series_labels);
    if numel(labels) ~= numel(yNames), error("series_labels must match y."); end
end

fig = figure("Visible", "off", "Color", "w", "Units", "centimeters", ...
    "Position", [2 2 style.figureCm]);
ax = axes(fig); hold(ax, "on");
colors = style.palette;
markers = {'o','s','^','d','v','p'};
lines = {'-','--','-.',':'};
x = T.(xName);

switch chartType
    case "line"
        for k = 1:numel(yNames)
            plot(ax, x, T.(yNames(k)), "Color", colors(wrap(k,size(colors,1)),:), ...
                "LineStyle", lines{wrap(k,numel(lines))}, "LineWidth", style.dataLineWidth, ...
                "Marker", markers{wrap(k,numel(markers))}, "MarkerSize", style.markerSize, ...
                "MarkerFaceColor", "w", "DisplayName", labels(k));
        end
    case "scatter"
        for k = 1:numel(yNames)
            scatter(ax, x, T.(yNames(k)), 34, colors(wrap(k,size(colors,1)),:), ...
                markers{wrap(k,numel(markers))}, "filled", "MarkerFaceAlpha", 0.78, ...
                "MarkerEdgeColor", "w", "DisplayName", labels(k));
        end
    case "errorbar"
        if ~isfield(spec, "yerr"), error("errorbar requires a precomputed yerr column."); end
        requiredUncertaintyFields = ["uncertainty_type","uncertainty_level","sample_size_source"];
        for fieldIndex = 1:numel(requiredUncertaintyFields)
            if ~isfield(spec, requiredUncertaintyFields(fieldIndex))
                error("errorbar requires %s.", requiredUncertaintyFields(fieldIndex));
            end
        end
        errName = string(spec.yerr); requireColumns(T, errName);
        for k = 1:numel(yNames)
            errorbar(ax, x, T.(yNames(k)), T.(errName), ...
                "Color", colors(wrap(k,size(colors,1)),:), "LineWidth", style.dataLineWidth, ...
                "Marker", markers{wrap(k,numel(markers))}, "MarkerSize", style.markerSize, ...
                "MarkerFaceColor", "w", "CapSize", 5, "DisplayName", labels(k));
        end
    case {"bar", "grouped_bar", "stacked_bar"}
        values = T{:, cellstr(yNames)};
        mode = "grouped"; if chartType == "stacked_bar", mode = "stacked"; end
        b = bar(ax, values, mode, "BarWidth", 0.72);
        for k = 1:numel(b)
            b(k).FaceColor = colors(wrap(k,size(colors,1)),:);
            b(k).EdgeColor = [0.22 0.26 0.29]; b(k).LineWidth = 0.45;
            b(k).DisplayName = labels(k);
        end
        xticks(ax, 1:height(T)); xticklabels(ax, string(x));
    case "horizontal_bar"
        b = barh(ax, T.(yNames(1)), 0.62, "FaceColor", colors(1,:), "EdgeColor", "none");
        b.DisplayName = labels(1); yticks(ax, 1:height(T)); yticklabels(ax, string(x));
        ax.YDir = "reverse";
    case {"dumbbell", "slope"}
        if numel(yNames) ~= 2, error("dumbbell requires exactly two y columns."); end
        old = T.(yNames(1)); current = T.(yNames(2)); rows = (1:height(T))';
        for r = 1:height(T)
            plot(ax, [old(r), current(r)], [r, r], "Color", [0.66 0.71 0.75], ...
                "LineWidth", 1.45, "HandleVisibility", "off");
        end
        scatter(ax, old, rows, 46, "o", "MarkerFaceColor", "w", ...
            "MarkerEdgeColor", colors(1,:), "LineWidth", 1.15, "DisplayName", labels(1));
        scatter(ax, current, rows, 46, "d", "MarkerFaceColor", colors(2,:), ...
            "MarkerEdgeColor", "w", "LineWidth", 0.6, "DisplayName", labels(2));
        yticks(ax, rows);
        if isfield(spec, "category_labels")
            cats = string(spec.category_labels);
        elseif isfield(spec, "category_prefix")
            cats = string(spec.category_prefix) + string(x);
        else
            cats = string(x);
        end
        yticklabels(ax, cats); ax.YDir = "reverse";
    case "box"
        values = T{:, cellstr(yNames)};
        for k = 1:numel(yNames)
            group = repmat(categorical(labels(k)), height(T), 1);
            boxchart(ax, group, values(:,k), "BoxFaceColor", colors(wrap(k,size(colors,1)),:), ...
                "BoxFaceAlpha", 0.65, "MarkerColor", [0.25 0.29 0.31]);
        end
    case "heatmap"
        if isfield(spec, "correlation")
            error("Correlation must be precomputed and validated before rendering.");
        end
        matrix = T{:, cellstr(yNames)};
        if any(~isfinite(matrix), "all")
            error("Heatmap values must all be finite.");
        end
        imagesc(ax, matrix); colorbar(ax);
        xticks(ax, 1:numel(yNames)); xticklabels(ax, labels);
        if isfield(spec, "row_labels"), yticklabels(ax, string(spec.row_labels)); end
        if isfield(spec, "matrix_semantics") && string(spec.matrix_semantics) == "correlation"
            if ~isfield(spec,"vmin") || ~isfield(spec,"vmax") || spec.vmin ~= -1 || spec.vmax ~= 1
                error("Correlation heatmaps require vmin=-1 and vmax=1.");
            end
            if any(abs(matrix) > 1 + 1e-12, "all")
                error("Correlation heatmap values must be within [-1, 1].");
            end
            clim(ax, [-1 1]); colormap(ax, correlationMap(256));
            reportedPalette = "correlation-blue-white-coral";
        else
            colormap(ax, parula(256));
            reportedPalette = "parula";
            if isfield(spec,"vmin") && isfield(spec,"vmax"), clim(ax,[spec.vmin spec.vmax]); end
        end
    case "area"
        values = T{:, cellstr(yNames)};
        a = area(ax, x, values, "LineWidth", 0.7);
        for k = 1:numel(a)
            a(k).FaceColor = colors(wrap(k,size(colors,1)),:); a(k).FaceAlpha = 0.55;
            a(k).DisplayName = labels(k);
        end
    otherwise
        error("Unsupported chart_type: %s", chartType);
end

xlabel(ax, string(getField(spec, "xlabel", xName)));
ylabel(ax, string(getField(spec, "ylabel", "")));
set(ax, "FontName", style.fontName, "FontSize", style.fontSize, ...
    "LineWidth", style.axisLineWidth, "Box", "off", "TickDir", "out", ...
    "XColor", style.axisColor, "YColor", style.axisColor, "Layer", "top");
grid(ax, "on"); ax.GridColor = style.gridColor; ax.GridAlpha = 0.55; ax.MinorGridAlpha = 0.25;

if numel(yNames) > 1 && chartType ~= "heatmap"
    lgd = legend(ax, "Location", "northoutside", "Orientation", "horizontal");
    lgd.Box = "off"; lgd.FontName = style.fontName; lgd.FontSize = style.fontSize;
end

stem = string(getField(spec, "figure_id", erase(string(java.io.File(char(specPath)).getName()), ".json")));
figPath = fullfile(outputDirectory, stem + ".fig");
pdfPath = fullfile(outputDirectory, stem + ".pdf");
pngPath = fullfile(outputDirectory, stem + ".png");
savefig(fig, figPath);
set(fig, "PaperUnits", "centimeters", "PaperSize", style.figureCm, ...
    "PaperPosition", [0 0 style.figureCm], "PaperPositionMode", "manual");
print(fig, pdfPath, "-dpdf", "-vector");
exportgraphics(fig, pngPath, "Resolution", 300, "BackgroundColor", "white");
close(fig);
reopened = openfig(figPath, "invisible"); close(reopened);

report = struct();
report.renderer = "matlab_plot_from_spec";
report.semantic_claim_validation = false;
report.status = "RUNTIME_VERIFIED";
report.matlab_version = string(version);
report.style_profile = string(profile);
report.effective_palette = reportedPalette;
report.font_family = string(style.fontName);
report.base_font_pt = style.fontSize;
report.effective_min_font_pt = max(7, style.fontSize - 1);
report.final_width_mm = style.figureCm(1) * 10;
switch chartType
    case {"line","errorbar"}
        report.line_width_pt = style.dataLineWidth;
    case "scatter"
        report.line_width_pt = 0.35;
    case {"bar","grouped_bar","stacked_bar"}
        report.line_width_pt = 0.45;
    case "horizontal_bar"
        report.line_width_pt = style.axisLineWidth;
    case {"dumbbell","slope"}
        report.line_width_pt = 1.45;
    case "box"
        report.line_width_pt = style.axisLineWidth;
    case "area"
        report.line_width_pt = 0.7;
    otherwise
        report.line_width_pt = style.axisLineWidth;
end
if ismember(chartType, ["scatter","box","area"])
    report.decorative_effects = {"transparent_fill"};
else
    report.decorative_effects = {"none"};
end
if numel(yNames) > 1 && chartType ~= "heatmap"
    report.legend_strategy = "top";
else
    report.legend_strategy = "none";
end
seriesColorMapping = repmat(struct("series","","color",""), 0, 1);
if chartType ~= "heatmap"
    seriesColorMapping = repmat(struct("series","","color",""), numel(labels), 1);
    for k = 1:numel(labels)
        seriesColorMapping(k).series = labels(k);
        seriesColorMapping(k).color = report.effective_palette(wrap(k,numel(report.effective_palette)));
    end
end
report.series_color_mapping = seriesColorMapping;
report.source = struct("path",leafName(sourcePath),"sha256",sha256File(sourcePath),"rows",height(T));
report.spec = struct("path",leafName(specPath),"sha256",sha256File(specPath));
report.render_contract = struct( ...
    "chart_type", chartType, ...
    "variables", [xName; yNames(:)], ...
    "transformations", string(getField(spec,"transformations","none")), ...
    "source_sha256", sha256File(sourcePath), ...
    "spec_sha256", sha256File(specPath));
report.outputs = [fileRecord(figPath), fileRecord(pdfPath), fileRecord(pngPath)];
report.reopen_check = struct("fig",true,"pdf",startsWith(readPrefix(pdfPath,4),"%PDF"),"png",isfile(pngPath));
report.warning = "RUNTIME_VERIFIED is not EVIDENCE_ELIGIBLE; run numeric, claim, and visual audits.";
manifestPath = fullfile(outputDirectory, stem + ".matlab-report.json");
fid = fopen(manifestPath, "w", "n", "UTF-8");
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, "%s\n", jsonencode(report, "PrettyPrint", true));
end

function value = getField(s, name, defaultValue)
if isfield(s, name), value = s.(name); else, value = defaultValue; end
end

function requireColumns(T, names)
available = string(T.Properties.VariableNames);
missing = names(~ismember(names, available));
if ~isempty(missing), error("Missing CSV columns: %s", strjoin(missing, ", ")); end
end

function index = wrap(value, count)
index = mod(value - 1, count) + 1;
end

function value = sha256File(path)
fid = fopen(path, "r"); if fid < 0, error("Cannot open for hashing: %s", path); end
cleanup = onCleanup(@() fclose(fid));
bytes = fread(fid, Inf, "*uint8");
md = javaMethod("getInstance", "java.security.MessageDigest", "SHA-256");
md.update(bytes);
value = lower(string(reshape(dec2hex(typecast(md.digest(),"uint8"),2).',1,[])));
end

function record = fileRecord(path)
info = dir(path);
record = struct("path",leafName(path),"sha256",sha256File(path),"bytes",info.bytes);
end

function name = leafName(path)
[~,stem,extension] = fileparts(path);
name = string(stem) + string(extension);
end

function value = readPrefix(path, count)
fid = fopen(path,"r"); cleanup = onCleanup(@() fclose(fid));
value = string(char(fread(fid,count,"*uint8")'));
end

function cmap = correlationMap(n)
% Perceptually ordered blue-white-coral diverging map for signed matrices.
if nargin < 1
    n = 256;
end
blue = [38 98 145] / 255;
white = [247 247 247] / 255;
coral = [213 75 63] / 255;
leftCount = ceil(n/2);
rightCount = n - leftCount + 1;
left = [linspace(blue(1),white(1),leftCount)', ...
        linspace(blue(2),white(2),leftCount)', ...
        linspace(blue(3),white(3),leftCount)'];
right = [linspace(white(1),coral(1),rightCount)', ...
         linspace(white(2),coral(2),rightCount)', ...
         linspace(white(3),coral(3),rightCount)'];
cmap = [left; right(2:end,:)];
end
