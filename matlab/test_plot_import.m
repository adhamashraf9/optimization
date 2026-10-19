function test_plot_import(study_dir)
%TEST_PLOT_IMPORT Regression for reserved CSV header "case" and spaced paths.
% Unexecuted until MATLAB is available. Example:
% addpath('matlab'); test_plot_import('results/demo');
    [runs, summary] = check_plot_inputs(study_dir);
    assert(ismember('case',runs.Properties.VariableNames));
    assert(ismember('case',summary.Properties.VariableNames));
    assert(height(runs)>0 && height(summary)>0);
    % A small copied demo is sufficient. Keep the copy for inspection rather
    % than deleting user data. tempname supplies a unique parent directory.
    test_root = tempname;
    mkdir(test_root);
    spaced_dir = fullfile(test_root,'study with spaces');
    [ok,message] = copyfile(study_dir,spaced_dir);
    assert(ok,'%s',message);
    [spaced_runs,spaced_summary] = check_plot_inputs(spaced_dir);
    assert(isequaln(runs,spaced_runs));
    assert(isequaln(summary,spaced_summary));
    fprintf('Import/header/spaced-path checks passed in MATLAB %s. Copy: %s\n',version,spaced_dir);
end
