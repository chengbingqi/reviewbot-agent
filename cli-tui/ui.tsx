import React, { useState, useEffect } from 'react';
import { render, Text, Box } from 'ink';
import Spinner from 'ink-spinner';

type SsePayload = {
    event: string;
    node?: string;
    message: string;
    data?: {
        report?: string;
    };
    error?: string;
};

const App = () => {
    const [status, setStatus] = useState('Initializing...');
    const [report, setReport] = useState('');
    const [warnings, setWarnings] = useState<string[]>([]);
    const [isDone, setIsDone] = useState(false);

    useEffect(() => {
        const runAgent = async () => {
            setStatus('Connecting to ReviewBot backend...');

            const testCode = `
def update_user(name, db_host, db_name):
    db_conn = f"mysql://root:123456@{db_host}/{db_name}"
    print("User updated")
            `;

            try {
                const response = await fetch('http://127.0.0.1:8000/review', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code: testCode })
                });

                const reader = response.body?.getReader();
                const decoder = new TextDecoder('utf-8');

                if (!reader) {
                    throw new Error('Response stream is unavailable.');
                }

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\n');

                    for (const line of lines) {
                        if (!line.startsWith('data: ')) continue;
                        const payload = JSON.parse(line.slice(6)) as SsePayload;
                        if (payload.event === 'node_end') {
                            setStatus(payload.message);
                        } else if (payload.event === 'error') {
                            setWarnings((items) => [...items, `${payload.node ?? 'unknown'}: ${payload.message}`]);
                        } else if (payload.event === 'done') {
                            setReport(payload.data?.report ?? '');
                            setIsDone(true);
                        }
                    }
                }
            } catch (error) {
                setWarnings((items) => [...items, 'Connection failed. Ensure the Python backend is running.']);
                setIsDone(true);
            }
        };

        runAgent();
    }, []);

    return (
        <Box flexDirection="column" padding={1}>
            <Box borderStyle="round" borderColor="cyan" padding={1}>
                <Text bold color="cyan">ReviewBot - AI Code Review Terminal</Text>
            </Box>

            {!isDone ? (
                <Box marginTop={1}>
                    <Text color="green"><Spinner type="dots" /> </Text>
                    <Text>{status}</Text>
                </Box>
            ) : (
                <Box marginTop={1} flexDirection="column">
                    <Text bold color="green">Review finished.</Text>
                    {warnings.length > 0 && (
                        <Box marginTop={1} flexDirection="column">
                            <Text color="yellow">Warnings:</Text>
                            {warnings.map((item, index) => (
                                <Text key={index} color="yellow">- {item}</Text>
                            ))}
                        </Box>
                    )}
                    <Box marginTop={1} paddingLeft={2} borderStyle="single" borderColor="gray">
                        <Text>{report || 'No report generated.'}</Text>
                    </Box>
                </Box>
            )}
        </Box>
    );
};

render(<App />);
