from typing import List, Annotated
import tempfile
from pathlib import Path
import json
from mimetypes import guess_type
import shutil

from fastapi import FastAPI, HTTPException, UploadFile, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.background import BackgroundTask

from toolbox_runner import __version__
from toolbox_runner.handler import ToolHandler, ToolRunner, ToolSniffer
from toolbox_runner.models import Tool, ToolJob, ToolResultFile
from toolbox_runner.docker_client import get_client


app = FastAPI(
    version=__version__,
    title="Async tool-specs enabled Container Runner",
    description="Asynchronous dispatching server for containerized tools implementing tool-specs interface.",
    root_path="/api/v1"
)

# add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# for now we will use a global handler
# we can later on create a ToolRunner per User witg hard-coded mount-paths and/or tool mapping
runner = ToolRunner()
handler = ToolHandler(runner=runner)

# for now we whitelist the tool container that may be called
WHITELIST = ['ghcr.io/vforwater/', 'ghcr.io/hydrocode-de/', 'ghcr.io/camels-de/', 'ghcr.io/kit-hyd/']


@app.get("/")
def index():
    return {
        'version': __version__
    }

@app.get("/tools")
def get_tools() -> List[str]:
    # get the current list of tools
    return list(handler.tool_map.keys())

@app.get("/tools/full")
def get_full_tool_list() -> List[Tool]:
    # container for the tools
    tools = []
    # get the current list of tools
    for tool_name in handler.tool_map.keys():
        # get the tool specification from the handler
        tool = handler.get_tool(tool_name)
        tools.append(tool)
    return tools

@app.get("/tool/{tool_name}")
def get_tool(tool_name: str) -> Tool:
    # get the tool specification
    tool =  handler.get_tool(tool_name)

    # raise a 404 if the tool is not found
    if tool is None:
        raise HTTPException(status_code=404, detail=f"Tool names '{tool_name}' was not found. Maybe you misspelled it? Make sure it is already registered.")

    return tool

@app.post("/tools/register")
def register_tools(docker_image: str):
    # check if the docker image is whitelisted
    if not any([docker_image.startswith(prefix) for prefix in WHITELIST]):
        raise HTTPException(status_code=403, detail=f"Image '{docker_image}' is not whitelisted for registration. Please contact the administrator. You may only use images from these namespaces: {WHITELIST}. If you are the administrator, you can change the WHITELIST variable")
    
    # check if the user defined a tag
    if ':' in docker_image:
        docker_image, tag = docker_image.split(':')
    else:
        tag = 'latest'

    # try to pull the requested images
    client = get_client()
    try:
        client.images.pull(docker_image, tag=tag)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not pull {docker_image}:{tag}. ERROR: {str(e)}")
    
    # create a tool sniffer to find tools
    try:
        sniffer = ToolSniffer(docker_image=docker_image)
        tools = sniffer.get_tools()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"The image {docker_image}:{tag} failed on registration. Does it follow the tool-specs: https://vforwater.github.io/tool-specs/ ? ERROR: {str(e)}")

    # register the tools
    responses = {}
    try:
        for tool in tools:
            handler.register_tool(tool_name=tool, docker_image=docker_image)
        responses[tool] = {'registered': True}
    except Exception as e:
        responses[tool] = {'registered': False, 'message': str(e)}
    
    return responses

@app.post("/tool/{tool_name}/create")
def create_job(
    tool_name: str, 
    files: list[UploadFile] = [], 
    parameters: Annotated[str, Form()] = '{}', 
    local_data: Annotated[str, Form()] = '{}',
    name_mapping: Annotated[str, Form()] = '{}'
) -> ToolJob:
    # parameter and local_data might be json encoded strings
    try:
        if isinstance(parameters, str):
            parameters = json.loads(parameters)
        if isinstance(local_data, str):
            local_data = json.loads(local_data)
        if isinstance(name_mapping, str):
            name_mapping = json.loads(name_mapping)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse the parameters or local_data. Make sure they are valid JSON. ERROR: {str(e)}")

    # add the uploaded files
    if files is not None:
        dir = tempfile.TemporaryDirectory()        
        for file in files:
            # write to a temporary directory
            p = Path(dir.name) / file.filename
            with open(p, 'wb') as f:
                f.write(file.file.read())
            local_data[name_mapping.get(p.stem, p.stem)] = str(p)
    else:
        dir = None
    
    # create a new job
    job = handler.create_job(tool_name, parameters=parameters, data=local_data)

    # delete the temporary directory
    if dir is not None:
        dir.cleanup()

    return job

@app.get("/jobs")
def get_jobs() -> List[ToolJob]:
    # get all jobs
    return handler.list_jobs(ids_only=False)

@app.get("/job/{job_id}")
def get_job(job_id: str) -> ToolJob:
    return handler.get_job(job_id=job_id)


@app.get("/job/{job_id}/results")
def get_job_results(job_id: str) -> List[ToolResultFile]:
    # get the job
    job = handler.get_job(job_id=job_id)
    
    # walk the output directory and return filenames, sizes and content types
    results = []
    for p in Path(job.out_dir).rglob('*'):
        results.append(ToolResultFile(
            path=str(p),
            filename= p.name,
            size=p.stat().st_size,
            is_dir=p.is_dir(),
            extension=p.suffix if not p.is_dir() else None,
            content_type=guess_type(p)[0] if not p.is_dir() else None
        ))
    return results

@app.get("/job/{job_id}/result/{file_name}")
def get_result_file(job_id: str, file_name: str):
    """
    Retrieve either a single file and send back, or, if the requested file
    end is 'results.zip', create a zip and send back.
    """
    # get the job
    job = handler.get_job(job_id=job_id)

    # check if all files are requested
    if file_name  == 'results.zip':
        # create a temporary file
        zip = tempfile.NamedTemporaryFile()
        
        # create the archive
        archive_name = shutil.make_archive(zip.name, 'zip', root_dir=job.out_dir, base_dir='.')
        return FileResponse(
            archive_name, 
            filename='results.zip',
            media_type='application/zip',
            content_disposition_type="attachment",
            background=BackgroundTask(shutil.rmtree, archive_name)
        )
        
    else:
        # get the file
        p = Path(job.out_dir) / file_name

        # raise a 404 if the file is not found
        if not p.exists():
            raise HTTPException(status_code=404, detail=f"File '{file_name}' not found in the output directory of job '{job_id}'")
        
        # guess the mime type
        mime = guess_type(p)[0]
        return FileResponse(p, media_type=mime if mime is not None else 'application/octet-stream')
    

@app.post("/job/{job_id}/run")
def run_job(job_id: str) -> ToolJob:
    job = handler.run_job(job_id=job_id)

    return job


if __name__ == '__main__':
    import uvicorn
    import os

    # get UVICORN settings
    HOST = os.getenv("UVICORN_HOST", "127.0.0.1")
    PORT = os.getenv("UVICORN_PORT", 8000)
    RELOAD = os.getenv("UVICORN_RELOAD", True)

    # run server
    uvicorn.run("server:app", host=HOST, port=int(PORT), reload=bool(RELOAD))
