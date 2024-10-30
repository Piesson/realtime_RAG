import aiohttp
import asyncio
import json
from enum import Enum
from typing import Any, Callable, Optional
from aiohttp import web
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.core.credentials import AzureKeyCredential
import logging
from logging.handlers import RotatingFileHandler

# 기존 logger 설정을 아래 코드로 교체
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class ToolResultDirection(Enum):
    TO_SERVER = 1
    TO_CLIENT = 2

class ToolResult:
    text: str
    destination: ToolResultDirection

    def __init__(self, text: str, destination: ToolResultDirection):
        self.text = text
        self.destination = destination

    def to_text(self) -> str:
        if self.text is None:
            return ""
        return self.text if type(self.text) == str else json.dumps(self.text)

class Tool:
    target: Callable[..., ToolResult]
    schema: Any

    def __init__(self, target: Any, schema: Any):
        self.target = target
        self.schema = schema

class RTToolCall:
    tool_call_id: str
    previous_id: str

    def __init__(self, tool_call_id: str, previous_id: str):
        self.tool_call_id = tool_call_id
        self.previous_id = previous_id

class RTMiddleTier:
    endpoint: str
    deployment: str
    key: Optional[str] = None
    
    # Tools are server-side only for now, though the case could be made for client-side tools
    # in addition to server-side tools that are invisible to the client
    tools: dict[str, Tool] = {}

    # Server-enforced configuration, if set, these will override the client's configuration
    # Typically at least the model name and system message will be set by the server
    model: Optional[str] = None
    system_message: Optional[str] = None
    temperature: float = 1.0  # Optional[float] = None
    max_tokens: Optional[int] = None
    disable_audio: Optional[bool] = None

    _tools_pending = {}
    _token_provider = None

    def __init__(self, endpoint: str, deployment: str, credentials: AzureKeyCredential | DefaultAzureCredential):
        self.endpoint = endpoint
        self.deployment = deployment
        if isinstance(credentials, AzureKeyCredential):
            self.key = credentials.key
        else:
            self._token_provider = get_bearer_token_provider(credentials, "https://cognitiveservices.azure.com/.default")
            self._token_provider() # Warm up during startup so we have a token cached when the first request arrives

        # 새로운 속성 추가
        self._response_in_progress = False
        self._last_search_time = None

    async def _process_message_to_client(self, msg: str, client_ws: web.WebSocketResponse, server_ws: web.WebSocketResponse) -> Optional[str]:
        message = json.loads(msg.data)
        updated_message = msg.data
        if message is not None:
            match message["type"]:
                case "session.created":
                    session = message["session"]
                    # Hide the instructions, tools and max tokens from clients, if we ever allow client-side 
                    # tools, this will need updating
                    session["instructions"] = ""
                    session["tools"] = []
                    session["tool_choice"] = "none"
                    session["max_response_output_tokens"] = None
                    updated_message = json.dumps(message)

                case "response.output_item.added":
                    if "item" in message and message["item"]["type"] == "function_call":
                        updated_message = None

                case "conversation.item.created":
                    if "item" in message and message["item"]["type"] == "function_call":
                        item = message["item"]
                        if item["call_id"] not in self._tools_pending:
                            self._tools_pending[item["call_id"]] = RTToolCall(item["call_id"], message["previous_item_id"])
                        updated_message = None
                    elif "item" in message and message["item"]["type"] == "function_call_output":
                        updated_message = None

                case "response.function_call_arguments.delta":
                    updated_message = None
                
                case "response.function_call_arguments.done":
                    updated_message = None

                case "response.output_item.done":
                    if "item" in message and message["item"]["type"] == "function_call":
                        if self._response_in_progress:  # 이미 응답 진행 중이면 중복 호출 방지
                            return None
                        self._response_in_progress = True # 새로 추가
                        item = message["item"]
                        tool_call = self._tools_pending[message["item"]["call_id"]]
                        tool = self.tools[item["name"]]
                        args = item["arguments"]
                        result = await tool.target(json.loads(args))
                        await server_ws.send_json({
                            "type": "conversation.item.create",
                            "item": {
                                "type": "function_call_output",
                                "call_id": item["call_id"],
                                "output": result.to_text() if result.destination == ToolResultDirection.TO_SERVER else ""
                            }
                        })
                        if result.destination == ToolResultDirection.TO_CLIENT:
                            # TODO: this will break clients that don't know about this extra message, rewrite 
                            # this to be a regular text message with a special marker of some sort
                            
                            # 여기에 로깅 코드 추가
                            tool_result = result.to_text()
                            logger.info(f"Tool result before sending to client: {tool_result}")
                            await client_ws.send_json({
                                "type": "extension.middle_tier_tool_response",
                                "previous_item_id": tool_call.previous_id,
                                "tool_name": item["name"],
                                "tool_result": result.to_text()
                            })
                        updated_message = None

                case "response.done":
                    if len(self._tools_pending) > 0:
                        self._tools_pending.clear() # Any chance tool calls could be interleaved across different outstanding responses?
                        await server_ws.send_json({
                            "type": "response.create"
                        })
                    if "response" in message:
                        replace = False
                        for i, output in enumerate(reversed(message["response"]["output"])):
                            if output["type"] == "function_call":
                                message["response"]["output"].pop(i)
                                replace = True
                        if replace:
                            updated_message = json.dumps(message)                        

        return updated_message

    async def _process_message_to_server(self, msg: str, ws: web.WebSocketResponse) -> Optional[str]:
            message = json.loads(msg.data)
            logger.info(f"Received message type: {message.get('type')}")
            updated_message = msg.data
            if message is not None:
                match message["type"]:
                    case "session.update":
                        session = message["session"]
                        modified = False
                         
                        # system message 추가
                        if self.system_message is not None and session.get("instructions") != self.system_message:
                            session["instructions"] = self.system_message
                            modified = True
                            logger.info(f"Updated system message: {self.system_message}")
                        
                        # 기존 설정들 유지
                        if self.temperature is not None:
                            session["temperature"] = self.temperature
                        if self.max_tokens is not None:
                            session["max_response_output_tokens"] = self.max_tokens
                        if self.disable_audio is not None:
                            session["disable_audio"] = self.disable_audio
                        
                        # tools 관련 설정
                        session["tool_choice"] = "auto" if len(self.tools) > 0 else "none" # auto -> required
                        # session["tool_choice"] = {"type": "function", "function": {"name": "search"}},
                        session["tools"] = [tool.schema for tool in self.tools.values()]
                        
                        updated_message = json.dumps(message)
                        logger.info(f"Returning message: {updated_message[:200]}...")  # 메시지가 길 수 있으므로 일부만 로깅
                        
                        if modified:
                            updated_message = json.dumps(message)
                        else:
                            updated_message = msg.data
                        
            return updated_message

    async def _forward_messages(self, ws: web.WebSocketResponse):
        async with aiohttp.ClientSession(base_url=self.endpoint) as session:
            params = { "api-version": "2024-10-01-preview", "deployment": self.deployment, "voice" : "nova"} # 목소리 변경 -> "voice" : "nova" 
            headers = {}
            if "x-ms-client-request-id" in ws.headers:
                headers["x-ms-client-request-id"] = ws.headers["x-ms-client-request-id"]
            if self.key is not None:
                headers = { "api-key": self.key }
            else:
                headers = { "Authorization": f"Bearer {self._token_provider()}" } # NOTE: no async version of token provider, maybe refresh token on a timer?
            
            async with session.ws_connect("/openai/realtime", headers=headers, params=params) as target_ws:
            
            # 초기 세션 설정을 더 완벽하게 구성
                initial_session = {
                        "type": "session.update",
                        "session": {
                            "instructions": self.system_message,
                            "turn_detection": {
                                "type": "server_vad",
                                "threshold": 0.5,
                                "silence_duration_ms": 600
                            },
                            "tool_choice": "auto" if len(self.tools) > 0 else "none",
                            # "tool_choice": {"type": "function", "function": {"name": "search"}},
                            "tools": [tool.schema for tool in self.tools.values()],
                            "temperature": self.temperature,
                            "max_response_output_tokens": self.max_tokens
                             }
                         }
                    
                # None인 필드 제거
                initial_session["session"] = {k: v for k, v in initial_session["session"].items() if v is not None}
            
                await target_ws.send_json(initial_session)
                logger.info(f"Sent initial session configuration: {json.dumps(initial_session)}")
    
                async def from_client_to_server():
                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                new_msg = await self._process_message_to_server(msg, ws)
                                logger.debug(f"Processed message?: {new_msg[:100]}...")  # 처리된 메시지의 처음 100자만 로깅
                                if new_msg is not None:
                                    await target_ws.send_str(new_msg)
                                    
                            else:
                                print("Error: unexpected message type:", msg.type)

                async def from_server_to_client():
                        async for msg in target_ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                # logger.critical(f"FROM Azure RAW: {msg.data}")  # 원본 메시지 먼저 로깅
                                new_msg = await self._process_message_to_client(msg, ws, target_ws)
                                logger.debug(f"Azure to our backend?: {new_msg[:100] if new_msg is not None else 'None returned'}")
                                if new_msg is not None:
                                    await ws.send_str(new_msg)
                            else:
                                print("Error: unexpected message type:", msg.type)

                try:
                        await asyncio.gather(from_client_to_server(), from_server_to_client())
                except ConnectionResetError:
                        # Ignore the errors resulting from the client disconnecting the socket
                        pass

    async def _websocket_handler(self, request: web.Request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await self._forward_messages(ws)
        return ws
    
    def attach_to_app(self, app, path):
        app.router.add_get(path, self._websocket_handler)
