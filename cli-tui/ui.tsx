import React, { useState, useEffect } from 'react';
import { render, Text, Box } from 'ink';
import Spinner from 'ink-spinner';

const App = () => {
    // 定义界面状态
    const [status, setStatus] = useState('初始化中...');
    const [report, setReport] = useState('');
    const [isDone, setIsDone] = useState(false);

    useEffect(() => {
        // 这个函数负责调用我们写好的 Python 后端
        const runAgent = async () => {
            setStatus('正在连接 ReviewBot 后台服务...');
            
            // 准备一段用于测试的代码
            const testCode = `
def update_user(name, db_host, db_name):
    # 这里的密码有安全风险哦
    db_conn = f"mysql://root:123456@{db_host}/{db_name}"
    print("User updated")
            `;
            
            try {
                // 使用原生的 fetch 发起 POST 请求
                const response = await fetch('http://127.0.0.1:8000/review', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code: testCode })
                });

                // 读取服务器源源不断推过来的流式数据 (SSE)
                const reader = response.body?.getReader();
                const decoder = new TextDecoder('utf-8');

                while (true) {
                    const { done, value } = await reader!.read();
                    if (done) break;
                    
                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\n');
                    
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            // 解析后端传来的 JSON 进度
                            const data = JSON.parse(line.slice(6));
                            if (data.status === 'processing') {
                                setStatus(data.message); // 更新动画旁边的文字
                            } else if (data.status === 'done') {
                                setReport(data.report);  // 保存最终报告
                                setIsDone(true);         // 标记任务完成
                            }
                        }
                    }
                }
            } catch (error) {
                setStatus('❌ 连接失败，请确保 Python 后台服务已启动！');
                setIsDone(true);
            }
        };

        runAgent();
    }, []);

    // 渲染 UI 界面
    return (
        <Box flexDirection="column" padding={1}>
            {/* 顶部标题框 */}
            <Box borderStyle="round" borderColor="cyan" padding={1}>
                <Text bold color="cyan">🚀 ReviewBot - 智能 DevOps 审查终端</Text>
            </Box>
            
            {/* 状态展示区 */}
            {!isDone ? (
                <Box marginTop={1}>
                    <Text color="green"><Spinner type="dots" /> </Text>
                    <Text>{status}</Text>
                </Box>
            ) : (
                <Box marginTop={1} flexDirection="column">
                    <Text bold color="green">✅ 代码审查完成！生成报告如下：</Text>
                    <Box marginTop={1} paddingLeft={2} borderStyle="single" borderColor="gray">
                        <Text>{report}</Text>
                    </Box>
                </Box>
            )}
        </Box>
    );
};

// 启动 React 终端应用
render(<App />);