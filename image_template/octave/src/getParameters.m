function params = getParameters()
    pkg load jsonlab
    % get the param file environement variable
    PARAM_FILE = getenv('PARAM_FILE');
    if isempty(PARAM_FILE)
        PARAM_FILE = '/in/tool.json';
    endif

    % read the file content as JSON
    raw_params = loadjson(fileread(PARAM_FILE));

    % read the tool name and its config
    TOOL = getenv('TOOL_RUN');
    if isempty(TOOL)
        TOOL = 'foobar';
    endif
    tool_params = getfield(raw_params, TOOL);

    % now it gets a bit funky:
    % The image contains yq to parse YAML. we can convert the tool.yml to JSON and read that one
    system('/src/yq -o json /src/tool.yml > /src/conf_tool.json')
    config = loadjson(fileread('/src/conf_tool.json'));

    % extract the params
    params_conf = getfield(config.tools, TOOL).parameters;

    % Finally. I really love octave/matlab. straightforward

    % get all fields defined in the PARAM file
    params_names = fieldnames(tool_params);

    % build an empty container for the final params
    params = struct;

    % loop through all parameters
    for par_idx = 1:length(params_names)
        % get the conf for this parameter
        paramconf = getfield(params_conf, params_names{par_idx});

        % get the value for this parameter
        paramval = getfield(tool_params, params_names{par_idx});

        % switch the different types
        if strcmp(paramconf.type, 'file')
            % this is really, really stupid...
            if strncmp(flip(paramval), flip('.mat'), 4)  % <- startsWith
                loaded_val = load(paramval);
            elseif strncmp(flip(paramval), flip('.csv'), 4)
                loaded_val = csvread(paramval);
            else
                loaded_val = paramval;
            endif
        else
            loaded_val = paramval;
        endif

        % finally add to the new struct
        params.(params_names{par_idx}) = loaded_val;
    end
endfunction