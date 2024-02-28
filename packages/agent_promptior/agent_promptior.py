from langchain_community.document_transformers.html2text import Html2TextTransformer
from langchain.text_splitter import MarkdownHeaderTextSplitter
from langchain_core.documents import Document
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CohereRerank 
from langchain.tools.retriever import create_retriever_tool
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.llms.cohere import Cohere
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv, find_dotenv
from langchain.smith import RunEvalConfig
from WebScraper.webscraper import WebScraper
import langsmith
import os

from langserve.pydantic_v1 import BaseModel, Field
from typing import Any, AsyncIterator, Optional, cast, Dict, List, Tuple

from langchain_core.messages import AIMessage, FunctionMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain.prompts import MessagesPlaceholder

from langchain_core.runnables import (
    ConfigurableField,
    ConfigurableFieldSpec,
    Runnable,
    RunnableConfig,
)

load_dotenv(find_dotenv())

class Input(BaseModel):
    input: str
    # session_id: str
    # chat_history: List[Union[HumanMessage, AIMessage, FunctionMessage]] = Field(
    #     ...,
    #     extra={"widget": {"type": "chat", "input": "input", "output": "output"}},
    # )


class Output(BaseModel):
    output: Any


class PromptiorAgent():
    def __init__(self, url):
        self.url = url
        self.pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
        self.scraper = WebScraper(url)
        self.index_name = os.environ["PINECONE_INDEX_NAME"]
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small", dimensions=1536)
        self.retriever = self.document_loader_and_retriever()
        self.rerank = self.rerank_retriever()
        self.tools = [self.create_retriever_tool(self.retriever)]
        self.redis_url = "redis://:kf46Oua6cs9cGNCbrsrUz36fio9nnpM2@redis-19832.c267.us-east-1-4.ec2.cloud.redislabs.com:19832/0"
        self.agent = self.create_agent()
        
        
    def document_loader_and_retriever(self):
        if self.index_name not in self.pc.list_indexes().names():
            self.pc.create_index(
                self.index_name,
                dimension=1536,
                metric="dotproduct",
                spec=ServerlessSpec(cloud="aws", region="us-west-2"),
            )
            
            html_content, page_content, title = self.scraper.run()
            docs = self.transform_and_split(html_content, page_content, title) 
            vectorstore = PineconeVectorStore.from_documents(index_name=self.index_name, documents=docs, embedding=self.embeddings, namespace="promptior")
        else:
            vectorstore = PineconeVectorStore.from_existing_index(index_name=self.index_name, embedding=self.embeddings, namespace="promptior")
            
        retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
        return retriever

    def transform_and_split(self, html_content, page_content, title):        
        doc_1 = Document(page_content=html_content)
        doc_2 = Document(page_content=page_content)

        html2text_transformer = Html2TextTransformer()
        transformed_docs = html2text_transformer.transform_documents([doc_1, doc_2])

        promptior_content = f"# {title} \n {transformed_docs[0].page_content} \n {transformed_docs[1].page_content}"

        headers_to_split_on = [
            ("##", "title")
            # ("###", "sub_title"),
        ]

        markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on, strip_headers=False)
        docs = markdown_splitter.split_text(promptior_content)
        for doc in docs:
            if 'title' in doc.metadata:
                doc.page_content = f"Title: {doc.metadata['title']} \n\n {doc.page_content}"
        
        return docs
    
    def rerank_retriever(self):
        compressor = CohereRerank(top_n=4)
        compression_retriever = ContextualCompressionRetriever(
            base_compressor=compressor, base_retriever=self.retriever
        )
        return compression_retriever
    
    def create_retriever_tool(self, retriever):
        return create_retriever_tool(
            retriever,
            "search_promptior",
            "Search for information about Promptior. For any questions about Promptior, you must use this tool!",
        )
    
    def create_agent(self):
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a very powerful assistant, from the company Promptior.ai, I want you to only answer questions based on the context that is returned to you."
                    "Talk with the user as normal. "
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                ("user", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )
        
        llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo-0125")
        agent = create_openai_functions_agent(llm, self.tools, prompt)
        agent_executor = AgentExecutor(agent=agent, tools=self.tools)
        return agent_executor

    def evaluation_agent(self, dataset_name="testing-promptior", project_name="test-virtual-razor-8"):
        eval_config = RunEvalConfig(
            evaluators=[
                "cot_qa"
            ],
            custom_evaluators=[],
            eval_llm=ChatOpenAI(model="gpt-3.5-turbo-0125", temperature=0)
        )

        client = langsmith.Client()
        chain_results = client.run_on_dataset(
            dataset_name=dataset_name,
            llm_or_chain_factory=self.agent,
            evaluation=eval_config,
            project_name=project_name,
            concurrency_level=5,
            verbose=True,
        )
        return chain_results
    
    def get_message_history(self, session_id: str):
        return RedisChatMessageHistory(session_id, url=self.redis_url)
    
    def run(self):
        agent_with_chat_history = RunnableWithMessageHistory(
            self.agent,
            self.get_message_history,
            input_messages_key="input",
            history_messages_key="chat_history",
        ).with_types(input_type=Input)

        return agent_with_chat_history