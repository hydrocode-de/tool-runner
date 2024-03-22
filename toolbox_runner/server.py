from fastapi import FastAPI

from toolbox_runner import __version__
from toolbox_runner.tools import ToolSniffer

app = FastAPI(
    version=__version__,
    title="Async tool-specs enabled Container Runner",
    description="Asynchronous dispatching server for containerized tools implementing tool-specs interface."
)




@app.get("/")
def index():
    return {
        'version': __version__
    }

@app.get("/image/{image_name}")
def get_tools(image_name: str):
    sniffer = ToolSniffer(docker_image=image_name)
    
    return {
        'image': image_name,
        'tools': sniffer.get_tools()
    }


if __name__ == '__main__':
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=5555, reload=True)
