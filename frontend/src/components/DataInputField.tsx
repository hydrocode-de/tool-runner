import { useEffect, useState } from "react"
import { Button, Input, Radio, Upload, UploadFile } from "antd"
import { UploadOutlined } from "@ant-design/icons"
import Title from "antd/es/typography/Title"


import { ToolInputData } from "../context/ToolsContext"


interface DataInputFieldProps {
    name: string
    value: string | UploadFile | undefined
    dataConf?: ToolInputData
    onChange: (data: string | UploadFile | undefined) => void
}

const DataInputField: React.FC<DataInputFieldProps> = ({ name, value, dataConf, onChange  }) => {
    // define a state to track the input mode
    const [mode, setMode] = useState<"upload" | "path" | "job">("upload")

    // empty the value when the mode changes
    useEffect(() => onChange(undefined), [mode])

    return <>
        <Title level={3}>{name}</Title>
        <p>{dataConf?.description}</p>
        <Radio.Group 
            value={mode}
            options={[
                { label: "Upload File", value: "upload" },
                { label: "Host Path", value: "path" },
                { label: "Job Result", value: "job", disabled: true }
            ]}
            optionType="button"
            onChange={e => setMode(e.target.value)}
        />

        {/* Switch the mode */}
        { mode === "path" ? (
            <>
                <p>You need to set the path to the file on the <strong>Host</strong> machine</p>
                <Input type="text" value={value as string || ''}  onChange={e => onChange(e.target.value)}/>
            </>
        ) : null}

        { mode === "upload" ? (
            
            <Upload.Dragger
                style={{padding: '1rem'}}
                accept={Array.isArray(dataConf?.extension) ? dataConf.extension.join(",") : dataConf?.extension}
                beforeUpload={() => false}
                onChange={info => onChange(info.fileList[0])}
            >
                <Button icon={<UploadOutlined />}>Upload File</Button>
            </Upload.Dragger>
            
        ) : null}

        { JSON.stringify(value) }

    </>
}

export default DataInputField