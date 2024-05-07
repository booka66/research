function [SzEventsTimes, SE_list] = getSzEnvelop_wSE(Vdata,sampRate,toleranceLvl, t)
%Seizure Detection
%The tolerance level might need to be high if you have low noise
%(10^3-10^4, e.g. 5000); if there is high noise, you will want a lower
%value

traceVariance = transpose(rolling_variance(Vdata, sampRate));

if sampRate/2 > 150
    frequency_range = [1,150]; % Frequency range of interest in Hz
else
    frequency_range = [1,round(sampRate/2)]; % Frequency range of interest in Hz
end
window_size = round(sampRate/10); % Specify the rolling window size
rolling_power = calculatePower(Vdata, sampRate, frequency_range, window_size, 0);% Calculate rolling power for the specified frequency range
t2 = transpose(linspace(0,length(Vdata)/sampRate, length(rolling_power)));

%REFERENCE:
%-Choose reference section (1 min) (in first 10min)  with:
%	-no LFP activity
%	-no seizure-like activity
%	-no electrical noise spikes
%-Set the reference section as spectral activity baseline and voltage noise floor

% Set the window size to be for one minute (sampling rate*60sec)
window_size1 = round(sampRate*60);
Vfirst10 = round(sampRate*60*10);

% Specify the step size for the window
step_size = round(sampRate/2);

% Initialize
range = 1:step_size:(Vfirst10 - window_size1 + 1);
min_dev_values = zeros(1, numel(range));

% Calculate deviation in each window
for i = 1:numel(range)
    end_index = range(i) + window_size1 - 1;

    % Check if the end index exceeds the size of V
    if end_index > numel(Vdata)
        break;  % Exit the loop if the index is out of bounds
    end

    window_data = Vdata(range(i):end_index);
    deviation = abs(window_data - mean(window_data));
    min_dev_values(i) = sum(deviation);
end

% Find the minimum value and its index
[min_value, min_index] = min(min_dev_values);

% Store the reference section location
referenceIdxs = [range(min_index), (range(min_index) + window_size1 - 1)];


%Store the reference section as a unique list
VRef = Vdata(referenceIdxs(1):referenceIdxs(2));
tRef = t(referenceIdxs(1):referenceIdxs(2));
power_ref = calculatePower(VRef, sampRate, frequency_range, window_size, 0);
varianceRef = transpose(rolling_variance(VRef, sampRate));

%combine Variance and Power coherence

fitVar = fitListSize(traceVariance, rolling_power);

variThresh = mean(varianceRef)+toleranceLvl*std(varianceRef);
powThresh = mean(power_ref)+toleranceLvl*std(power_ref);
oneSec = find(t2>1,1);
Sz_window_size = oneSec*2;

szList = rollingWindowThreshold(fitVar, rolling_power, Sz_window_size, variThresh, powThresh);

%Cut out any seizures less than 10sec
szTimeMin = 10; %in sec
szListClean = szLenLim(szList,oneSec*szTimeMin);


%fitAC = fitListSize(Vdata, szListClean);

% %plot detection
% figure;
% plot(t2,fitAC,'k')
% hold on
% plot(t2(szListClean),.8*fitAC(szListClean), 'm')

%extract the event details for the seizure list
SzEventsIdxs = getSzEvents(szListClean);
SzEventTimes = t2(SzEventsIdxs);
% Initialize the merged events matrix
merged_events = [];
threshold_seconds = 60;


%Check if any Szs detected
if isempty(SzEventTimes)
    SzEventsTimes = 0;
    SE_list = 0;
else
    if size(SzEventTimes,2) == 1
        SzEventsTimes = SzEventTimes;
    end
    if size(SzEventTimes,2) > 1
        %Exception for a size of 1 event
        % Iterate over rows of the events matrix
        current_event = SzEventTimes(1, :);
        for i = 2:size(SzEventTimes, 1)
            % Check if the end time of the previous event is within the threshold
            if SzEventTimes(i, 1) - current_event(2) <= threshold_seconds
                % Merge the current event with the previous one
                current_event(2) = SzEventTimes(i, 2);
            else
                % Add the merged event to the merged events matrix
                merged_events = [merged_events; current_event];
                % Set the current event to the next event
                current_event = SzEventTimes(i, :);
            end
        end
        SzEventsTimes = [merged_events; current_event];
    end
    
    
        % Initialize an empty list to store the filtered rows
        SE_list = [];
        
        % Iterate over each row in the time_list
        if size(SzEventTimes, 2) < 2
            if (SzEventTimes(2)- SzEventTimes(1)) > 5*60
                SE_list = SzEventTimes;
            end
        else
            for i = 1:size(SzEventsTimes, 1)
                start_time = SzEventsTimes(i, 1);
                end_time = SzEventsTimes(i, 2);
                
                % Check if the time interval is greater than the threshold
                if (end_time-start_time) > 5*60
                    % If the time interval is greater than 5 minutes, add the row to the filtered_list
                    SE_list = [SE_list; SzEventsTimes(i, :)];
                end
            end
        end
        
        %Within SE, combine discharges within 6 min
        if size(SzEventTimes,2)>1
            for i = 2:size(SzEventsTimes, 1)
                for j = 1:size(SE_list,1)
                    if SzEventsTimes(i, 1) > SE_list(j, 2)
                        if (SzEventsTimes(i, 1) - SE_list(j,2)) < 6*60
                            SE_list(j,2) = SzEventsTimes(i,2);
                        end
                    end
                end
            end
            
            if size(SE_list, 1) >1
                for i = 1:size(SE_list, 1)-1
                    if SE_list(i,2) >= SE_list(i,2)
                        SE_list(i+1,:) = SE_list(i,:);
                    end
                end
            end
        
            %Remove Duplicates
            [~, unique_indices, ~] = unique(SE_list, 'rows');
            SE_list = SE_list(unique_indices, :);
        end
end
   
end