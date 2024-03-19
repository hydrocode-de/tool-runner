"""
These utility functions should be added to json2args 
"""
from typing import List, Dict, Type, TYPE_CHECKING
from enum import StrEnum

from pydantic import BaseModel, create_model
from pydantic.fields import FieldInfo

if TYPE_CHECKING:
    from toolbox_runner.models import Parameter

# define a lookup to map tool-spec types to pydantic types
TYPE_LOOKUP = {
    'string': str,
    'integer': int,
    'float': float,
    'boolean': bool,
    'date': str,
    'datetime': str,
    'time': str,
    'struct': dict,
    'asset': str,
    'enum': StrEnum
}

# define the building blocks of the inputs.json
class InputParameter(BaseModel):
    pass

class InputData(BaseModel):
    pass


def create_field_tuple(par: 'Parameter'):
    if par.type == 'enum':
        type_ =  StrEnum(par.name, {v: v for v in par.values})
    elif par.array:
        type_ = List[TYPE_LOOKUP[par.type]]
    else:
        type_ = TYPE_LOOKUP[par.type]

    # build field arguments
    args = {}
    # add default values if any
    if par.default is not None:
        args['default'] = par.default
    
    # add optional flag
    elif par.optional:
        args['default'] = None
    
    # add description
    if par.description is not None:
        args['description'] = par.description

    # add the value range limits
    if par.min is not None:
        args['ge'] = par.min
    if par.max is not None:
        args['le'] = par.max
    
    # return as tuple
    return (type_, FieldInfo(**args))


def create_input_model(name: str, parameters: Dict[str, 'Parameter']) -> Type[InputParameter]:
    """
    Create a Pydantic model of the input parameters dynamically from the contents
    of the parameters attribute.
    """
    
                
    # create a dictionary of the parameters
    fields = {name: create_field_tuple(par) for name, par in parameters.items()}

    
    # generate the model name 
    model_name = name.replace('_', ' ').title().replace(' ', '') + 'Params'
    # dynamically create a Pydantic model
    Model = create_model(model_name, **fields, __base__=InputParameter)

    return Model
