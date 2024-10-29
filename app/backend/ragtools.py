import re
from typing import Any
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import VectorizableTextQuery

from rtmt import RTMiddleTier, Tool, ToolResult, ToolResultDirection

# 새로 추가한 부분<
import logging
logger = logging.getLogger(__name__)
# 새로 추가한 부분>

_search_tool_schema = {
    "type": "function",
    "name": "search",
    "description": "MANDATORY SEARCH TOOL INSTRUCTION: " + \
                   "For every user input, without exception: ALWAYS call the SEARCH tool first: " + \
                   "Copy the exact user input for search " + \
                   "Process the search results before responding " + \
                   "Simple format: " + \
                   "SEARCH: <paste exact user message> " + \
                   "Example conversation flow: " + \
                   "User: '안녕하세요! 저는 미국에서 온 존이라고 해요. 한국은 처음이에요!'" + \
                   "SEARCH: '안녕하세요! 저는 미국에서 온 존이라고 해요. 한국은 처음이에요!'" + \
                   "[Process results] " + \
                   "Assistant: '어머, 반가워요 존님! 한국에 언제 오셨어요? 저는 민지라고 해요.'" + \
                   "User: '저는 일주일 전에 왔어요! 아직 한국어를 잘 못하지만 열심히 배우고 있어요 ㅎㅎ'" + \
                   "SEARCH: '저는 일주일 전에 왔어요! 아직 한국어를 잘 못하지만 열심히 배우고 있어요 ㅎㅎ'" + \
                   "[Process results] " + \
                   "Assistant: '와~ 일주일 전에 오셨는데 한국말 정말 잘하시네요! 혹시 주말에 시간 되시면 제가 맛있는 한식당 알려드릴까요?'" + \
                   "Remember: " + \
                   "ALWAYS use SEARCH for every user message" + \
                   "Copy the exact user input into SEARCH" + \
                   "Process search results before responding" + \
                   "Maintain natural conversation flow",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query"
            }
        },
        "required": ["query"],
        "additionalProperties": False
    }
}

#_grounding_tool_schema = {
#    "type": "function",
#    "name": "report_grounding",
#      "description": "Report use of a source from the knowledge base as part of an answer (effectively, cite the source). Sources " + \
#                   "appear in square brackets before each knowledge base passage. Always use this tool to cite sources when responding " + \
#                   "with information from the knowledge base.",
#    "parameters": {
#        "type": "object",
#        "properties": {
#            "sources": {
#                "type": "array",
#                "items": {
#                    "type": "string"
#                },
#                "description": "List of source names from last statement actually used, do not include the ones not used to formulate a response"
#            }
#        },
#        "required": ["sources"],
#        "additionalProperties": False
#    }
#}

async def _search_tool(search_client: SearchClient, args: Any) -> ToolResult:
    print(f"Searching for '{args['query']}' in the knowledge base.")
    # Hybrid + Reranking query using Azure AI Search
    search_results = await search_client.search(
        search_text=args['query'], 
        query_type="semantic",
        top=2,
        vector_queries=[VectorizableTextQuery(text=args['query'], k_nearest_neighbors=20, fields="text_vector")],
        select="chunk_id,title,chunk")
    result = ""
    async for r in search_results:
        result += f"[{r['chunk_id']}]: {r['chunk']}\n-----\n"
    print(f"Search results: {result[:200]}...") # 새로 추가한 부분
    logger.critical(f"Search results: {result[:200]}...")  # 새로 추가한 부분(결과의 일부만 로깅)
    return ToolResult(result, ToolResultDirection.TO_SERVER)

KEY_PATTERN = re.compile(r'^[a-zA-Z0-9_=\-]+$')

# TODO: move from sending all chunks used for grounding eagerly to only sending links to 
# the original content in storage, it'll be more efficient overall
#async def _report_grounding_tool(search_client: SearchClient, args: Any) -> None:
#    sources = [s for s in args["sources"] if KEY_PATTERN.match(s)]
#    list = ",".join(args["sources"]).replace("'", "''")
#    print(f"Grounding source: {list}")
    # Use search instead of filter to align with how detailt integrated vectorization indexes
    # are generated, where chunk_id is searchable with a keyword tokenizer, not filterable 
#    search_results = await search_client.search(search_text=list, 
#                                                search_fields=["chunk_id"], 
#                                                select=["chunk_id", "title", "chunk"], 
#                                                top=len(sources), 
#                                                query_type="full")
    
    # If your index has a key field that's filterable but not searchable and with the keyword analyzer, you can 
    # use a filter instead (and you can remove the regex check above, just ensure you escape single quotes)
    # search_results = await search_client.search(filter=f"search.in(chunk_id, '{list}')", select=["chunk_id", "title", "chunk"])

#    docs = []
#    async for r in search_results:
#        docs.append({"chunk_id": r['chunk_id'], "title": r["title"], "chunk": r['chunk']})
#    return ToolResult({"sources": docs}, ToolResultDirection.TO_CLIENT)

def attach_rag_tools(rtmt: RTMiddleTier, search_endpoint: str, search_index: str, credentials: AzureKeyCredential | DefaultAzureCredential) -> None:
    logger.info("Attaching RAG tools") # 새로 추가한 부분
    if not isinstance(credentials, AzureKeyCredential):
        credentials.get_token("https://search.azure.com/.default") # warm this up before we start getting requests
    search_client = SearchClient(search_endpoint, search_index, credentials, user_agent="RTMiddleTier")

    rtmt.tools["search"] = Tool(schema=_search_tool_schema, target=lambda args: _search_tool(search_client, args))
#    rtmt.tools["report_grounding"] = Tool(schema=_grounding_tool_schema, target=lambda args: _report_grounding_tool(search_client, args))
    logger.info("RAG tools attached") # 새로 추가한 부분
