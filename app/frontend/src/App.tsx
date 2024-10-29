import { useState } from "react";
import { Mic, MicOff } from "lucide-react";

import { Button } from "@/components/ui/button";
import { GroundingFiles } from "@/components/ui/grounding-files";
import GroundingFileView from "@/components/ui/grounding-file-view";
import StatusMessage from "@/components/ui/status-message";

import useRealTime from "@/hooks/useRealtime";
import useAudioRecorder from "@/hooks/useAudioRecorder";
import useAudioPlayer from "@/hooks/useAudioPlayer";

import { GroundingFile, ToolResult } from "./types";

import logo from "./assets/new-logo.svg";

function App() {
    const [isRecording, setIsRecording] = useState(false);
    const [groundingFiles, setGroundingFiles] = useState<GroundingFile[]>([]);
    const [selectedFile, setSelectedFile] = useState<GroundingFile | null>(null);

    const [chatHistory, setChatHistory] = useState<{
        role: 'user' | 'ai';
        message: string;
        translatedMessage?: string;  // 번역된 텍스트 저장
    }[]>([]);

    // 번역 중인 상태 추가
    const [translatingIndex, setTranslatingIndex] = useState<number | null>(null);

    const translateMessage = async (message: string, index: number) => {
        try {
            setTranslatingIndex(index);
            const response = await fetch('/api/translate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: message })
            });
            
            const data = await response.json();
            
            setChatHistory(prev => prev.map((chat, i) => 
                i === index 
                    ? { ...chat, translatedMessage: data.translatedText }
                    : chat
            ));
        } catch (error) {
            console.error('Translation error:', error);
        } finally {
            setTranslatingIndex(null);
        }
    };

    const { startSession, addUserAudio, inputAudioBufferClear } = useRealTime({
        enableInputAudioTranscription: true,
        onWebSocketOpen: () => console.log("WebSocket connection opened"),
        onWebSocketClose: () => console.log("WebSocket connection closed"),
        onWebSocketError: event => console.error("WebSocket error:", event),
        onReceivedError: message => console.error("error", message),
        onReceivedResponseAudioDelta: message => {
            isRecording && playAudio(message.delta);
        },
        onReceivedInputAudioBufferSpeechStarted: () => {
            stopAudioPlayer();
        },
        onReceivedExtensionMiddleTierToolResponse: message => {
            const result: ToolResult = JSON.parse(message.tool_result);

            const files: GroundingFile[] = result.sources.map(x => {
                const match = x.chunk_id.match(/_pages_(\d+)$/);
                const name = match ? `${x.title}#page=${match[1]}` : x.title;
                return { id: x.chunk_id, name: name, content: x.chunk };
            });

            setGroundingFiles(prev => [...prev, ...files]);
        }, 
        onReceivedInputAudioTranscriptionCompleted: transcription => {
            // 사용자 발화 완료시
            if(transcription.transcript) {
                setChatHistory(prev => [...prev, {
                    role: 'user',
                    message: transcription.transcript
                }]);
            }
        },
        onReceivedResponseDone: responseDone => {
             // AI 응답 완료시
             if (responseDone.response && responseDone.response.output) {
                responseDone.response.output.forEach(output => {
                    if (output.content) {
                        output.content.forEach(content => {
                            if (content.transcript) {
                                setChatHistory(prev => [...prev, {
                                    role: 'ai',
                                    message: content.transcript
                                }]);
                            }
                        });
                    }
                });
            }
        }
    });

    const { reset: resetAudioPlayer, play: playAudio, stop: stopAudioPlayer } = useAudioPlayer();
    const { start: startAudioRecording, stop: stopAudioRecording } = useAudioRecorder({ onAudioRecorded: addUserAudio });

    const onToggleListening = async () => {
        if (!isRecording) {
            startSession();
            await startAudioRecording();
            resetAudioPlayer();

            setIsRecording(true);
        } else {
            await stopAudioRecording();
            stopAudioPlayer();
            inputAudioBufferClear();

            setIsRecording(false);
        }
    };

    return (
        <div className="flex min-h-screen flex-col bg-gray-100 text-gray-900">
            <div className="p-4 sm:absolute sm:left-4 sm:top-4">
                <img src={logo} alt="New logo" className="h-16 w-16" />
            </div>
            <main className="flex flex-grow flex-col items-center justify-center">
                <h1 className="mb-8 bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-4xl font-bold text-transparent md:text-7xl">
                    Talk to an AI Korean friend!
                </h1>
                <div className="mb-4 flex flex-col items-center justify-center">
                    <Button
                        onClick={onToggleListening}
                        className={`h-12 w-60 ${isRecording ? "bg-red-600 hover:bg-red-700" : "bg-purple-500 hover:bg-purple-600"}`}
                        aria-label={isRecording ? "Stop recording" : "Start recording"}
                    >
                        {isRecording ? (
                            <>
                                <MicOff className="mr-2 h-4 w-4" />
                                Stop conversation
                            </>
                        ) : (
                            <>
                                <Mic className="mr-2 h-6 w-6" />
                            </>
                        )}
                    </Button>
                    <StatusMessage isRecording={isRecording} />
                </div>
                <div className="w-full max-w-2xl mx-auto mt-8 p-4 bg-white rounded-lg shadow">
                    {chatHistory.map((chat, index) => (
                        <div key={index} className={`mb-4 ${
                            chat.role === 'user' ? 'text-right' : 'text-left'
                        }`}>
                            <div className={`inline-block p-3 rounded-lg ${
                                chat.role === 'user' 
                                    ? 'bg-purple-500 text-white' 
                                    : 'bg-gray-200 text-gray-800'
                            }`}>
                                {chat.message}
                                <div className="mt-2">
                                    <button
                                        onClick={() => translateMessage(chat.message, index)}
                                        disabled={translatingIndex === index}
                                        className={`text-xs underline ${
                                            chat.role === 'ai' 
                                                ? 'text-gray-600'  // AI 응답의 번역 버튼 스타일
                                                : 'text-white'     // 사용자 메시지의 번역 버튼 스타일
                                        }`}
                                    >
                                        {translatingIndex === index ? '...' : 'Translate'}
                                    </button>
                                    {chat.translatedMessage && (
                                        <div className="mt-2 text-sm">
                                            {chat.translatedMessage}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
                <GroundingFiles files={groundingFiles} onSelected={setSelectedFile} />
            </main>

            <footer className="py-4 text-center">
                <p>© 2024 Koreigner. All rights reserved. | Seoul, Korea</p>
            </footer>

            <GroundingFileView groundingFile={selectedFile} onClosed={() => setSelectedFile(null)} />
        </div>
    );
}

export default App;
