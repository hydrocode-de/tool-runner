from typing import Optional, List, Dict, Type

from pydantic import BaseModel, Field

from toolbox_runner.util import create_input_model, InputParameter


class Parameter(BaseModel):
    name: str
    description:Optional[str] = None
    type: str
    array: Optional[bool] = False
    optional: Optional[bool] = False
    default: Optional[bool] = None
    min: Optional[int | float] = None
    max: Optional[int | float] = None
    values: Optional[List[str]] = None


class Data(BaseModel):
    path: str
    description: Optional[str] = None
    example: Optional[str] = None
    extension: Optional[str] = None

    # TODO: implement custom validators, that check each file for extension if given




class Tool(BaseModel):
    name: str
    title: str
    description: str
    version: Optional[str] = None
    parameters: Dict[str, Parameter] = Field(repr=False)
    data: Optional[List[str] | Dict[str, Data]] = None

    # image metadata
    docker_image: str

    def input_validator(self) -> Type[InputParameter]:
        """
        Create a Pydantic model of the input parameters dynamically from the contents
        of the parameters attribute.
        """
        Model = create_input_model(self.name, self.parameters)

        return Model
    
    def input_file(self, parameter: Optional[dict] = None, data: Dict[str, str] = {}) -> dict:
        """
        Return a serializable representation of the inputs.json needed to dispatch 
        a new tool-spec enabled docker job.
        """
        # get the input model
        Validator = self.input_validator()

        # validate the parameter
        valid_params = Validator(**parameter)

        # validate the data input
        # TODO: not sure where to do the actual copy of the files
        data_paths = {name: Data(path=path).path for name, path in data.items()}


        # build the inputs.json
        inputs = {
            self.name: {
                'parameters': valid_params.model_dump(), 
                'data': data_paths
            }
        }

        return inputs
