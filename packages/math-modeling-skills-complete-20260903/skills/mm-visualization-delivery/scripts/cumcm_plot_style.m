function style = cumcm_plot_style(profile)
%CUMCM_PLOT_STYLE Original local CUMCM style definitions for MATLAB figures.
% No source code, image, or data from the user's reference corpus is copied.

if nargin < 1 || strlength(string(profile)) == 0
    profile = "cumcm-vivid";
end
profile = string(profile);

style = struct();
style.profile = profile;
style.fontName = "Microsoft YaHei";
style.fontSize = 9;
style.axisLineWidth = 0.8;
style.dataLineWidth = 1.35;
style.markerSize = 5.5;
style.gridColor = [0.85 0.88 0.90];
style.axisColor = [0.22 0.26 0.29];
style.figureCm = [16.0 9.5];

switch profile
    case "cumcm-highlight"
        style.palette = [170 180 189; 60 141 107; 217 130 43; 47 93 124; 138 111 176] / 255;
    case "cumcm-data-dense"
        style.palette = [36 75 107; 79 134 166; 125 183 197; 145 168 138; 192 163 90] / 255;
    case "cumcm-vivid"
        style.palette = [42 157 143; 231 111 81; 233 196 106; 69 123 157; 155 93 229; 241 91 181] / 255;
    otherwise
        style.palette = [47 93 124; 217 130 43; 76 149 108; 138 111 176; 198 93 87; 95 107 115] / 255;
end
end
