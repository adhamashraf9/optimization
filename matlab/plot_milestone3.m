function plot_milestone3(study_dir, output_dir)
%PLOT_MILESTONE3 Plot saved Python results, using base MATLAB only.
% Example from repo root:
% addpath('matlab'); plot_milestone3('results/comparison','results/figures');
% Statistics, fitness, graph edges and coverage flags are read, not recomputed.
% Requires MATLAB R2020b+. Actual execution must be separately verified.
    [runs, summary] = check_plot_inputs(study_dir);
    assert(~isfolder(output_dir), 'Choose a new output directory to preserve earlier figures.');
    mkdir(output_dir);
    cases = unique(runs.('case'),'stable');
    for c = 1:numel(cases)
        mask = runs.('case') == cases(c) & runs.status == "completed";
        preferred = mask & (runs.method == "sa_feasible" | runs.method == "baseline");
        if any(preferred), mask = preferred; end
        indices = find(mask);
        if isempty(indices), continue; end
        % Selecting a representative best run is explicitly labelled; group
        % statistics below include all seeds and are computed by Python.
        [~, local] = max(runs.fitness(indices));
        row = indices(local);
        root = fullfile(study_dir,char(runs.run_directory(row)));
        data = jsondecode(fileread(fullfile(root,'case.json')));
        problem = data.problem;
        label = sprintf('%s | %s | best run seed %d',cases(c),runs.method(row),runs.seed(row));
        for state = {'initial','best'}
            if strcmp(state{1},'initial'), prefix = 'initial_'; else, prefix = ''; end
            pos = readtable(fullfile(root,[prefix 'positions.csv']));
            targets = readtable(fullfile(root,[prefix 'targets.csv']));
            edges = readtable(fullfile(root,[prefix 'edges.csv']));
            f = figure('Visible','off','Position',[100 100 1000 500],'Color','w');
            subplot(1,2,1); hold on;
            for j = 1:height(edges)
                plot([edges.x1(j) edges.x2(j)],[edges.y1(j) edges.y2(j)], ...
                    '-','Color',[.65 .65 .65],'HandleVisibility','off');
            end
            angles = linspace(0,2*pi,181);
            for j = 1:height(pos)
                plot(pos.x(j)+pos.radius(j)*cos(angles),pos.y(j)+pos.radius(j)*sin(angles), ...
                    ':','Color',[.2 .4 .8],'HandleVisibility','off');
            end
            sizes = 25 + 70*targets.weight/max([targets.weight;1]);
            hit = targets.covered == 1;
            scatter(targets.x(~hit),targets.y(~hit),sizes(~hit),[.65 .65 .65],'filled','DisplayName','Uncovered targets');
            scatter(targets.x(hit),targets.y(hit),sizes(hit),[.1 .6 .25],'filled','DisplayName','Covered targets');
            % Quantitative priority key, using the same area mapping as targets.
            if ~isempty(targets.weight)
                for weight = unique([min(targets.weight),median(targets.weight),max(targets.weight)])
                    scatter(NaN,NaN,25+70*weight/max([targets.weight;1]),[.4 .4 .4], ...
                        'filled','DisplayName',sprintf('Priority %.2f',weight));
                end
            end
            scatter(pos.x,pos.y,60,[.1 .3 .9],'^','filled','DisplayName','UAV');
            for j = 1:height(pos)
                text(pos.x(j),pos.y(j),sprintf('  U%d: %.1f m',pos.id(j),pos.z(j)), ...
                    'FontSize',7,'Color',[.1 .2 .6]);
            end
            scatter(problem.gcs(1),problem.gcs(2),100,'r','s','filled','DisplayName','GCS');
            axis equal; xlim(problem.bounds(1,:)); ylim(problem.bounds(2,:)); grid on;
            xlabel('x (m)'); ylabel('y (m)'); title([state{1} ' footprint; size = priority']);
            legend('Location','best');
            subplot(1,2,2); hold on;
            for j = 1:height(edges)
                plot3([edges.x1(j) edges.x2(j)],[edges.y1(j) edges.y2(j)], ...
                    [edges.z1(j) edges.z2(j)],'-','Color',[.65 .65 .65],'HandleVisibility','off');
            end
            scatter3(pos.x,pos.y,pos.z,60,'b','^','filled','DisplayName','UAV');
            for j = 1:height(pos)
                text(pos.x(j),pos.y(j),pos.z(j),sprintf('  %.1f m',pos.z(j)),'FontSize',7);
            end
            scatter3(problem.gcs(1),problem.gcs(2),problem.gcs(3),100,'r','s','filled','DisplayName','GCS');
            xlabel('x (m)'); ylabel('y (m)'); zlabel('Altitude (m)'); grid on; view(35,25);
            xlim(problem.bounds(1,:)); ylim(problem.bounds(2,:)); zlim([0 max(problem.bounds(3,2),problem.gcs(3))+10]);
            title(label,'Interpreter','none'); legend('Location','best');
            save_figure(f,output_dir,sprintf('%s_%s_placement',cases(c),state{1}));
        end
        trace = readtable(fullfile(root,'trace.csv'));
        f = figure('Visible','off','Position',[100 100 900 650],'Color','w');
        subplot(2,1,1);
        plot(trace.evaluation,trace.current_fitness,'Color',[.65 .65 .65]); hold on;
        plot(trace.evaluation,trace.best_fitness,'b','LineWidth',1.5);
        xlabel('Consumed fitness evaluations'); ylabel('Fitness'); grid on;
        legend('Current state','Best feasible','Location','best'); title(label,'Interpreter','none');
        subplot(2,1,2);
        semilogy(trace.evaluation,trace.temperature,'r');
        xlabel('Consumed fitness evaluations'); ylabel('Temperature (fitness units)'); grid on;
        title('Geometric cooling; blank during initialization/calibration');
        save_figure(f,output_dir,sprintf('%s_convergence_temperature',cases(c)));
    end
    % All-seed summaries use already computed means/sample standard deviations.
    for c = 1:numel(cases)
        rows = summary(summary.('case')==cases(c),:);
        if isempty(rows), continue; end
        f = figure('Visible','off','Position',[100 100 1150 800],'Color','w');
        subplot(2,2,1);
        errorbar(1:height(rows),rows.mean_fitness,rows.std_fitness,'o');
        ylabel('Fitness (mean +/- sample SD)'); decorate(rows.method);
        title(sprintf('%s: feasible-run quality',cases(c)),'Interpreter','none');
        subplot(2,2,2); bar(rows.mean_coverage_fraction);
        ylabel('Weighted coverage fraction'); ylim([0 1]); decorate(rows.method);
        subplot(2,2,3); bar(rows.mean_power_per_uav);
        ylabel('Power per UAV (W)'); decorate(rows.method);
        subplot(2,2,4); bar(rows.mean_runtime);
        ylabel('Mean solver runtime (s)'); decorate(rows.method);
        save_figure(f,output_dir,sprintf('%s_method_or_parameter_comparison',cases(c)));
    end
    f = figure('Visible','off','Position',[100 100 1000 500],'Color','w');
    methods = unique(summary.method,'stable');
    for j = 1:numel(methods)
        rows=summary(summary.method==methods(j),:);
        [~,order]=sort(rows.num_uavs); rows=rows(order,:);
        subplot(1,2,1); hold on;
        plot(rows.num_uavs,rows.mean_runtime,'o','DisplayName',char(methods(j)));
        subplot(1,2,2); hold on;
        plot(rows.num_uavs,rows.mean_coverage_fraction,'o','DisplayName',char(methods(j)));
    end
    subplot(1,2,1); xlabel('UAV count'); ylabel('Mean runtime (s)'); grid on;
    title('Different target counts/distributions also vary'); legend('Location','best','Interpreter','none');
    subplot(1,2,2); xlabel('UAV count'); ylabel('Weighted coverage fraction'); ylim([0 1]); grid on;
    title('Normalized coverage; not a controlled scaling law'); legend('Location','best','Interpreter','none');
    save_figure(f,output_dir,'problem_size_performance');
    fprintf('Figures generated in %s using MATLAB %s\n',output_dir,version);
end

function decorate(labels)
    grid on; xticks(1:numel(labels)); xticklabels(labels); xtickangle(40);
    set(gca,'TickLabelInterpreter','none');
end

function save_figure(f,directory,name)
    print(f,fullfile(directory,[name '.png']),'-dpng','-r160');
    set(f,'PaperPositionMode','auto');
    print(f,fullfile(directory,[name '.pdf']),'-dpdf','-bestfit');
    close(f);
end
