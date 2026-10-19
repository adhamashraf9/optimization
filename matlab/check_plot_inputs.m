function [runs, summary] = check_plot_inputs(study_dir)
%CHECK_PLOT_INPUTS Validate Python exports without recomputing model results.
% Requires base MATLAB R2020b or newer; no toolboxes.
    required = {'manifest.json','runs.csv','summary.csv'};
    for k = 1:numel(required)
        assert(isfile(fullfile(study_dir, required{k})), ...
            'Missing study file: %s', required{k});
    end
    manifest = jsondecode(fileread(fullfile(study_dir,'manifest.json')));
    assert(manifest.complete, 'Study is incomplete; inspect Python execution first.');
    % "case" is a MATLAB keyword. Preserve CSV headers explicitly so the
    % dynamic table-variable access below does not depend on name sanitization.
    runs = readtable(fullfile(study_dir,'runs.csv'),'TextType','string','VariableNamingRule','preserve');
    summary = readtable(fullfile(study_dir,'summary.csv'),'TextType','string','VariableNamingRule','preserve');
    require_columns(runs, {'case','method','seed','status','run_directory','fitness'});
    require_columns(summary, {'case','method','num_uavs','num_targets', ...
        'mean_fitness','std_fitness','mean_coverage_fraction', ...
        'mean_power_per_uav','mean_runtime','successful_runs','attempted_runs'});
    for k = 1:height(runs)
        if runs.status(k) ~= "completed"
            fprintf('Skipping failed run: %s (%s)\n', runs.run_directory(k),runs.status(k));
            continue;
        end
        root = fullfile(study_dir,char(runs.run_directory(k)));
        files = {'case.json','config.json','result.json','trace.csv', ...
            'positions.csv','targets.csv','edges.csv', ...
            'initial_positions.csv','initial_targets.csv','initial_edges.csv'};
        for j = 1:numel(files)
            assert(isfile(fullfile(root,files{j})), 'Missing run file: %s',fullfile(root,files{j}));
        end
        pos = readtable(fullfile(root,'positions.csv'));
        targets = readtable(fullfile(root,'targets.csv'));
        edges = readtable(fullfile(root,'edges.csv'));
        trace = readtable(fullfile(root,'trace.csv'));
        require_columns(pos,{'id','x','y','z','radius'});
        require_columns(targets,{'id','x','y','weight','covered'});
        require_columns(edges,{'x1','y1','z1','x2','y2','z2'});
        require_columns(trace,{'evaluation','temperature','current_fitness','best_fitness'});
    end
end

function require_columns(t, names)
    assert(all(ismember(names,t.Properties.VariableNames)), ...
        'CSV columns do not match the documented Python export schema.');
end
