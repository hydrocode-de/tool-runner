import { useEffect, useState } from "react"
import Title from "antd/es/typography/Title"
import { Collapse, DatePicker, Empty, Input, InputNumber, Select, Switch, UploadFile } from "antd"
import { Dayjs } from "dayjs"
import { JsonEditor } from "json-edit-react"

import { Tool } from "../context/ToolsContext"
import DataInputField from "./DataInputField"


interface Parameterization {
    [key: string]: any
}
interface RunToolFormProps {
    tool: Tool
    onParamChange: (params: Parameterization) => void,
    onDataChange: (data: {[key: string]: string | UploadFile | undefined}) => void
}

const RunToolForm: React.FC<RunToolFormProps> = ({ tool, onParamChange, onDataChange }) => {
    // create a state to store the parameters
    const defaultValues = Object.values(tool.parameters).reduce((obj, p) => (obj[p.name] = p.default, obj), {} as Parameterization)
    const [param, setParam] = useState<Parameterization>(defaultValues)
    const [data, setData] = useState<{[key: string]: string | UploadFile | undefined}>({})

    // create a function to update the params
    const updateParam = (name: string, value: any) => {
        const newParam = { ...param, [name]: value }
        setParam(newParam)
    }

    // create a function to update the dataConf
    const updateData = (name: string, value: string | UploadFile | undefined) => {
        const newData = { ...data, [name]: value }
        setData(newData)
    }

    // use effect to listen to changes in param and call the onChange function
    useEffect(() => onParamChange(param), [param])
    useEffect(() => onDataChange(data), [data])

    return <>
        <Title level={1}>{tool.title ? tool.title : tool.name}</Title>
        <p>{ tool.description }</p>

        <Collapse>
            <Collapse.Panel header="Parameters" key="parameters">
                { Object.entries(tool.parameters).map(([name, parameter]) => (
                    <div key={name}>
                        <Title level={4}>{name}</Title>
                        <p>{parameter.description}</p>
                        
                        {/* Switch the different input types */}
                        { parameter.type === "string" ? (
                            <Input type="text" value={param[name]} onChange={e => updateParam(name, e.target.value)} />
                        ) : null }

                        { ["integer", "float"].includes(parameter.type) ? (
                            <InputNumber 
                                value={param[name]} 
                                onChange={e => updateParam(name, e.target.value)}
                                min={parameter.min}
                                max={parameter.max}
                                step={parameter.type === "integer" ? 1 : 0.1}
                            />
                        ) : null}

                        { parameter.type === "boolean" ? (
                            <Switch checked={param[name]} onChange={s => updateParam(name, s)} />
                        ) : null}

                        { parameter.type === "enum" ? (
                            <Select 
                                value={param[name]}
                                onChange={v => updateParam(name, v)}
                                options={parameter.values?.map(v => ({ label: v, value: v }))}
                            />
                        ) : null }

                        { ["date", "time", "datetime"].includes(parameter.type) ? (
                            <DatePicker 
                                value={new Dayjs(param[name])}
                                onChange={d => updateParam(name, d?.toISOString())}
                            />
                        ) : null }

                        { parameter.type === "struct" ? (
                            <JsonEditor
                                data={param[name] || {}}
                                onUpdate={({ newData }) => updateParam(name, newData)}
                            />
                        ) : null }
                    </div>

                )) }
            </Collapse.Panel>
        </Collapse>

        <Collapse>
            <Collapse.Panel header="Data" key="data">

                {tool.data ?  Object.entries(tool.data).map(([name, dataConf]) => (
                    <div key={name}>
                        <DataInputField name={name} value={data[name]} dataConf={dataConf} onChange={value => updateData(name, value)} />
                    </div>
                )) : <Empty />}

            </Collapse.Panel>
        </Collapse>
        {/* <pre>
            <code>
                {JSON.stringify(tool, null, 2)}
            </code>
        </pre> */}
    </>
}

export default RunToolForm