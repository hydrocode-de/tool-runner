import { Flex, List, notification } from "antd"
import { CaretRightOutlined, DeleteOutlined } from "@ant-design/icons"

import {  useJobs } from "../context/JobContext"
import { AxiosError } from "axios"


const JobList: React.FC = () => {
    // get the jobs from the job context
    const { jobs, runJob, refreshJobs, deleteJob } = useJobs()

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

    
    return <>
        { notificationContext}
        <List 
            itemLayout="vertical"
            dataSource={jobs}
            renderItem={job => (
                <List.Item
                    actions={[
                        job.status === 'pending' ? (
                            <CaretRightOutlined style={{color: 'green', cursor: 'pointer'}} onClick={() => handleRunJob(job.job_id)} />
                        ) : null,
                        <DeleteOutlined style={{color: 'red', cursor: 'pointer'}} onClick={() => handleDelete(job.job_id)} />
                    ]}
                >
                    <List.Item.Meta 

                        title={<Flex style={{width: '100%'}}>
                            <div>{job.tool_name} tool</div>
                            <div>created {job.timestamp}</div>
                        </Flex>}
                        description={`Status: ${job.status} - Results: ${job.result_status} - mount: ${job.out_dir}` }
                    />
                </List.Item>
            )}
            
        />
    </>
}

export default JobList