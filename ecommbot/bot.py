import os
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_classic.chains.history_aware_retriever import create_history_aware_retriever
from langchain_classic.chains.retrieval import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import MessagesPlaceholder, ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_astradb import AstraDBVectorStore, AstraDBChatMessageHistory

# Load environment variables
load_dotenv()

# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")    
ASTRA_DB_API_ENDPOINT = os.getenv("ASTRA_DB_API_ENDPOINT")
ASTRA_DB_APPLICATION_TOKEN = os.getenv("ASTRA_DB_APPLICATION_TOKEN")
ASTRA_DB_KEYSPACE = os.getenv("ASTRA_DB_KEYSPACE")


class EcommChatBot:
    def __init__(self):
        """
        Initializes the LLM, the Vector Database connection, and builds
        a conversational RAG chain that remembers past chat history.
        """
        print("Initializing the AI and linking to AstraDB...")

        # Embeddings
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        
        # LLM
        self.llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0.2, max_output_tokens=200)

        # Vector database
        self.vstore = AstraDBVectorStore(
            embedding=self.embeddings,
            collection_name="advanced_ecomm",
            api_endpoint=ASTRA_DB_API_ENDPOINT,
            token=ASTRA_DB_APPLICATION_TOKEN,
            namespace=ASTRA_DB_KEYSPACE,
        )

        # Retriever for top 5 relevant chunks
        self.retriever = self.vstore.as_retriever(search_kwargs={"k": 3})

        # Build the RAG chain
        self._build_chain()

    def _get_session_history(self, session_id: str):
        """Returns the message history for a given session, stored in AstraDB."""
        return AstraDBChatMessageHistory(
            session_id=session_id,
            api_endpoint=ASTRA_DB_API_ENDPOINT,
            token=ASTRA_DB_APPLICATION_TOKEN,
            namespace=ASTRA_DB_KEYSPACE,
        )

    def _build_chain(self):
        """Builds the history-aware retriever + QA chain."""
        
        # Prompt to rewrite follow-up questions into standalone questions
        rephrase_prompt = ChatPromptTemplate.from_messages([
            ("system", "Given the following conversation and a follow up question, "
                       "rephrase the follow up question to be a standalone question. "
                       "If there is no chat history, just output the user's question as is."),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}")
        ])

        # History-aware retriever
        history_aware_retriever = create_history_aware_retriever(
            llm=self.llm,
            retriever=self.retriever,
            prompt=rephrase_prompt
        )

        # Prompt to answer user questions using retrieved context and history
        qa_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are Aura AI, a professional electronics assistant. "
                       "Provide direct, helpful answers in 2 sentences maximum."
                       "No fluff or polite intros. If the answer isn't in the context, say 'Information not found.'\n\n"
                       "Context:\n{context}"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}")
        ])

        # Chain to generate answers using the documents
        qa_chain = create_stuff_documents_chain(self.llm, qa_prompt)

        # Full RAG chain: retrieve + answer
        base_rag_chain = create_retrieval_chain(history_aware_retriever, qa_chain)

        # Wrap in history management
        self.rag_chain = RunnableWithMessageHistory(
            base_rag_chain,
            self._get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history",
            output_messages_key="answer"
        )

    def ask(self, question: str, session_id: str = "default_session") -> str:
        """
        Passes the user's question through the RAG chain with session support.
        """
        try:
            # We use config to pass the session_id to the history manager
            response = self.rag_chain.invoke(
                {"input": question},
                config={"configurable": {"session_id": session_id}}
            )
            answer = response["answer"]
        except Exception as e:
            import traceback
            print(f"Error in bot.ask: {e}")
            traceback.print_exc()
            answer = "Sorry, something went wrong. Let's try again."

        return answer


# Terminal chat interface
if __name__ == "__main__":
    bot = EcommChatBot()
    print("\n--- Bot initialized. Type 'exit' to quit ---\n")
    
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            print("Goodbye!")
            break
        
        response = bot.ask(user_input)
        print(f"Bot: {response}\n")