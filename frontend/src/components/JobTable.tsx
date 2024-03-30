import { notification, Space, Table } from "antd"
import type { TableColumnsType } from "antd"
import { DeleteOutlined, CaretRightOutlined, DownloadOutlined } from "@ant-design/icons"
import { AxiosError } from "axios"

import { ToolJob, ToolJobStatus, useJobs } from "../context/JobContext"
import { useEffect, useState } from "react"
import { useSettings } from "../context/SettingsContext"


const JobTable: React.FC = () => {
    // get the jobs from the job context
    const { jobs, runJob, refreshJobs, deleteJob } = useJobs()

    // get the backend url
    const { backendUrl } = useSettings()

    // get the notification context
    const [notificationApi, notificationContext] = notification.useNotification()
    
    // crete a handler for running jobs
    const handleRunJob = (jobId: string) => {
        // start the job and directly refresh
        runJob(jobId).then(job => {
            notificationApi.success({
                message: 'Job Finished',
                description: `Job ${job.job_id} finished after ${job.runtime?.toFixed(1)} seconds with status ${job.result_status}`
            })
        }).catch((err: AxiosError<{detail: string}>) => {
            notificationApi.error({
                message: 'Backend Error on Job Run',
                description: err.response?.data?.detail || err.message,
            })
        })

        // directly refresh without waiting for the job to finish
        refreshJobs().then(() => {
            // after refreshing notify, the the job has been started
            notificationApi.info({
                message: 'Job Started',
                description: `Job ${jobId} has been started`
            })
        })
    }

    // handle the deletion
    const handleDelete = (jobId: string) => {
        deleteJob(jobId)
        .then(({ message }) => {
            notificationApi.success({
                message: `Success`,
                description: message
            })
        })
        .then(() => refreshJobs())
        .catch((err: AxiosError<{detail: string}>) => {
            notificationApi.error({
                message: 'Backend Error on Job Deletion',
                description: err.response?.data?.detail || err.message,
            })
        })
    }

    // build the columns whenever the jobs change
    const [columns, setColumns] = useState<TableColumnsType<ToolJob>>([])
    
    // build the columns
    useEffect(() => {
        const cols: TableColumnsType<ToolJob> = [
            {
                title: 'Tool Name', 
                dataIndex: 'tool_name', 
                filters: jobs.filter((job, idx, arr) => arr.indexOf(job) === idx).map(job => ({text: job.tool_name, value: job.tool_name})), 
                onFilter: (value, record) => record.tool_name === value,
                sortOrder: 'descend'
            },
            {
                title: 'Job status',
                dataIndex: 'status',
                filters: Object.values(ToolJobStatus).map(status => ({text: status, value: status})),
                onFilter: (value, record) => record.status === value
            },
            {
                title: 'Result status',
                dataIndex: 'result_status',
                filters: jobs.filter((job, idx, arr) => job.result_status && arr.indexOf(job) === idx).map(job => ({text: job.result_status!, value: job.result_status!})),
                onFilter: (value, record) => record.result_status === value
            },
            {
                title: 'Runtime',
                dataIndex: 'runtime',
            },
            {
                title: 'Action',
                dataIndex: '',
                render: (record) => (<Space>
                    {record.status === 'pending' ? (
                        <CaretRightOutlined style={{color: 'green', cursor: 'pointer'}} onClick={() => handleRunJob(record.job_id)} />
                    ) : null}
                    { record.status === 'completed' ? (
                        <a href={`${backendUrl}/job/${record.job_id}/result/results.zip`} download>
                            <DownloadOutlined style={{color: 'blue', cursor: 'pointer'}} />
                        </a>
                    ) : null }
                    <DeleteOutlined style={{color: 'red', cursor: 'pointer'}} onClick={() => handleDelete(record.job_id)} />
                </Space>)
            }
        ]

        setColumns(cols)
    }, [jobs])
    
    return <>
        { notificationContext }
        <Table dataSource={jobs} columns={columns} />
    </>
}

export default JobTable