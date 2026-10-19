%RUN_MATLAB_FIGURES Generate all Milestone 3 figures from saved final results.
% Open this file in base MATLAB R2020b or newer and click Run.
% No Python installation or MATLAB toolboxes are needed for this step.

project_root = fileparts(mfilename('fullpath'));
addpath(fullfile(project_root,'matlab'));
study_names = {'main','sensitivity','challenging'};

% Check all inputs before creating output folders.
for study_index = 1:numel(study_names)
    check_plot_inputs(fullfile(project_root,'results','final_v1', ...
        study_names{study_index}));
end

% Use a fresh directory on each invocation so earlier figures are preserved.
figure_base = fullfile(project_root,'figures',datestr(now,'yyyymmdd_HHMMSS'));
figure_root = figure_base;
run_number = 1;
while isfolder(figure_root) || isfile(figure_root)
    figure_root = sprintf('%s_%d',figure_base,run_number);
    run_number = run_number + 1;
end
mkdir(figure_root);

for study_index = 1:numel(study_names)
    study_name = study_names{study_index};
    fprintf('Generating %s figures...\n',study_name);
    plot_milestone3(fullfile(project_root,'results','final_v1',study_name), ...
        fullfile(figure_root,study_name));
end

fprintf('\nAll figures saved as PNG and PDF in:\n%s\n',figure_root);
fprintf('Inspect initial/best placements, labels, axes and convergence before submission.\n');
