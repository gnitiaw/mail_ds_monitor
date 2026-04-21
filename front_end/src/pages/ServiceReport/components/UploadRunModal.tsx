import React, { useEffect, useState } from 'react';
import { Alert, DatePicker, Form, Modal, Upload, message } from 'antd';
import type { UploadFile, UploadProps } from 'antd';
import dayjs from 'dayjs';
import { createServiceReportRun, createServiceReportSourceRun } from '../../../api/serviceReport';
import type { ServiceReportConfig } from '../../../api/types';

const { RangePicker } = DatePicker;

interface UploadRunModalProps {
  visible: boolean;
  config: ServiceReportConfig | null;
  onCancel: () => void;
  onSuccess: (runId: string) => void;
}

const normalizeUploadEvent = (event: { fileList?: UploadFile[] } | UploadFile[]): UploadFile[] => {
  if (Array.isArray(event)) {
    return event;
  }
  return event?.fileList ?? [];
};

const singleFileProps: UploadProps = {
  maxCount: 1,
  beforeUpload: () => false,
  accept: '.csv,.xlsx',
};

const getRequiredFile = (fileList: UploadFile[] | undefined, label: string): File => {
  const file = fileList?.[0]?.originFileObj;
  if (!(file instanceof File)) {
    throw new Error(`${label} 未上传`);
  }
  return file;
};

const UploadRunModal: React.FC<UploadRunModalProps> = ({ visible, config, onCancel, onSuccess }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!visible) {
      return;
    }
    form.resetFields();
    form.setFieldsValue({
      time_range: [dayjs().startOf('month'), dayjs().endOf('month')],
    });
  }, [visible, form]);

  const handleOk = async () => {
    if (!config) {
      return;
    }

    try {
      const values = await form.validateFields();
      const [start, end] = values.time_range as [dayjs.Dayjs, dayjs.Dayjs];
      setLoading(true);
      const sourceRun = await createServiceReportSourceRun(config.config_id, {
        window_start: start.toISOString(),
        window_end: end.toISOString(),
        inspection_file: getRequiredFile(values.inspection_file, '巡检文件'),
        vulnerability_file: getRequiredFile(values.vulnerability_file, '漏洞文件'),
        worklog_file: getRequiredFile(values.worklog_file, '运维工作记录文件'),
        zentao_bug_file: getRequiredFile(values.zentao_bug_file, '禅道缺陷文件'),
      });
      const run = await createServiceReportRun(config.config_id, {
        window_start: start.toISOString(),
        window_end: end.toISOString(),
        source_run_id: sourceRun.source_run_id,
        force_regenerate: false,
      });
      message.success('已完成数据汇总并生成报告');
      onSuccess(run.run_id);
    } catch (error) {
      if (error instanceof Error && error.message.endsWith('未上传')) {
        message.error(error.message);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title={config ? `上传材料并生成报告：${config.name}` : '上传材料并生成报告'}
      open={visible}
      onOk={handleOk}
      onCancel={onCancel}
      confirmLoading={loading}
      destroyOnClose
      okText="开始生成"
      width={720}
    >
      <Form form={form} layout="vertical">
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 20 }}
          message="运行时上传导入"
          description="首期要求在每次生成报告时上传四类标准文件。页面会先完成 source_run，再基于该快照生成 report_run。"
        />

        <Form.Item
          name="time_range"
          label="报告时间窗口"
          rules={[{ required: true, message: '请选择报告时间窗口' }]}
        >
          <RangePicker showTime style={{ width: '100%' }} />
        </Form.Item>

        <Form.Item
          name="inspection_file"
          label="巡检结果文件"
          valuePropName="fileList"
          getValueFromEvent={normalizeUploadEvent}
          rules={[{ required: true, message: '请上传巡检结果文件' }]}
        >
          <Upload {...singleFileProps}>
            <div>点击上传 `.csv` / `.xlsx` 文件</div>
          </Upload>
        </Form.Item>

        <Form.Item
          name="vulnerability_file"
          label="漏洞修复文件"
          valuePropName="fileList"
          getValueFromEvent={normalizeUploadEvent}
          rules={[{ required: true, message: '请上传漏洞修复文件' }]}
        >
          <Upload {...singleFileProps}>
            <div>点击上传 `.csv` / `.xlsx` 文件</div>
          </Upload>
        </Form.Item>

        <Form.Item
          name="worklog_file"
          label="运维工作记录文件"
          valuePropName="fileList"
          getValueFromEvent={normalizeUploadEvent}
          rules={[{ required: true, message: '请上传运维工作记录文件' }]}
        >
          <Upload {...singleFileProps}>
            <div>点击上传 `.csv` / `.xlsx` 文件</div>
          </Upload>
        </Form.Item>

        <Form.Item
          name="zentao_bug_file"
          label="禅道缺陷清单文件"
          valuePropName="fileList"
          getValueFromEvent={normalizeUploadEvent}
          rules={[{ required: true, message: '请上传禅道缺陷文件' }]}
        >
          <Upload {...singleFileProps}>
            <div>点击上传 `.csv` / `.xlsx` 文件</div>
          </Upload>
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default UploadRunModal;
